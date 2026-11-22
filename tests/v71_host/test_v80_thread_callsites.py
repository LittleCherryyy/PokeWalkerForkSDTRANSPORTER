"""Synthetic V8.0 HGSS NitroSDK thread-callsite checks; no ROM used."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[2]/"tools/v8_0/hgss_thread_callsite_audit.py"
sp=importlib.util.spec_from_file_location("v80_thread_calls",SCRIPT)
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)


def thumb_call(pc,target,arm=False):
    off=(target-pc-4)&0x7fffff
    if off&1:raise ValueError("unaligned")
    return struct.pack("<HH",0xf000|((off>>12)&0x7ff),
                       (0xe800 if arm else 0xf800)|((off>>1)&0x7ff))


def arm_bl(pc,target):
    return struct.pack("<I",0xeb000000|(((target-pc-8)>>2)&0xffffff))


class ThreadAuditTests(unittest.TestCase):
    def test_callsite_table_is_known_and_narrow(self):
        self.assertEqual(len(m.SITES),5)
        self.assertEqual([(a,b,c,d) for a,b,c,d,*_ in m.SITES],[
            ("OS_IsThreadAvailable",13,"thumb",0x02226DD4),
            ("OS_CreateThread",13,"thumb",0x02226E00),
            ("OS_WakeupThreadDirect",13,"thumb",0x02226E36),
            ("OS_CreateThread",39,"arm",0x022299AC),
            ("OS_WakeupThreadDirect",39,"arm",0x022299B4),
        ])

    def test_thumb_os_thread_calls_decode_and_check_neighbor(self):
        for site in (x for x in m.SITES if x[2]=="thumb"):
            name,overlay,isa,pc,side,neighbor=site
            load=pc-0x40
            image=bytearray(0x100)
            place=pc-load
            dest=0x020AA000
            image[place:place+4]=thumb_call(pc,dest,arm=True)
            other=place-2 if side=="before" else place+4
            struct.pack_into("<H",image,other,neighbor)
            r=m.resolve_thread_callsite(image,load,site)
            self.assertEqual(r["target"],f"0x{dest:08X}")
            self.assertEqual(r["target_mode"],"ARM (BLX)")
            self.assertFalse(r["safe_to_create_thread"])
            struct.pack_into("<H",image,other,0)
            with self.assertRaisesRegex(m.ThreadAuditError,"mismatch"):
                m.resolve_thread_callsite(image,load,site)

    def test_arm_os_thread_calls_decode_and_check_neighbor(self):
        for site in (x for x in m.SITES if x[2]=="arm"):
            name,overlay,isa,pc,side,neighbor=site
            load=pc-0x40
            image=bytearray(0x100)
            place=pc-load
            dest=0x020ACC00
            image[place:place+4]=arm_bl(pc,dest)
            other=place-4 if side=="before" else place+4
            struct.pack_into("<I",image,other,neighbor)
            r=m.resolve_thread_callsite(image,load,site)
            self.assertEqual(r["target"],f"0x{dest:08X}")
            self.assertEqual(r["target_mode"],"ARM (BL)")
            struct.pack_into("<I",image,place,0)
            with self.assertRaises(m.ThreadAuditError):
                m.resolve_thread_callsite(image,load,site)

    def test_bounded_fingerprint_only(self):
        import hashlib
        data=bytes(range(128))
        self.assertEqual(m.read_arm9_window(data,0x02000000,0x02000010),
                         hashlib.sha256(data[16:48]).hexdigest())
        self.assertIsNone(m.read_arm9_window(data,0x02000000,0x01ffffff))
        self.assertIsNone(m.read_arm9_window(data,0x02000000,0x02000070))

    def test_comparison_no_thread_permission(self):
        def fixture(game,shift=0):
            return {
                "game_code":game, "rom_sha1":"dummy",
                "arm9_runtime_sha256":"dummy",
                "callsites":[{
                    "name":name,"overlay":ov,"callsite":f"0x{pc:08X}",
                    "target":f"0x{0x020D0000+i*4+shift:08X}",
                    "target_mode":"ARM (BL)",
                    "target_region":"ARM9 static executable range (not ABI-verified)",
                    "static_arm9_32byte_sha256":"hash",
                } for i,(name,ov,isa,pc,side,neighbor) in enumerate(m.SITES)]
            }
        result=m.compare(fixture("IPKE"),fixture("IPGE"))
        self.assertEqual(result["same_immediate_targets"],5)
        self.assertFalse(result["game_scheduler_abi_verified"])
        self.assertFalse(result["independent_arm9_worker_verified"])
        self.assertFalse(result["network_enabled"])
        self.assertFalse(result["arm7_wm_radio_owned_by_bridge"])
        different=m.compare(fixture("IPKE"),fixture("IPGE",shift=4))
        self.assertEqual(different["same_immediate_targets"],0)
        with self.assertRaises(m.ThreadAuditError):
            m.compare(fixture("IPKE"),fixture("IPKE"))

    def test_cli_refuses_overwrite_and_duplicate(self):
        with tempfile.TemporaryDirectory() as root:
            hg=Path(root)/"hg.nds"
            ss=Path(root)/"ss.nds"
            hg.write_bytes(b"HG")
            ss.write_bytes(b"SS")
            save=hg.read_bytes()
            self.assertEqual(m.main([str(hg),str(ss),"--output",str(hg)]),2)
            self.assertEqual(hg.read_bytes(),save)
            self.assertEqual(m.main([str(hg),str(hg)]),2)


if __name__=="__main__":
    unittest.main()
