"""V7.5 read-only WCM/SOC callsite audit: synthetic instruction tests only.

No proprietary ROM or live Wi-Fi calls are used by CI.
"""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest


P = Path(__file__).resolve().parents[2] / "tools/v7_5/hgss_wifi_call_targets.py"
spec = importlib.util.spec_from_file_location("v75_calls", P)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def thumb_bl_bytes(pc, target):
    delta = target - (pc + 4)
    if (delta & 1) or not -(1 << 22) <= delta < (1 << 22):
        raise ValueError("target not representable")
    displacement = delta & ((1 << 23) - 1)
    return struct.pack("<HH", 0xF000 | ((displacement >> 12) & 0x7FF),
                       0xF800 | ((displacement >> 1) & 0x7FF))


def arm_bl_bytes(pc, target):
    delta = target - pc - 8
    if delta & 3 or not -(1 << 25) <= delta < 1 << 25:
        raise ValueError("invalid ARM BL")
    return struct.pack("<I", 0xEB000000 | ((delta >> 2) & 0xFFFFFF))


class WifiCallsiteTests(unittest.TestCase):
    def test_public_documented_callsites_match_safety_gate(self):
        self.assertEqual(len(mod.SITES), 5)
        self.assertEqual({x[0] for x in mod.SITES},
                         {"WCM_GetPhase","WCM_Init","WCM_StartupAsync",
                          "SOC_Socket","SOC_Connect"})

    def test_thumb_bl_backward_to_main(self):
        pc = 0x02237E0C
        target = 0x02083CD0
        first, second = struct.unpack("<HH", thumb_bl_bytes(pc,target))
        got, kind = mod.thumb_call(first,second,pc)
        self.assertEqual((got, kind),(target,"Thumb (BL)"))
        with self.assertRaises(mod.CallsiteError):
            mod.thumb_call(0xD003,second,pc)

    def test_arm_bl_to_main(self):
        pc = 0x02229C5C
        target = 0x020A4E70
        instr = struct.unpack("<I",arm_bl_bytes(pc,target))[0]
        got, kind = mod.arm_bl(instr,pc)
        self.assertEqual((got,kind),(target,"ARM (BL)"))
        with self.assertRaises(mod.CallsiteError):
            mod.arm_bl(instr ^ 0x10000000,pc)

    def test_thumb_neighbor_must_match_before_reporting_target(self):
        name, ov, mode, pc, expected = mod.SITES[0]
        load = pc-20
        data = bytearray(80)
        target = 0x02083CD0
        data[20:24] = thumb_bl_bytes(pc, target)
        struct.pack_into("<H",data,24,expected)
        result = mod.resolve_site(data,load,name,pc,mode,expected)
        self.assertEqual(result["decoded_immediate_target"],f"0x{target:08X}")
        self.assertFalse(result["target_is_callable_wifi_api"])
        struct.pack_into("<H",data,24,0x2808)
        with self.assertRaisesRegex(mod.CallsiteError,"post-call cmp"):
            mod.resolve_site(data,load,name,pc,mode,expected)

    def test_arm_neighbor_must_match_before_reporting_target(self):
        name, ov, mode, pc, expected = mod.SITES[-1]
        load = pc-20
        data = bytearray(80)
        target = 0x020A4E70
        struct.pack_into("<I",data,16,expected)
        data[20:24] = arm_bl_bytes(pc,target)
        result = mod.resolve_site(data,load,name,pc,mode,expected)
        self.assertEqual(result["decoded_immediate_target"],f"0x{target:08X}")
        struct.pack_into("<I",data,16,0)
        with self.assertRaisesRegex(mod.CallsiteError,"pre-call"):
            mod.resolve_site(data,load,name,pc,mode,expected)

    def test_explicit_range_classifier_not_proof_of_wifi(self):
        ovs = {72:(0x022378C0,b"\0"*2000,{}),
               13:(0x022208E8,b"\0"*20000,{}),
               39:(0x02229000,b"\0"*10000,{})}
        self.assertIn("static executable",mod.region_of(0x02001235,0x02000000,1122040,ovs))
        self.assertIn("overlay 72",mod.region_of(0x02237E0C,0x02000000,1122040,ovs))
        self.assertIn("other area",mod.region_of(0x02300000,0x02000000,1122040,ovs))

    def test_overlay_fat_and_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"fake.bin"
            data=bytearray(0x5000)
            hdr=bytearray(0x200)
            struct.pack_into("<II",hdr,0x50,0x300,64)
            fat=struct.pack("<II",0x2000,0x2010)
            struct.pack_into("<8I",data,0x300,72,0x022378C0,16,0,0,0,0,0)
            struct.pack_into("<8I",data,0x320,72,0x022378C0,16,0,0,0,0,0)
            data[0x2000:0x2010]=bytes(16)
            path.write_bytes(data)
            with path.open("rb") as f:
                with self.assertRaisesRegex(mod.CallsiteError,"expected one"):
                    mod.get_overlay(f,hdr,fat,len(data),72)
            struct.pack_into("<8I",data,0x320,39,0x02239000,16,0,0,0,0,0)
            path.write_bytes(data)
            with path.open("rb") as f:
                load,img,details=mod.get_overlay(f,hdr,fat,len(data),72)
                self.assertEqual(load,0x022378C0)
                self.assertEqual(len(img),16)
                self.assertFalse(details["packed"])

    def test_cross_game_comparison_preserves_fail_closed_gate(self):
        def fixture(code, offset):
            return {
                "game_code":code, "arm9_static_bytes":1122040,
                "callsites":[{
                    "name":name,
                    "caller_address":f"0x{address:08X}",
                    "decoded_immediate_target":f"0x{0x02050000 + i*4 + offset:08X}",
                    "target_region":"ARM9 static executable range (not ABI-verified)",
                } for i, (name, ov, mode, address, neighbor) in enumerate(mod.SITES)],
            }
        hg=fixture("IPKE",0)
        ss=fixture("IPGE",0)
        paired=mod.compare_reports(hg,ss)
        self.assertEqual(paired["total_sites"],5)
        self.assertEqual(paired["same_targets"],5)
        self.assertFalse(paired["wifi_abi_verified"])
        self.assertFalse(paired["function_execution_allowed"])
        ss["callsites"][1]["decoded_immediate_target"]="0x02060000"
        paired=mod.compare_reports(hg,ss)
        self.assertEqual(paired["same_targets"],4)
        with self.assertRaisesRegex(mod.CallsiteError,"one original US"):
            mod.compare_reports(hg,hg)

    def test_output_same_as_source_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"rom.nds"
            p.write_bytes(b"DO NOT OVERWRITE")
            before=p.read_bytes()
            self.assertEqual(mod.main([str(p),"--output",str(p)]),2)
            self.assertEqual(before,p.read_bytes())


if __name__ == "__main__":
    unittest.main()
