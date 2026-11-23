"""V9.0 no-ROM synthetic ARM9 scheduler literal window tests."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[2]
SRC=HERE/"tools/v9_0/hgss_arm9_thread_trace_windows.py"
spec=importlib.util.spec_from_file_location("v90_thread_windows",SRC)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE=0x02000000


def fixture(code="IPKE"):
    image=bytearray(0x120000) # include 0x02111908 original site
    def setword(address,value):
        struct.pack_into("<I",image,address-BASE,value)
    for i,opcode in enumerate(m.v84.ENTRY_OPCODES):
        setword(m.v84.ENTRY+i*4,opcode)
    records=[]
    for name,(pc,target,kind,width) in m.ANCHORS.items():
        # Synthetic literal site is within 12-bit PC-relative reach.
        candidate_base=(
            0x021E16A0 if name in (
                "halfword_header_control","current_candidate_read"
            ) else 0x021E167C
        )
        if name=="legacy_candidate_169c":
            candidate_base=0x021E167C
        if name.startswith("scheduler_list_"):
            candidate_base=0x021E167C
        if name=="callback_candidate_read":
            candidate_base=0x021E167C
        delta=target-candidate_base
        assert 0<=delta<=0x80
        literal=pc+0xC0
        setword(pc,0xE59F0000|(literal-pc-8))  # r0 literal LDR
        setword(literal,candidate_base)
        if width=="halfword":
            # AL LDRH r1,[r0,#0] immediate
            setword(pc+4,0xE1D010B0)
        else:
            setword(pc+4,0xE5901000+delta if kind=="load"
                    else 0xE5801000+delta)
        # No invented control flow: stop at an unconditional branch.
        setword(pc+8,0xEA000000)
        records.append({
            "source_instruction":f"0x{pc:08X}",
            "source_literal":f"0x{literal:08X}",
            "literal_value":f"0x{candidate_base:08X}",
            "effective_address":f"0x{target:08X}",
            "access":kind,"width":width,"base_register":"r0",
        })
    return image,{
        "game_code":code,
        "direct_accesses":records,
        "direct_access_count":38,
        "newly_recognized_arm_halfword_access_count":1,
    }


class BoundedSchedulerTests(unittest.TestCase):
    def test_each_anchor_has_bounded_semantics_without_original_code_bytes(self):
        image,upstream=fixture()
        r=m.analyze_image(image,BASE,upstream)
        self.assertEqual(len(r["records"]),8)
        self.assertTrue(r["all_original_v89_anchors_validated"])
        self.assertFalse(r["thread_fields_proven"])
        for name,record in r["records"].items():
            self.assertEqual(len(record["source_32byte_sha256"]),64)
            self.assertEqual(record["semantic_steps"][0]["kind"],
                             "fixed_base_memory_access")
            self.assertEqual(record["semantic_steps"][1]["kind"],
                             "stop_control_flow")
            self.assertFalse(record["traced_executable_path_proven"])
            self.assertFalse(record["thread_pointer_dereferenced"])
            self.assertEqual(record["max_instructions_including_source"],8)
            self.assertNotIn("instruction_hex",record)

    def test_register_copy_and_add_only_track_known_original_literal(self):
        base=0x020D1600
        pc=0x020D1620
        code=bytearray(0x100)
        for i,word in enumerate((
            0xE59F0004, # first source opcode (not decoded by helper)
            0xE1A05000, # MOV r5,r0
            0xE2855004, # ADD r5,r5,#4
            0xE5951000, # LDR r1,[r5] -> A4
            0xEA000000, # stop branch
            0xE5901000, # must never be reached
        )):
            struct.pack_into("<I",code,pc-base+i*4,word)
        trace=m.trace_straight_line(code,base,pc,0,0x021E16A0)
        steps=trace["semantic_steps"]
        self.assertEqual([x["kind"] for x in steps],[
            "mov_register","add_immediate","fixed_base_memory_access",
            "stop_control_flow"
        ])
        self.assertTrue(steps[1]["tracked_pointer_propagated"])
        self.assertEqual(steps[2]["effective_address"],"0x021E16A4")
        self.assertFalse(steps[2]["actual_memory_dereferenced"])

    def test_unknown_branch_or_conditional_stops_without_pointer_following(self):
        for inst,kind in (
            (0x1A000000,"stop_conditional_instruction"),
            (0xEA000000,"stop_control_flow"),
            (0xE12FFF10,"stop_control_flow"),
            (0xE1A0F000,"stop_pc_write"),
            (0xE7901000,"stop_unrecognized_instruction"),
        ):
            code=bytearray(0x40)
            struct.pack_into("<I",code,4,inst)
            result=m.trace_straight_line(code,0x02000000,
                                         0x02000000,0,0x021E16A0)
            # Insert at +4 (pc+4) after initial source.
            self.assertEqual(result["semantic_steps"][0]["kind"],kind)
            self.assertEqual(result["instructions_after_source_examined"],1)

    def test_comparison_marks_syntactic_match_not_executable_proof(self):
        img_a,meta_a=fixture("IPKE")
        img_b,meta_b=fixture("IPGE")
        a=m.analyze_image(img_a,BASE,meta_a)
        b=m.analyze_image(img_b,BASE,meta_b)
        r=m.compare(a,b)
        self.assertTrue(r["all_eight_anchor_windows_shared"]["matching_code_hash_and_semantics"])
        self.assertEqual(r["all_eight_anchor_windows_shared"]["number"],8)
        self.assertFalse(r["actual_OSi_ThreadInfo_base_proven"])
        self.assertFalse(r["safe_to_create_or_wakeup_thread"])
        self.assertFalse(r["ARM7_radio_ownership_proven"])
        self.assertFalse(r["wifi_enabled"])
        with self.assertRaises(m.TraceError):
            m.compare(a,a)

    def test_guard_rejects_modified_original_signature_and_followup(self):
        image,meta=fixture()
        first_pc=m.ANCHORS["halfword_header_control"][0]
        struct.pack_into("<I",image,first_pc-BASE+4,0xEA000000)
        with self.assertRaisesRegex(m.TraceError,"no longer matches V8.9"):
            m.analyze_image(image,BASE,meta)
        image,meta=fixture()
        image[m.v84.ENTRY-BASE]=0
        with self.assertRaises(m.v84.ThreadXrefError):
            m.analyze_image(image,BASE,meta)

    def test_source_and_output_are_distinct_original_rom_backups(self):
        with tempfile.TemporaryDirectory() as d:
            hg=Path(d)/"HeartGold.nds"
            ss=Path(d)/"SoulSilver.nds"
            hg.write_bytes(b"HG-original")
            ss.write_bytes(b"SS-original")
            original=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),original)
            self.assertEqual(m.main([str(hg),str(hg)]),2)


if __name__=="__main__":
    unittest.main()
