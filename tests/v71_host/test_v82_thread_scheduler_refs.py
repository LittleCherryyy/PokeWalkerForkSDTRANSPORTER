"""V8.2 strict no-ROM test vectors for passive NitroSDK OS state references."""
import importlib.util
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

P=Path(__file__).resolve().parents[2]/"tools/v8_2/hgss_thread_scheduler_refs.py"
spec=importlib.util.spec_from_file_location("v82_sched_test",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE=0x02000000


def insert_word(data,offset,word):
    struct.pack_into("<I",data,offset,word)


class SchedulerRefsTests(unittest.TestCase):
    def test_pc_relative_arm_literal_decode(self):
        self.assertEqual(m.decode_pc_literal(0xE59F0018,BASE+0x20),
                         (0,BASE+0x40))
        self.assertEqual(m.decode_pc_literal(0xE51F1008,BASE+0x20),
                         (1,BASE+0x20))
        self.assertIsNone(m.decode_pc_literal(0xE3A00000,BASE+0x20))
        self.assertIsNone(m.decode_pc_literal(0x159F0018,BASE+0x20))

    def test_field_offset_is_only_syntactic_candidate(self):
        a=m.decode_r0_memory_offset(0xE5901004)
        self.assertEqual(a["signed_offset"],4)
        self.assertEqual(a["access"],"load")
        self.assertFalse(a["offset_is_verified_osthread_field"])
        b=m.decode_r0_memory_offset(0xE5002008)
        self.assertEqual(b["signed_offset"],-8)
        self.assertEqual(b["access"],"store")
        self.assertIsNone(m.decode_r0_memory_offset(0xE5911004))
        self.assertIsNone(m.decode_r0_memory_offset(0x15901004))

    def test_sha256_anchored_entry_resolves_only_static_literal(self):
        ram=bytearray(0x200)
        start=0x20
        # LDR r0,[pc,#0x18] reads from offset 0x40; do not read pointer.
        insert_word(ram,start,0xE59F0018)
        insert_word(ram,start+4,0xE5901004)
        insert_word(ram,start+8,0xE12FFF1E)
        insert_word(ram,0x40,0x02000180)
        sig=hashlib.sha256(ram[start:start+128]).hexdigest()
        x=m.inspect_entry(ram,BASE,BASE+start,sig,"IPKE")
        self.assertEqual(x["linear_scan_bytes"],12)
        self.assertIn("BX LR",x["stop_reason"])
        self.assertEqual(len(x["pc_relative_literal_references"]),1)
        ref=x["pc_relative_literal_references"][0]
        self.assertEqual(ref["literal_address"],"0x02000040")
        self.assertEqual(ref["pointer_value"],"0x02000180")
        self.assertTrue(ref["literal_within_static_arm9"])
        self.assertFalse(ref["verified_scheduler_global"])
        self.assertEqual(x["candidate_r0_base_offsets"][0]["signed_offset"],4)
        self.assertFalse(x["function_safe_to_invoke"])
        self.assertFalse(x["code_bytes_exported"])
        with self.assertRaisesRegex(m.SchedulerRefError,"hash mismatch"):
            m.inspect_entry(ram,BASE,BASE+start,"bad","IPKE")

    def test_out_of_bounds_literal_is_never_dereferenced(self):
        ram=bytearray(256)
        insert_word(ram,0,0xE51F0040)
        insert_word(ram,4,0xE12FFF1E)
        sig=hashlib.sha256(ram[:128]).hexdigest()
        result=m.inspect_entry(ram,BASE,BASE,sig,"IPGE")
        reference=result["pc_relative_literal_references"][0]
        self.assertEqual(reference["literal_within_static_arm9"],False)
        self.assertIsNone(reference["pointer_value"])
        self.assertEqual(reference["pointer_classification"],"not dereferenced")

    def test_overlay_storage_gap_is_not_assumed_struct_size(self):
        example={
            "overlay_static_end":"0x0222AB80",
            "overlay_static_plus_bss_end":"0x0222B6E0",
            "arg1_thread_structure":"0x0222ADF8",
            "stack_lower_bound":"0x0222AED0",
            "arg4_stack_top":"0x0222B6D0",
            "arg5_stack_bytes":2048,
        }
        result=m.check_overlay39_storage(example)
        self.assertEqual(result["reserved_gap_between_object_start_and_stack"],216)
        self.assertTrue(result["gap_is_not_proven_struct_size"])
        self.assertFalse(result["safe_to_allocate_new_worker_here"])
        example["arg5_stack_bytes"]=1024
        with self.assertRaises(m.SchedulerRefError):
            m.check_overlay39_storage(example)

    def test_cross_game_comparison_does_not_prove_live_global(self):
        def fixture(game):
            return {
                "game_code":game,
                "functions":{name:{
                    "v81_128byte_sha256_verified":True,
                    "candidate_r0_base_offsets":[{"signed_offset":4}],
                    "pc_relative_literal_references":[],
                    "stop_reason":"BX LR",
                } for name in m.v81.THREAD_ENTRIES},
                "overlay39_allocation":{"safe_to_allocate_new_worker_here":False},
            }
        result=m.compare(fixture("IPKE"),fixture("IPGE"))
        self.assertEqual(len(result["comparisons"]),3)
        self.assertFalse(result["safe_to_call_thread_apis"])
        self.assertFalse(result["scheduler_runtime_initialized_proven"])
        self.assertFalse(result["arm7_radio_ownership_proven"])
        with self.assertRaises(m.SchedulerRefError):
            m.compare(fixture("IPKE"),fixture("IPKE"))

    def test_cli_never_overwrites_rom(self):
        with tempfile.TemporaryDirectory() as tmp:
            hg=Path(tmp)/"HeartGold.nds"
            ss=Path(tmp)/"SoulSilver.nds"
            hg.write_bytes(b"own original HG backup")
            ss.write_bytes(b"own original SS backup")
            old=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),old)
            self.assertEqual(m.main([str(hg),str(hg)]),2)


if __name__=="__main__":
    unittest.main()
