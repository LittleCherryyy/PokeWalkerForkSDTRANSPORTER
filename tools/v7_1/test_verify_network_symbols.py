import json
import tempfile
import unittest
from pathlib import Path
from verify_network_symbols import verify_manifest, EXPECTED


def sample():
    return {"schema": 1, "blocked_reason": "unverified",
            "functions": [{"symbol": name, "address": None,
                           "residency": "unverified"}
                          for name in sorted(EXPECTED)]}


class ResearchManifestTests(unittest.TestCase):
    def verify(self, obj):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(obj), encoding="utf-8")
            verify_manifest(path)

    def test_all_unverified_pass(self):
        self.verify(sample())

    def test_guessed_address_fails(self):
        obj = sample()
        obj["functions"][0]["address"] = "0x021D464C"
        with self.assertRaises(ValueError):
            self.verify(obj)

    def test_overlay_without_proof_fails(self):
        obj = sample()
        obj["functions"][0]["residency"] = "resident"
        with self.assertRaises(ValueError):
            self.verify(obj)

    def test_missing_symbol_fails(self):
        obj = sample()
        obj["functions"].pop()
        with self.assertRaises(ValueError):
            self.verify(obj)


if __name__ == "__main__":
    unittest.main()
