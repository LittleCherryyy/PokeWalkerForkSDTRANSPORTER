"""V8.4 test synthetic static ARM9 instruction-literal cross-reference map."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[2]/"tools/v8_4/hgss_thread_flag_xrefs.py"
spec=importlib.util.spec_from_file_location("v84_thread_xrefs",SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE=0x020D1A00


def fixture(game="IPKE"):
    img=bytearray(0x600)
    def put(address,word):
        struct.pack_into("<I",img,address-BASE,word)
    for i,word in enumerate(m.ENTRY_OPCODES):
        put(m.ENTRY+i*4,word)
    # Another valid PC-relative literal reference to the same global.
    extra_pc=0x020D1B00
    extra_lit=0x020D1B40
    put(extra_pc,0xE59F0000 | (extra_lit-extra_pc-8))
    put(extra_lit,m.FLAG_ADDR)
    # A static literal to a neighboring address; still not a verified field.
    near_pc=0x020D1B04
    near_lit=0x020D1B44
    put(near_pc,0xE59F1000 | (near_lit-near_pc-8))
    put(near_lit,m.FLAG_ADDR+4)
    # A raw value that looks like a literal but nobody reads it.
    put(0x020D1B80,m.FLAG_ADDR+8)
    return img


class ThreadFlagXrefTests(unittest.TestCase):
    def test_exact_original_entry_is_hard_guard(self):
        data=fixture()
        self.assertTrue(m.verify_original_entry(data,BASE))
        data[m.ENTRY-BASE]=0
        with self.assertRaisesRegex(m.ThreadXrefError,"guard mismatch"):
            m.verify_original_entry(data,BASE)

    def test_scan_only_reaches_arm_pc_relative_literals(self):
        img=fixture()
        sites=m.scan_candidate_literal_sites(img,BASE)
        self.assertIn(m.ENTRY+12,sites)
        self.assertIn(0x020D1B40,sites)
        self.assertIn(0x020D1B44,sites)
        self.assertIn(0x020D1B80,sites)
        refs=m.find_pc_relative_xrefs(img,BASE,sites)
        self.assertEqual(
            {x["instruction_address"] for x in refs},
            {"0x020D1AC4","0x020D1B00","0x020D1B04"}
        )
        self.assertNotIn("0x020D1B80", {x["literal_address"] for x in refs})
        self.assertTrue(all(x["validated_executable_instruction"] is False for x in refs))
        self.assertTrue(all(x["validated_osthread_field"] is False for x in refs))
        self.assertTrue(all(len(x["nearest_32byte_sha256"])==64 for x in refs))

    def test_nearby_global_remains_candidate_not_verified(self):
        result=m.analyze_image(fixture(),BASE,"IPKE")
        self.assertTrue(result["entry_opcode_guard_passed"])
        self.assertEqual(result["syntactic_arm_ldr_xref_count"],3)
        offsets={x["address_delta_from_thread_flag"] for x in result["literal_xrefs"]}
        self.assertEqual(offsets,{0,4})
        self.assertTrue(result["nearby_field_offsets_are_unverified"])

    def test_dont_follow_unbounded_or_untrusted_literals(self):
        img=fixture()
        # Deliberately place an LDR whose literal lies OUTSIDE image.
        pc=0x020D1B20
        struct.pack_into("<I",img,pc-BASE,0xE59F0FFF)
        refs=m.find_pc_relative_xrefs(img,BASE,m.scan_candidate_literal_sites(img,BASE))
        self.assertFalse(any(x["instruction_address"]==f"0x{pc:08X}" for x in refs))
        with self.assertRaises(m.ThreadXrefError):
            m.find_pc_relative_xrefs(img,BASE,{})

    def test_cross_title_comparison_no_thread_permissions(self):
        hg=m.analyze_image(fixture(),BASE,"IPKE")
        ss=m.analyze_image(fixture("IPGE"),BASE,"IPGE")
        result=m.compare(hg,ss)
        self.assertEqual(result["shared_xref_count"],3)
        self.assertEqual(len(result["shared_xrefs"]),3)
        self.assertTrue(all(x["same_context_sha256"] for x in result["shared_xrefs"]))
        self.assertFalse(result["safe_to_create_or_reuse_thread"])
        self.assertFalse(result["game_thread_list_address_proven"])
        self.assertFalse(result["arm7_radio_ownership_proven"])
        self.assertFalse(result["wifi_enabled"])
        with self.assertRaises(m.ThreadXrefError):
            m.compare(hg,hg)

    def test_cli_refuses_to_modify_original_rom(self):
        with tempfile.TemporaryDirectory() as folder:
            hg=Path(folder)/"HeartGold.nds"
            ss=Path(folder)/"SoulSilver.nds"
            hg.write_bytes(b"HG")
            ss.write_bytes(b"SS")
            old=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),old)
            self.assertEqual(m.main([str(hg),str(hg)]),2)


if __name__=="__main__":
    unittest.main()
