"""No-ROM synthetic V8.5 NitroSDK thread-info candidate offsets tests."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[2]/"tools/v8_5/hgss_thread_info_layout_audit.py"
spec=importlib.util.spec_from_file_location("v85_thread_layout_tests",SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE=0x020D1A00

def make_game(code="IPKE"):
    image=bytearray(0x500)
    def word(addr,value):
        struct.pack_into("<I",image,addr-BASE,value)
    for i,v in enumerate(m.v84.ENTRY_OPCODES):
        word(m.v84.ENTRY+i*4,v)
    refs=[]
    for pc,literal,global_addr,reg,next_word in (
        (0x020D1B00,0x020D1B40,0x021E16A0,0,0xE5901004),
        (0x020D1B08,0x020D1B44,0x021E16A0,1,0xE5812010),
        (0x020D1B10,0x020D1B48,0x021E167C,2,0xE5923008),
        (0x020D1B18,0x020D1B4C,0x021E1688,3,0xE5934010),
    ):
        imm=literal-pc-8
        word(pc,0xE59F0000 | (reg<<12) | imm)
        word(pc+4,next_word)
        word(literal,global_addr)
        refs.append({
            "literal_value":f"0x{global_addr:08X}",
            "instruction_address":f"0x{pc:08X}",
            "literal_address":f"0x{literal:08X}",
            "register":f"r{reg}",
        })
    return image, {
        "game_code":code,
        "entry_opcode_guard_passed":True,
        "literal_xrefs":refs,
    }

class V85LayoutTests(unittest.TestCase):
    def test_two_distinct_nitrosdk_header_layouts(self):
        self.assertEqual(
            m.LAYOUTS["SDK_THREAD_INFINITY"],
            {"current":4,"list":8,"switchCallback":12}
        )
        self.assertEqual(
            m.LAYOUTS["legacy_fixed_thread_limit"],
            {"current":8,"list":12,"switchCallback":16}
        )
        self.assertNotEqual(m.LAYOUTS["SDK_THREAD_INFINITY"],
                            m.LAYOUTS["legacy_fixed_thread_limit"])

    def test_one_instruction_memory_access_register_match(self):
        x=m.direct_arm_access(0xE5901004,0)
        self.assertEqual((x["signed_offset"],x["access"],x["width"]),(4,"load","word"))
        self.assertTrue(x["candidate_not_verified_osthreadinfo_field"])
        y=m.direct_arm_access(0xE5812010,1)
        self.assertEqual((y["signed_offset"],y["access"]),(16,"store"))
        self.assertIsNone(m.direct_arm_access(0xE5901004,2))
        self.assertIsNone(m.direct_arm_access(0x15901004,0))
        self.assertIsNone(m.direct_arm_access(0xE7901004,0))
        self.assertIsNone(m.direct_arm_access(0xE5901180,0))

    def test_real_0x021e1688_flag_not_mistaken_for_struct(self):
        image,metadata=make_game()
        r=m.audit_static_image(image,BASE,metadata)
        self.assertEqual(r["candidate_xrefs"],{
            "0x021E16A0":2,
            "0x021E167C":1,
        })
        self.assertEqual(len(r["single_immediate_instruction_accesses"]),3)
        self.assertTrue(all(x["candidate_not_verified_osthreadinfo_field"]
                            for x in r["single_immediate_instruction_accesses"]))
        self.assertFalse(r["possible_thread_info_struct_verified"])
        self.assertFalse(r["instruction_values_exported"])
        self.assertNotIn("0x021E1688",r["candidate_xrefs"])
        self.assertEqual(len(r["groups"]),3)

    def test_mismatch_original_entry_disables_all_analysis(self):
        image,metadata=make_game()
        image[m.v84.ENTRY-BASE]=0
        with self.assertRaises(m.v84.ThreadXrefError):
            m.audit_static_image(image,BASE,metadata)

    def test_invalid_cross_reference_fails_closed(self):
        image,metadata=make_game()
        metadata["literal_xrefs"][0]["literal_address"]="0x020D1B48"
        with self.assertRaisesRegex(m.ThreadLayoutError,"no longer matches"):
            m.audit_static_image(image,BASE,metadata)

    def test_compare_never_approves_thread_or_wifi(self):
        image_a,meta_a=make_game("IPKE")
        image_b,meta_b=make_game("IPGE")
        a=m.audit_static_image(image_a,BASE,meta_a)
        b=m.audit_static_image(image_b,BASE,meta_b)
        res=m.compare(a,b)
        self.assertEqual(res["shared_first_following_instruction_matches"],3)
        self.assertEqual(res["only_hg_matches"],0)
        self.assertEqual(res["only_ss_matches"],0)
        self.assertFalse(res["game_scheduler_struct_base_verified"])
        self.assertFalse(res["safe_to_call_scheduler_api"])
        self.assertFalse(res["live_current_thread_pointer_read"])
        self.assertFalse(res["wifi_enabled"])
        with self.assertRaises(m.ThreadLayoutError):
            m.compare(a,a)

    def test_cli_refuses_rom_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            hg=Path(folder)/"HeartGold.nds"
            ss=Path(folder)/"SoulSilver.nds"
            hg.write_bytes(b"HG")
            ss.write_bytes(b"SS")
            saved=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),saved)
            self.assertEqual(m.main([str(hg),str(hg)]),2)


if __name__=="__main__":
    unittest.main()
