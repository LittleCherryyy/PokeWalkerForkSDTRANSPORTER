"""V8.1 synthetic original HGSS OS thread setup checks without copyrighted ROM."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[2]/"tools/v8_1/hgss_thread_abi_context.py"
spec=importlib.util.spec_from_file_location("hgss_v81_tested",SCRIPT)
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def sample_overlay():
    base=0x02229400
    buf=bytearray(0x3500)
    def put(addr,word):
        struct.pack_into("<I",buf,addr-base,word)
    for pc,w in v.CALLER_WORDS.items():
        put(pc,w)
    for pc,(rd,lit,value) in v.LDR_SITES.items():
        signed=lit-(pc+8)
        assert 0<=signed<=0xfff
        put(pc,0xE59F0000|(rd<<12)|signed)
        put(lit,value)
    return base,bytes(buf),{
        "bss_bytes":0x800,
        "overlay_id":39,
    }


class V81ThreadAbi(unittest.TestCase):
    def test_three_pinned_scheduler_entries(self):
        self.assertEqual(
            {k:v[0] for k,v in v.THREAD_ENTRIES.items()},
            {
                "OS_IsThreadAvailable":0x020D1AC4,
                "OS_CreateThread":0x020D1AD4,
                "OS_WakeupThreadDirect":0x020D1F34,
            },
        )
        self.assertTrue(all(len(sha)==64 for addr,sha in v.THREAD_ENTRIES.values()))

    def test_overlay39_six_args_and_thread_overlay_lifetime(self):
        result=v.inspect_overlay39_setup(sample_overlay())
        self.assertTrue(result["six_argument_sequence_validated"])
        self.assertEqual(result["arg5_stack_bytes"],0x800)
        self.assertEqual(result["arg6_priority_initialized_to"],16)
        self.assertIsNone(result["arg3_user_pointer"])
        self.assertEqual(result["arg2_entry_is_overlay_local_trampoline"],
                         "0x02229974")
        self.assertEqual(result["entry_trampoline_final_target"],
                         "0x02229474")
        self.assertTrue(result["thread_storage_callback_stack_within_overlay_allocation"])
        self.assertTrue(result["overlay_unload_can_invalidate_entry_and_stack"])
        self.assertFalse(result["game_thread_creation_or_reuse_safe"])
        self.assertFalse(result["game_network_thread_alive_in_overworld_proven"])
        self.assertEqual(len(result["literal_sites"]),len(v.LDR_SITES))

    def test_all_caller_instruction_signatures_fail_closed(self):
        base,img,meta=sample_overlay()
        for address in v.CALLER_WORDS:
            broken=bytearray(img)
            struct.pack_into("<I",broken,address-base,0)
            with self.assertRaisesRegex(v.ThreadContextError,"caller code mismatch"):
                v.inspect_overlay39_setup((base,broken,meta))

    def test_broken_pc_relative_literals_fail_closed(self):
        base,img,meta=sample_overlay()
        pc=0x0222999C
        broken=bytearray(img)
        struct.pack_into("<I",broken,pc-base,0xE3A01000)  # MOV r1, #0 not LDR
        with self.assertRaisesRegex(v.ThreadContextError,"literal"):
            v.inspect_overlay39_setup((base,broken,meta))
        broken=bytearray(img)
        literal=0x022299CC
        struct.pack_into("<I",broken,literal-base,0)
        with self.assertRaisesRegex(v.ThreadContextError,"target mismatch"):
            v.inspect_overlay39_setup((base,broken,meta))

    def test_signed_pc_literal_decode(self):
        self.assertEqual(v.decode_literal_ldr_arm(0xE59F1010,0x02000100,1),
                         0x02000118)
        self.assertEqual(v.decode_literal_ldr_arm(0xE51FC00C,0x02000100,12),
                         0x020000FC)
        with self.assertRaises(v.ThreadContextError):
            v.decode_literal_ldr_arm(0xE3A00000,0x02000100,0)
        with self.assertRaises(v.ThreadContextError):
            v.decode_literal_ldr_arm(0xE59F1010,0x02000100,0)

    def test_invalid_overlay_bounds(self):
        with self.assertRaises(v.ThreadContextError):
            v.u32_at(b"\0"*12,0x02000000,0x02000003)
        with self.assertRaises(v.ThreadContextError):
            v.u32_at(b"\0"*12,0x02000000,0x0200000C)

    def test_cross_title_compare_fails_closed_even_on_matching_abi(self):
        def example(code,hashval):
            fns={
                name:{
                    "entry":f"0x{address:08X}",
                    "fixed_32byte_sha256":sha,
                    "additional_128byte_sha256":hashval,
                    "terminal_candidate":f"0x{address:08X}",
                } for name,(address,sha) in v.THREAD_ENTRIES.items()
            }
            return {
                "game_code":code, "scheduler_function_entries":fns,
                "overlay39_thread_setup":{
                    "six_argument_sequence_validated":True,
                    "literal_sites":{"thread":"0x02000000"},
                },
            }
        r=v.compare(example("IPKE","same"),example("IPGE","same"))
        self.assertEqual(len(r["cross_title_thread_comparison"]),3)
        self.assertTrue(r["overlay39_setup_same_between_games"])
        self.assertFalse(r["scheduler_runtime_initialized_proven"])
        self.assertFalse(r["worker_stack_lifetime_proven"])
        self.assertFalse(r["source_game_thread_can_be_reused"])
        self.assertFalse(r["network_enabled"])
        with self.assertRaises(v.ThreadContextError):
            v.compare(example("IPKE","same"),example("IPKE","same"))

    def test_cli_refuses_to_overwrite_rom(self):
        with tempfile.TemporaryDirectory() as directory:
            hg=Path(directory)/"HeartGold.nds"
            ss=Path(directory)/"SoulSilver.nds"
            hg.write_bytes(b"HG")
            ss.write_bytes(b"SS")
            data=hg.read_bytes()
            self.assertEqual(v.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),data)
            self.assertEqual(v.main([str(hg),str(hg)]),2)


if __name__=="__main__":
    unittest.main()
