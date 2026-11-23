"""V7.7 offline PC reference: synthetic protocol checks, no commercial ROM."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

P=Path(__file__).resolve().parents[2]/"tools/v7_7/hgss_wifi_live_crc_reference.py"
sp=importlib.util.spec_from_file_location("v77_offline_crc",P)
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)


class V77PcCrcTests(unittest.TestCase):
    def test_exact_v76_entry_mapping(self):
        expected={
            "WCM_Init":0x020AD850,
            "WCM_StartupAsync":0x020AD9C0,
            "WCM_GetPhase":0x020AE420,
            "SOC_Socket":0x020A2EAC,
            "SOC_Connect":0x020A2F04,
        }
        self.assertEqual({name:value[0] for name,value in m.ENTRIES.items()},expected)
        self.assertTrue(all(len(value[1])==64 for value in m.ENTRIES.values()))

    def test_cross_title_comparison_refuses_to_claim_network(self):
        def synthetic(code,kind):
            return {
                "game_code":code,"rom_sha1":"sha","arm9_runtime_sha256":"hash",
                "windows":{name:{
                    "address":f"0x{addr:08X}","bytes":32,
                    "crc32":kind,"v76_sha256_verified":True,
                } for name,(addr,h) in m.ENTRIES.items()}
            }
        result=m.compare(synthetic("IPKE","12345678"),
                         synthetic("IPGE","12345678"))
        self.assertEqual(len(result["cross_title_crc32"]),5)
        self.assertTrue(result["all_five_crc_equal"])
        self.assertFalse(result["radio_or_network_enabled"])
        self.assertFalse(result["resident_code_verified_on_dsi"])
        with self.assertRaisesRegex(m.ReferenceError,"one original US"):
            m.compare(synthetic("IPKE","12345678"),
                      synthetic("IPKE","12345678"))

    def test_never_overwrite_original_rom(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"HeartGold.nds"
            b=Path(tmp)/"SoulSilver.nds"
            a.write_bytes(b"HG")
            b.write_bytes(b"SS")
            saved=a.read_bytes()
            self.assertEqual(m.main([str(a),str(b),"--output",str(a)]),2)
            self.assertEqual(a.read_bytes(),saved)

if __name__=="__main__":
    unittest.main()
