# Yitcoin miner downloads (experimental)

The `Yitcoin native miner packages` Actions workflow builds four separate
packages: Windows x64, Linux x64, macOS Intel, and macOS Apple Silicon.
Open https://github.com/shadiqaust/cpuminer-opt/actions and select a run.
Download only a package from a successful platform job. There is no installer,
GUI, or signed production release; never disable antivirus to run this miner.
Windows ARM and Linux ARM are not included.

Each artifact contains a ZIP (Windows) or tar.gz (Linux/Mac), its SHA256 file,
source commit, license, runtime libraries, and a placeholder mining config.
Extract the outer GitHub artifact ZIP first, then verify the inner archive:

```powershell
# Windows PowerShell, in the download directory:
Get-FileHash .\yitcoin-miner-windows-x86_64.zip -Algorithm SHA256
Get-Content .\yitcoin-miner-windows-x86_64.zip.sha256
Expand-Archive .\yitcoin-miner-windows-x86_64.zip -DestinationPath "$HOME\yitcoin-miner"
```

```bash
# Linux:
sha256sum yitcoin-miner-linux-x86_64.tar.gz
cat yitcoin-miner-linux-x86_64.tar.gz.sha256
tar -xzf yitcoin-miner-linux-x86_64.tar.gz
```

```bash
# Mac Apple Silicon (use macos-x86_64 for an Intel Mac):
shasum -a 256 yitcoin-miner-macos-arm64.tar.gz
cat yitcoin-miner-macos-arm64.tar.gz.sha256
tar -xzf yitcoin-miner-macos-arm64.tar.gz
```

Stop if the hash differs. Matching checksums are not publisher signatures.
Linux builds target Ubuntu 24.04/glibc 2.39 or compatible newer systems;
Mac builds target macOS 15. Runtime smoke testing occurs on the CI runner,
not every possible computer. Intel/AMD builds use a baseline x86-64 target,
not the CI runner's CPU-specific native optimizations.

## Connect to your Linux Yitcoin node safely

Your node must be updated, synced, and connected to another Yitcoin peer.
At/after activation height 200 the miner honors the mandatory 2% owner
subsidy output; transaction fees go to the miner. Do not use an old miner.
The package tests use synthetic loopback work, not your live chain. They
exercise SHA256d proof of work and the 49/1 coinbase split, but are not a
full consensus-node integration test.

For a Windows/Mac miner using your Linux node, keep RPC on the Linux loopback
address. Open a separate terminal and keep this SSH tunnel running:

```bash
ssh -N -L 127.0.0.1:29432:127.0.0.1:19432 yitcoin@seed.yitcoin.com
```

Use your actual account/server if different. This command also works in Windows
PowerShell when the OpenSSH client is installed. It does not require WSL.
Do not open public firewall access to RPC port 19432 or tunnel port 29432.
P2P port 19433 is not a miner RPC endpoint.

Copy `miner.example.json` to `miner.json` and edit it locally:

- `url`: `http://127.0.0.1:29432` for the tunnel, or
  `http://127.0.0.1:19432` when hashing on the Linux node itself.
- `user` and `pass`: the dedicated **Linux node miner RPC account**,
  not your SSH login. That account needs getblocktemplate/submitblock access.
- `coinbase-addr`: your public YITC wallet receiving address.
- `threads`: begin with 2 and monitor CPU temperature.

Never share or commit `miner.json`: it contains a password. This miner does
not create a wallet or need private keys. The receiving wallet can live on
any synced Yitcoin node.

## Start and stop

Windows PowerShell, from the extracted folder containing cpuminer.exe:

```powershell
Copy-Item .\miner.example.json .\miner.json
notepad .\miner.json
.\cpuminer.exe --config=.\miner.json
```

Linux/Mac, from the extracted folder containing cpuminer:

```bash
umask 077
cp miner.example.json miner.json
nano miner.json
chmod 600 miner.json
./cpuminer --config=./miner.json
```

Do not overwrite an existing miner.json with these copy commands.
Stop with Ctrl+C. On Mac, review the unsigned/ad-hoc-signed application using
System Settings → Privacy & Security if blocked; never disable Gatekeeper
globally. Keep all DLLs/dylibs and the `lib/` directory with the executable.

Initially stop after one accepted block and confirm the chain height and wallet
outputs through your Yitcoin node. Newly mined funds remain immature until the
100-block coinbase maturity requirement is met. Hashing earns no guaranteed
reward; block discovery is probabilistic. Never import valuable Bitcoin keys.
