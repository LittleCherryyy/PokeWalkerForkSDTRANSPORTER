"""V9.2 backward ARM9 register-value source: no-ROM synthetic tests."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
TOOL=ROOT/"tools/v9_2/hgss_store_value_backtrace.py"
SPEC=importlib.util.spec_from_file_location("v92_backtrace_test",TOOL)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
OLD=ROOT/"tests/v71_host/test_v90_arm9_scheduler_windows.py"
S=importlib.util.spec_from_file_location("v92_old_fixture",OLD)
t=importlib.util.module_from_spec(S)
S.loader.exec_module(t)
BASE=t.BASE


def fixture(code="IPKE"):
    img,upstream=t.fixture(code)
    def put(addr,inst):
        struct.pack_into("<I",img,addr-BASE,inst)
    # A8 store A: r1 = immediate 0 before literal LDR r0 = 167C
    put(0x020D189C,0xE3A01000)  # MOV r1,#0
    # A8 store B: read unknown runtime RAM into r2, MOV to r1.
    put(0x020D2028,0xE5942000)  # LDR r2,[r4,#0] unknown
    put(0x020D202C,0xE1A01002)  # MOV r1,r2
    # A8 store C: MOV r1,r1 -> skip; unknown predecessor
    put(0x020D20CC,0xE1A01001)
    # Callback: first LDR r1,[r0,#48] then STR r1,[r0,#48].
    # This allows identifying the preceding LDR as its nearest writer.
    put(0x020D21D8,0xE5801030)
    put(0x020D21DC,0xEA000000)
    # V9.0 and V9.1 metadata are reconstructed synthetically; do not
    # compare hash values against real ROMs in this host test.
    older=m.v91.v90.analyze_image(img,BASE,upstream)
    prior=m.v91.analyze_image(img,BASE,older)
    return img,prior


class V92OriginTests(unittest.TestCase):
    def test_immediate_zero_writer_precedes_known_original_list_store(self):
        img,_=fixture()
        rec=m._origin(img,BASE,1,0x020D18A0,0x020D1880,0)
        self.assertEqual(rec["kind"],"mov_immediate")
        self.assertEqual(rec["safe_constant"],0)
        self.assertEqual(rec["writer_pc"],"0x020D189C")
        self.assertFalse(rec["actual_ram_read"])

    def test_chain_moving_value_from_unknown_ram_is_never_dereferenced(self):
        img,_=fixture()
        rec=m._origin(img,BASE,1,0x020D2030,0x020D2004,0)
        self.assertEqual(rec["kind"],"register_copy")
        self.assertEqual(rec["from_register"],"r2")
        self.assertEqual(rec["source"]["kind"],"load_from_unknown_runtime_memory")
        self.assertFalse(rec["source"]["runtime_memory_followed"])

    def test_unmodeled_predecessor_fails_closed(self):
        img,_=fixture()
        rec=m._origin(img,BASE,1,0x020D20D0,0x020D20A8,0)
        self.assertEqual(rec["kind"],"unresolved")
        self.assertIn("conditional instruction",rec["reason"])

    def test_full_four_original_store_anchors_are_checked(self):
        img,prior=fixture()
        out=m.analyze_image(img,BASE,prior)
        self.assertTrue(out["all_original_v91_store_anchors_validated"])
        self.assertEqual(len(out["records"]),4)
        self.assertEqual(out["records"]["scheduler_list_store_a"]
                         ["source_register_origin"]["kind"],"mov_immediate")
        self.assertEqual(out["records"]["scheduler_list_store_b"]
                         ["source_register_origin"]["kind"],"register_copy")
        self.assertEqual(out["records"]["callback_candidate_read"]
                         ["source_register_origin"]["kind"],
                         "load_from_unknown_runtime_memory")
        for rec in out["records"].values():
            self.assertFalse(rec["executed_path_verified"])
            self.assertFalse(rec["true_thread_field_verified"])
            self.assertFalse(rec["actual_runtime_register_value_known"])
            self.assertFalse(rec["rom_or_ram_write_performed"])

    def test_original_store_opcode_mismatch_is_refused(self):
        img,prior=fixture()
        pc=0x020D18A4
        struct.pack_into("<I",img,pc-BASE,0xEA000000)
        with self.assertRaisesRegex(m.BacktraceError,"store opcode"):
            m.analyze_image(img,BASE,prior)

    def test_a8_and_ac_backtraces_match_synthetically_across_games(self):
        img_a,prior_a=fixture("IPKE")
        img_b,prior_b=fixture("IPGE")
        a=m.analyze_image(img_a,BASE,prior_a)
        b=m.analyze_image(img_b,BASE,prior_b)
        result=m.compare(a,b)
        self.assertTrue(result["all_four_store_writer_traces_equivalent"])
        for gate in ("actual_OSi_ThreadInfo_structure_verified",
                     "actual_thread_objects_read","safe_to_create_worker_thread",
                     "bootstrap_owned_long_lived_stack_verified",
                     "ARM7_WiFi_IRQ_ownership_proven","wifi_enabled",
                     "rom_save_or_walker_modified"):
            self.assertFalse(result[gate])
        with self.assertRaises(m.BacktraceError):
            m.compare(a,a)

    def test_branch_and_condition_barriers_stop_backtracking(self):
        img,prior=fixture()
        for ins,expected in ((0xEA000000,"branch or BX/BLX"),
                             (0x1A000000,"conditional instruction")):
            a=0x020D189C
            struct.pack_into("<I",img,a-BASE,ins)
            result=m._origin(img,BASE,1,a,a-8,0)
            self.assertEqual(result["kind"],"unresolved")
            self.assertIn(expected,result["reason"])

    def test_outputs_cannot_overwrite_rom_or_save_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            hg=Path(tmp)/"HeartGold.nds"
            ss=Path(tmp)/"SoulSilver.nds"
            hg.write_bytes(b"Original HG")
            ss.write_bytes(b"Original SS")
            old=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),old)
            for suffix in (".sav",".dsv",".walker",".nds"):
                self.assertEqual(m.main([
                    str(hg),str(ss),"--output",str(Path(tmp)/("data"+suffix))
                ]),2)

if __name__=="__main__":
    unittest.main()
