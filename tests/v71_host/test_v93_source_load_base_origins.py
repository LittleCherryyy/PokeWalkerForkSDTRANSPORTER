"""V9.3 no-ROM synthetic original ARM9 source-load base-register audit."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"tools/v9_3/hgss_store_address_register_origins.py"
S=importlib.util.spec_from_file_location("v93_synthetic",SRC)
m=importlib.util.module_from_spec(S)
S.loader.exec_module(m)
F=ROOT/"tests/v71_host/test_v90_arm9_scheduler_windows.py"
T=importlib.util.spec_from_file_location("v93_v90_fixture",F)
t=importlib.util.module_from_spec(T)
T.loader.exec_module(t)
BASE=t.BASE


def fixture(code="IPKE"):
    img,meta=t.fixture(code)
    def write(pc,w):
        struct.pack_into("<I",img,pc-BASE,w)
    # All three V9.2 report results are LDR r1 -> one of r0/r8/r7
    # immediately before the matching store. No actual RAM reads.
    write(0x020D1898,0xE1A00004) # MOV r0,r4 (hypothesis only)
    write(0x020D189C,0xE5901000) # LDR r1,[r0]
    # This later literal LDR r0 overwrites the *prior* r0, and only
    # supplies the store DESTINATION (original v9.0 anchor at 18A0).
    write(0x020D2028,0xE59F8078) # LDR r8,[PC,#0x78] -> 20A8
    write(0x020D20A8,0x021E3864) # known aligned original RAM value
    write(0x020D202C,0xE5981000) # LDR r1,[r8]
    write(0x020D20C8,0xE5967004) # LDR r7,[r6,#4]
    write(0x020D20CC,0xE5971000) # LDR r1,[r7]
    # Callback matches V9.2 on real HGSS: STR r5,[r1] at 21D8,
    # with a branch at 21CC obstructing static r5 provenance.
    # Move source literal to r1 and read into unrelated r2.
    pc=0x020D21D0
    write(pc,0xE59F1000|0xB8) # old literal pc+0xC0, same address
    write(pc+4,0xE5912030) # LDR r2,[r1,#48]
    write(pc+8,0xE5815030) # STR r5,[r1,#48]
    write(pc+12,0xEA000000)
    write(pc-4,0xEA000000)
    for row in meta["direct_accesses"]:
        if row["source_instruction"]==f"0x{pc:08X}":
            row["base_register"]="r1"
            break
    # Chain the same static verifiers that real .nds analysis uses.
    v90=m.v92.v91.v90.analyze_image(img,BASE,meta)
    v91=m.v92.v91.analyze_image(img,BASE,v90)
    v92=m.v92.analyze_image(img,BASE,v91)
    return img,v92


class V93SourceLoadBases(unittest.TestCase):
    def test_a_old_r0_is_overwritten_by_later_literal_for_store(self):
        img,old=fixture()
        out=m.analyze_image(img,BASE,old)
        a=out["records"]["scheduler_list_store_a"]
        self.assertEqual(a["source_load_pc"],"0x020D189C")
        self.assertEqual(a["source_load_base_register"],"r0")
        self.assertTrue(a["source_base_overwritten_by_later_store_literal"])
        self.assertEqual(a["store_destination_literal_pc"],"0x020D18A0")
        self.assertEqual(a["source_base_origin_before_load"]["kind"],
                         "register_copy")
        self.assertEqual(a["source_base_origin_before_load"]["from_register"],
                         "r4")
        self.assertIsNone(a["static_address_if_direct_original_literal"])
        self.assertFalse(a["live_runtime_address_register_known"])

    def test_b_pc_literal_source_only_classifies_static_address(self):
        img,old=fixture()
        b=m.analyze_image(img,BASE,old)["records"]["scheduler_list_store_b"]
        self.assertEqual(b["source_load_pc"],"0x020D202C")
        self.assertEqual(b["source_load_base_register"],"r8")
        self.assertFalse(b["source_base_overwritten_by_later_store_literal"])
        self.assertEqual(b["source_base_origin_before_load"]["kind"],
                         "pc_literal_value")
        self.assertEqual(b["source_base_origin_before_load"]["safe_constant"],
                         "0x021E3864")
        self.assertEqual(b["static_address_if_direct_original_literal"],
                         "0x021E3864")
        self.assertTrue(b["static_address_is_not_a_runtime_memory_read"])

    def test_c_runtime_loaded_address_never_followed(self):
        img,old=fixture()
        c=m.analyze_image(img,BASE,old)["records"]["scheduler_list_store_c"]
        self.assertEqual(c["source_load_base_register"],"r7")
        self.assertEqual(c["source_base_origin_before_load"]["kind"],
                         "load_from_unknown_runtime_memory")
        self.assertFalse(c["source_base_origin_before_load"]
                         ["runtime_memory_followed"])
        self.assertIsNone(c["static_address_if_direct_original_literal"])

    def test_callback_branch_boundary_remains_closed(self):
        img,old=fixture()
        result=m.analyze_image(img,BASE,old)
        self.assertEqual(result["callback_0x021E16AC"]["stop_pc"],
                         "0x020D21CC")
        self.assertTrue(result["callback_0x021E16AC"]
                        ["source_value_unknown"])

    def test_load_opcode_tampering_rejected(self):
        img,old=fixture()
        struct.pack_into("<I",img,0x020D202C-BASE,0xEA000000)
        with self.assertRaisesRegex(m.BaseOriginError,"source-load opcode"):
            m.analyze_image(img,BASE,old)

    def test_v92_original_provenance_must_match_exact_pcs(self):
        img,old=fixture()
        old["records"]["scheduler_list_store_b"]["source_register_origin"]["address_register"]="r9"
        with self.assertRaisesRegex(m.BaseOriginError,"V9.2 source writer"):
            m.analyze_image(img,BASE,old)

    def test_title_comparison_does_not_grant_thread_or_network_access(self):
        h,hprev=fixture("IPKE")
        s,sprev=fixture("IPGE")
        out=m.compare(m.analyze_image(h,BASE,hprev),
                      m.analyze_image(s,BASE,sprev))
        self.assertTrue(out["all_three_source_load_base_origins_equivalent"])
        for name in ("scheduler_osthreadinfo_base_proven",
                     "original_thread_object_dereferenced",
                     "safe_to_create_worker_thread",
                     "bootstrap_owned_persistent_stack_proven",
                     "ARM7_WiFi_irq_or_radio_owned","wifi_enabled",
                     "rom_or_save_modified"):
            self.assertFalse(out[name])
        with self.assertRaises(m.BaseOriginError):
            m.compare(m.analyze_image(h,BASE,hprev),
                      m.analyze_image(h,BASE,hprev))

    def test_output_rom_and_save_extensions_refused(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            hg=d/"HeartGold.nds"
            ss=d/"SoulSilver.nds"
            hg.write_bytes(b"HG owner backup")
            ss.write_bytes(b"SS owner backup")
            orig=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),orig)
            self.assertEqual(m.main([str(hg),str(hg)]),2)
            for ext in (".sav",".dsv",".walker",".nds"):
                self.assertEqual(m.main([str(hg),str(ss),"--output",
                                         str(d/("backup"+ext))]),2)


if __name__=="__main__":
    unittest.main()
