"""Parser tests run on any OS; do not load or redistribute system DLLs."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "bundle_windows", Path(__file__).with_name("bundle-windows.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

RUNTIME = r"libcurl-4.dll => D:\msys64\mingw64\bin\libcurl-4.dll (0x1234)"


class DependencyTests(unittest.TestCase):
    def test_loader_api_contracts_are_not_concrete_missing_dlls(self):
        text = "\n".join([
            RUNTIME,
            "api-ms-win-core-file-l1-1-0.dll => not found",
            "ext-ms-win-com-suspendresiliency-l1-1-0.dll => not found",
        ])
        self.assertEqual(module.runtime_paths(text), [r"D:\msys64\mingw64\bin\libcurl-4.dll"])

    def test_missing_concrete_dll_still_fails(self):
        with self.assertRaisesRegex(RuntimeError, "libjansson-4.dll"):
            module.runtime_paths(RUNTIME + "\nlibjansson-4.dll => not found")

    def test_system_libraries_are_not_copied_and_runtime_is_deduplicated(self):
        text = RUNTIME + "\n" + RUNTIME + "\n" + r"KERNEL32.dll => C:\Windows\System32\KERNEL32.dll (0x1)"
        self.assertEqual(len(module.runtime_paths(text)), 1)

    def test_empty_closure_fails(self):
        with self.assertRaisesRegex(RuntimeError, "No MinGW"):
            module.runtime_paths("api-ms-win-core-file-l1-1-0.dll => not found")


if __name__ == "__main__":
    unittest.main()
