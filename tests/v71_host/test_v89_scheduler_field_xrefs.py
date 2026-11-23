"""V8.9 original ARM9 synthetic LDRH/STRH cross-reference semantics tests.

No copyrighted game data, ROM, live RAM, radio or saves required.
"""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

PATH=Path(__file__).resolve().parents[2]/"tools/v8_9/hgss_scheduler_field_xrefs.py"
SPEC=importlib.util.spec_from_file_location("hgss_v89_synthetic",PATH)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
BASE=0x020D1A00


def fixture(game="IPKE"):
    ram=bytearray(0x400)
    def setword(addr,v):
        struct.pack_into("<I",ram,addr-BASE,v)
    for i,w in enumerate(m.v84.ENTRY_OPCODES):
        setword(m.v84.ENTRY+4*i,w)
    refs=[]
    for pc,lit,source,rd,next_word in (
        # LDRH r1,[r0,#2] models legacy u16 max_entry candidate.
        (0x020D1B00,0x020D1BA0,0x021E169C,0,0xE1D010B2),
        # STRH r1,[r2,#0], models u16 store candidate at A0.
        (0x020D1B10,0x020D1BA4,0x021E16A0,2,0xE1C210B0),
        # LDR r2,[r0,#8] -> A8, already V8.5 word recognized.
        (0x020D1B20,0x020D1BA8,0x021E16A0,0,0xE5902008),
        # STR r2,[r3,#0] -> B0, not a valid OSThread pointer proof.
        (0x020D1B30,0x020D1BAC,0x021E16B0,3,0xE5832000),
        # LDR r4,[r0,#44] -> A8, same address via older 167C base.
        (0x020D1B40,0x020D1BB0,0x021E167C,0,0xE590402C),
        # A candidate LDR PC that is not followed by direct register memory.
        (0x020D1B50,0x020D1BB4,0x021E16AC,1,0xE1A00001),
    ):
        offset=lit-pc-8
        assert 0<=offset<=0xfff
        setword(pc,0xE59F0000|(rd<<12)|offset)
        setword(pc+4,next_word)
        setword(lit,source)
        refs.append({
            "instruction_address":f"0x{pc:08X}",
            "literal_address":f"0x{lit:08X}",
            "literal_value":f"0x{source:08X}",
            "register":f"r{rd}",
        })
    return ram,{"game_code":game,"entry_opcode_guard_passed":True,"literal_xrefs":refs}


class V89SchedulerFieldsTests(unittest.TestCase):
    def test_arm_unconditional_immediate_halfword_load(self):
        v=m.decode_arm_immediate_halfword(0xE1D010B2,0)
        self.assertEqual(v["signed_offset"],2)
        self.assertEqual(v["width"],"halfword")
        self.assertEqual(v["access"],"load")
        self.assertFalse(v["field_identity_proven"])

    def test_arm_unconditional_immediate_halfword_store(self):
        v=m.decode_arm_immediate_halfword(0xE1C210B0,2)
        self.assertEqual(v["signed_offset"],0)
        self.assertEqual(v["width"],"halfword")
        self.assertEqual(v["access"],"store")
        self.assertIsNone(m.decode_arm_immediate_halfword(0xE1C210B0,3))

    def test_reject_signed_register_conditional_and_postindex(self):
        self.assertIsNone(m.decode_arm_immediate_halfword(0x11D010B2,0))
        self.assertIsNone(m.decode_arm_immediate_halfword(0xE19010B2,0))
        self.assertIsNone(m.decode_arm_immediate_halfword(0xE0D010B2,0))
        self.assertIsNone(m.decode_arm_immediate_halfword(0xE1D010D2,0))
        self.assertIsNone(m.decode_arm_immediate_halfword(0xE1D018B2,0))

    def test_strict_original_rom_guard_and_one_step_access(self):
        image,meta=fixture()
        r=m.analyze_image(image,BASE,meta)
        self.assertEqual(r["direct_access_count"],5)
        self.assertEqual(r["newly_recognized_arm_halfword_access_count"],2)
        self.assertTrue(r["static_matches_may_be_data"])
        self.assertTrue(r["rom_bytes_exported"] is False)
        actual={(x["effective_address"],x["access"],x["width"])
                for x in r["direct_accesses"]}
        self.assertIn(("0x021E169E","load","halfword"),actual)
        self.assertIn(("0x021E16A0","store","halfword"),actual)
        self.assertIn(("0x021E16A8","load","word"),actual)
        self.assertIn(("0x021E16B0","store","word"),actual)
        self.assertEqual(sum(x["effective_address"]=="0x021E16A8"
                             for x in r["direct_accesses"]),2)
        self.assertTrue(all(not x["proved_scheduler_field"] for x in r["direct_accesses"]))
        image[m.v84.ENTRY-BASE]=0
        with self.assertRaisesRegex(m.v84.ThreadXrefError,"mismatch"):
            m.analyze_image(image,BASE,meta)

    def test_tampered_literal_or_opcode_is_refused(self):
        image,meta=fixture()
        struct.pack_into("<I",image,0x020D1BA0-BASE,0)
        with self.assertRaisesRegex(m.FieldXrefError,"literal address does not match"):
            m.analyze_image(image,BASE,meta)
        image,meta=fixture()
        struct.pack_into("<I",image,0x020D1B20-BASE,0xE1A00000)
        with self.assertRaisesRegex(m.FieldXrefError,"source PC-relative LDR"):
            m.analyze_image(image,BASE,meta)

    def test_cross_title_comparison_does_not_create_thread_rights(self):
        aimg,ameta=fixture("IPKE")
        bimg,bmeta=fixture("IPGE")
        a=m.analyze_image(aimg,BASE,ameta)
        b=m.analyze_image(bimg,BASE,bmeta)
        r=m.compare(a,b)
        self.assertEqual(r["shared_direct_access_count"],5)
        self.assertEqual(r["heartgold_only_accesses"],0)
        self.assertEqual(r["soulsilver_only_accesses"],0)
        legacy=r["hypothesis_legacy_struct_at_0x021e169c"]
        self.assertEqual(legacy["low_half_possible_is_need_rescheduling"],3)
        self.assertEqual(legacy["upper_half_possible_max_entry"],0)
        self.assertEqual(legacy["entry0_if_legacy_layout"],"0x0000001F")
        self.assertFalse(legacy["entry0_valid_aligned_ntr_ram_pointer"])
        for key in ("osthreadinfo_base_confirmed","os_create_thread_safe",
                    "worker_memory_allocation_safe","network_enabled",
                    "arm7_wifi_owned_by_bridge"):
            self.assertFalse(r[key])
        with self.assertRaises(m.FieldXrefError):
            m.compare(a,a)

    def test_command_line_never_overwrites_roms(self):
        with tempfile.TemporaryDirectory() as d:
            hg=Path(d)/"HeartGold.nds"
            ss=Path(d)/"SoulSilver.nds"
            hg.write_bytes(b"HG-owned-original")
            ss.write_bytes(b"SS-owned-original")
            old=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),old)
            self.assertEqual(m.main([str(hg),str(hg)]),2)


if __name__=="__main__":
    unittest.main()
