"""V9.1 strict ARM9 register provenance, eight anchor synthetic no-ROM tests."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"tools/v9_1/hgss_register_provenance.py"
SPEC=importlib.util.spec_from_file_location("v91_synthetic",SCRIPT)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
OLD=ROOT/"tests/v71_host/test_v90_arm9_scheduler_windows.py"
T_SPEC=importlib.util.spec_from_file_location("v90_existing_fixture",OLD)
t=importlib.util.module_from_spec(T_SPEC)
T_SPEC.loader.exec_module(t)
BASE=t.BASE


def fixture(code="IPKE",extra=True):
    image,meta=t.fixture(code)
    if extra:
        def put(addr,word):
            struct.pack_into("<I",image,addr-BASE,word)
        # LDR [r0,+32], ADD r1,+1, STR r1 [r0,+32], branch.
        pc=m.v90.ANCHORS["legacy_candidate_169c"][0]
        put(pc+8,0xE2811001)  # ADD r1,r1,#1
        put(pc+12,0xE5801020) # STR r1,[r0,#32]
        put(pc+16,0xEA000000)
        # LDRH r1,[r0], CMP r1,#0, then conditional BNE.
        pc=m.v90.ANCHORS["halfword_header_control"][0]
        put(pc+8,0xE3510000) # CMP r1,#0
        put(pc+12,0x1A000000) # stop conditional branch
        # Read and store callback candidate without ADD.
        pc=m.v90.ANCHORS["callback_candidate_read"][0]
        put(pc+8,0xE5801030) # STR r1,[r0,#48]
        put(pc+12,0xEA000000)
    return image,meta


class V91ProvenanceTests(unittest.TestCase):
    def test_incrementing_same_word_is_syntactic_rmw_candidate(self):
        image,_=fixture()
        pc=m.v90.ANCHORS["legacy_candidate_169c"][0]
        r=m.trace_provenance(image,BASE,pc,0,0x021E167C)
        self.assertEqual([x["kind"] for x in r["steps"]],[
            "memory_read","increment_or_decrement","memory_write",
            "stop_control_flow"
        ])
        self.assertEqual(len(r["read_modify_write_same_address_candidates"]),1)
        rmw=r["read_modify_write_same_address_candidates"][0]
        self.assertEqual(rmw["effective_address"],"0x021E169C")
        self.assertEqual(rmw["provenance"]["transforms"],[
            {"operation":"add","immediate":1}
        ])
        self.assertEqual(r["steps"][2]["value_provenance"]["read_address"],
                         "0x021E169C")
        self.assertTrue(r["steps"][2]["value_originates_at_same_address"])
        self.assertFalse(r["live_RAM_dereferences"])

    def test_halfword_loaded_value_is_compared_to_zero(self):
        image,_=fixture()
        pc=m.v90.ANCHORS["halfword_header_control"][0]
        r=m.trace_provenance(image,BASE,pc,0,0x021E16A0)
        self.assertEqual([x["kind"] for x in r["steps"]],[
            "memory_read","compare_value","stop_conditional_instruction"
        ])
        self.assertEqual(len(r["compare_loaded_halfword_or_word_to_zero_candidates"]),1)
        fact=r["compare_loaded_halfword_or_word_to_zero_candidates"][0]
        self.assertEqual(fact["provenance"]["read_address"],"0x021E16A0")
        self.assertEqual(fact["provenance"]["width"],"halfword")
        self.assertFalse(r["steps"][1]["actual_test_outcome_known"])

    def test_identical_source_store_does_not_imply_increment(self):
        image,_=fixture()
        pc=m.v90.ANCHORS["callback_candidate_read"][0]
        r=m.trace_provenance(image,BASE,pc,0,0x021E167C)
        self.assertEqual([x["kind"] for x in r["steps"]],[
            "memory_read","memory_write","stop_control_flow"
        ])
        self.assertEqual(r["steps"][1]["value_provenance"]["read_address"],
                         "0x021E16AC")
        self.assertTrue(r["steps"][1]["value_originates_at_same_address"])
        self.assertFalse(r["steps"][1]["read_modify_write_candidate"])
        self.assertEqual(r["read_modify_write_same_address_candidates"],[])

    def test_opaque_memory_read_does_not_become_pointer_to_follow(self):
        image,_=fixture()
        pc=m.v90.ANCHORS["current_candidate_read"][0]
        # Loaded r1 from A4, then LDR r2,[r1,#4] has unknown target.
        struct.pack_into("<I",image,pc-BASE+8,0xE5912004)
        struct.pack_into("<I",image,pc-BASE+12,0xEA000000)
        r=m.trace_provenance(image,BASE,pc,0,0x021E16A0)
        self.assertEqual(r["steps"][0]["effective_address"],"0x021E16A4")
        self.assertIsNone(r["steps"][1]["effective_address"])
        self.assertFalse(r["steps"][1]["effective_address_derived_from_literal"])
        self.assertFalse(r["live_RAM_dereferences"])

    def test_reg_copy_transform_provenance_without_actual_ram_read(self):
        pc=0x02001000
        img=bytearray(128)
        words=(
            0xE59F0000, # source LDR literal (not analyzed in helper)
            0xE5901004, # LDR r1,[r0,#4] -> provenance A4
            0xE1A02001, # MOV r2,r1
            0xE2822001, # ADD r2,r2,#1
            0xE5802004, # STR r2,[r0,#4]
            0xEA000000,
        )
        for i,w in enumerate(words):
            struct.pack_into("<I",img,i*4,w)
        r=m.trace_provenance(img,pc,pc,0,0x021E16A0)
        self.assertEqual(len(r["read_modify_write_same_address_candidates"]),1)
        self.assertEqual(r["read_modify_write_same_address_candidates"][0]
                         ["provenance"]["read_address"],"0x021E16A4")
        self.assertFalse(r["steps"][1]["pointer_literal_propagated"])

    def test_original_v90_reconstruction_must_match_all_eight_sites(self):
        image,meta=fixture()
        old=m.v90.analyze_image(image,BASE,meta)
        new=m.analyze_image(image,BASE,old)
        self.assertEqual(len(new["records"]),8)
        self.assertTrue(new["all_eight_original_anchor_checks_passed"])
        self.assertFalse(new["verified_OSThreadInfo_base"])
        self.assertFalse(new["wifi_enabled"])
        self.assertFalse(new["original_arm_code_or_rom_bytes_exported"])
        self.assertEqual(len(new["records"]["legacy_candidate_169c"]
                            ["read_modify_write_same_address_candidates"]),1)
        image[m.v90.v84.ENTRY-BASE]=0
        with self.assertRaises(m.v90.v84.ThreadXrefError):
            m.v90.analyze_image(image,BASE,meta)

    def test_identical_roms_do_not_prove_scheduler_or_wifi(self):
        img_a,meta_a=fixture("IPKE")
        img_b,meta_b=fixture("IPGE")
        a=m.analyze_image(img_a,BASE,m.v90.analyze_image(img_a,BASE,meta_a))
        b=m.analyze_image(img_b,BASE,m.v90.analyze_image(img_b,BASE,meta_b))
        output=m.compare(a,b)
        self.assertTrue(output["eight_anchor_provenance_equal"])
        for field in (
            "legacy_OSThreadInfo_at_0x021E169C_confirmed",
            "OSi_ThreadInfo_at_0x021E16A0_confirmed",
            "safe_to_create_or_wakeup_threads",
            "bootstrap_owned_worker_stack_proven",
            "ARM7_wifi_driver_or_irq_owned",
            "wifi_enabled",
        ):
            self.assertFalse(output[field])
        with self.assertRaises(m.ProvenanceError):
            m.compare(a,a)

    def test_malformed_or_overwrite_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            hg=Path(d)/"HeartGold.nds"
            ss=Path(d)/"SoulSilver.nds"
            hg.write_bytes(b"HG")
            ss.write_bytes(b"SS")
            before=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),before)
            for suffix in (".sav",".walker",".dsv"):
                self.assertEqual(m.main([
                    str(hg),str(ss),"--output",str(Path(d)/("backup"+suffix))
                ]),2)
            self.assertEqual(m.main([str(hg),str(hg)]),2)

if __name__=="__main__":
    unittest.main()
