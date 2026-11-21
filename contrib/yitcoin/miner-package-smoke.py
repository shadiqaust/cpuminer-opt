"""Exercise the packaged miner against synthetic loopback RPC, never a live chain.

Checks capability negotiation, real SHA256d work, submitted header PoW,
coinbase serialization, merkle root, witness commitment, and the 49/1 split.
This fixture is not a substitute for integration with a validating Core node.
"""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import threading
import time


def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def compact(stream):
    first = stream.read(1)[0]
    if first < 253:
        return first
    return int.from_bytes(stream.read({253: 2, 254: 4, 255: 8}[first]), "little")


OWNER_SCRIPT = bytes.fromhex("0014" + "11" * 20)
MINER_SCRIPT = bytes.fromhex("76a914" + "00" * 20 + "88ac")
TARGET = 0x7FFFFF << (8 * (0x20 - 3))
done = threading.Event()
errors = []
capability_seen = threading.Event()


def check_block(raw_hex):
    raw = bytes.fromhex(raw_hex)
    header = raw[:80]
    assert len(header) == 80
    assert int.from_bytes(sha256d(header), "little") <= TARGET, "invalid PoW"
    assert header[4:36] == bytes(32)
    assert header[72:76] == bytes.fromhex("ffff7f20")
    stream = io.BytesIO(raw[80:])
    assert compact(stream) == 1, "expected only coinbase"
    tx_start = stream.tell()
    version = stream.read(4)
    witness = stream.read(2) == b"\x00\x01"
    stream.seek(tx_start + (6 if witness else 4))
    inputs_start = stream.tell()
    assert compact(stream) == 1
    assert stream.read(36) == bytes(32) + b"\xff" * 4
    script_sig = stream.read(compact(stream))
    assert script_sig.startswith(bytes.fromhex("02c800")), "wrong BIP34 height"
    assert stream.read(4) == b"\xff" * 4
    count = compact(stream)
    assert count == 3, "miner, owner, and segwit commitment expected"
    outputs = []
    for _ in range(count):
        value = struct.unpack("<Q", stream.read(8))[0]
        outputs.append((value, stream.read(compact(stream))))
    outputs_end = stream.tell()
    assert outputs[0] == (4_900_000_000, MINER_SCRIPT), outputs
    assert outputs[1] == (100_000_000, OWNER_SCRIPT), outputs
    assert outputs[2] == (0, bytes.fromhex("6a24aa21a9ed") + sha256d(bytes(64)))
    assert witness, "missing coinbase witness"
    assert compact(stream) == 1
    assert stream.read(compact(stream)) == bytes(32)
    locktime = stream.read(4)
    assert len(locktime) == 4
    assert stream.read() == b""
    stripped = version + raw[80:][inputs_start:outputs_end] + locktime
    assert sha256d(stripped) == header[36:68], "merkle root mismatch"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        result, error = None, None
        method = request["method"]
        if method == "getblocktemplate":
            opts = request["params"][0]
            if "yitcoin-owner-reward" not in opts.get("capabilities", []):
                errors.append("missing owner reward capability")
                done.set()
                error = {"code": -8, "message": "missing owner capability"}
            else:
                capability_seen.set()
                result = {
                    "version": 0x20000000,
                    "height": 200,
                    "previousblockhash": "00" * 32,
                    "curtime": int(time.time()),
                    "bits": "207fffff",
                    "target": f"{TARGET:064x}",
                    "transactions": [],
                    "rules": ["segwit"],
                    "mutable": ["time", "transactions", "prevblock"],
                    "coinbaseaux": {},
                    "coinbasevalue": 5_000_000_000,
                    "yitcoin_owner_reward": 100_000_000,
                    "yitcoin_owner_script": OWNER_SCRIPT.hex(),
                    "sizelimit": 4000000,
                    "sigoplimit": 80000,
                }
        elif method == "submitblock":
            try:
                check_block(request["params"][0])
            except Exception as exc:
                errors.append(str(exc))
                result = "invalid-fixture-block"
            done.set()
        elif method == "getmininginfo":
            result = {"blocks": 199, "difficulty": 0.00000000046566, "networkhashps": 0}
        else:
            error = {"code": -32601, "message": "unsupported fixture RPC"}
        body = json.dumps({"id": request.get("id"), "result": result, "error": error}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    executable = str(Path(sys.argv[1]).resolve())
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as directory:
            # Fixture-only credentials. No external RPC connection or wallet.
            config = {
                "algo": "sha256d", "threads": 1,
                "url": f"http://127.0.0.1:{server.server_port}",
                "user": "fixture", "pass": "fixture",
                # Public burn address: tests only. Never use as a real payout.
                "coinbase-addr": "1111111111111111111114oLvT2",
            }
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(config))
            with open("miner-smoke.log", "w+") as log:
                environment = os.environ.copy()
                if os.name == "nt":
                    # Prove the packaged DLLs are enough; do not accidentally
                    # resolve missing dependencies from the MSYS2 toolchain.
                    root = environment.get("SystemRoot", r"C:\Windows")
                    environment["PATH"] = os.pathsep.join(
                        [str(Path(executable).parent), str(Path(root) / "System32"), root])
                process = subprocess.Popen([executable, "--config=" + str(path)],
                                           stdout=log, stderr=log, env=environment)
                try:
                    deadline = time.monotonic() + 60
                    while not done.wait(0.1):
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError("Miner exited or timed out before valid fixture submission")
                    assert capability_seen.is_set(), "capability not seen"
                    assert not errors, errors
                    print("PASS: packaged native miner negotiated owner reward and submitted valid synthetic 49/1 SHA256d block.")
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                    log.seek(0)
                    print(log.read()[-6000:])
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
