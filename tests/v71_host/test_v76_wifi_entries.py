"""Synthetic ARM-state V7.6 veneer and safety tests, with no copyrighted ROM."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

P=Path(__file__).resolve().parents[2]/"tools/v7_6/hgss_wifi_entry_audit.py"
spec=importlib.util.spec_from_file_location("v76_entry_probe",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
BASE=0x02000000


def word(buf,at,value):
    struct.pack_into("<I",buf,at-BASE,value)


class EntryTests(unittest.TestCase):
    def test_arm_b_forward_and_prologue(self):
        buf=bytearray(256)
        pc=BASE+0x20
        dest=BASE+0x70
        disp=((dest-pc-8)>>2)&0xFFFFFF
        word(buf,pc,0xEA000000|disp)
        word(buf,dest,0xE92D4010)
        trace,final,why=m.trace_target(buf,BASE,pc)
        self.assertEqual(len(trace),2)
        self.assertEqual(final,dest)
        self.assertEqual(trace[0]["finding"],"ARM unconditional B")
        self.assertIn("prologue",trace[1]["finding"])

    def test_arm_b_backward_and_cyclic(self):
        buf=bytearray(256)
        pc=BASE+0x80
        dest=BASE+0x40
        disp=((dest-pc-8)>>2)&0xFFFFFF
        word(buf,pc,0xEA000000|disp)
        word(buf,dest,0xE92D4008)
        _,end,_=m.trace_target(buf,BASE,pc)
        self.assertEqual(end,dest)
        word(buf,dest,0xEA000000|(((pc-dest-8)>>2)&0xFFFFFF))
        _,end,why=m.trace_target(buf,BASE,pc)
        self.assertIsNone(end)
        self.assertEqual(why,"cycle")

    def test_arm_pc_literal_veneer(self):
        buf=bytearray(256)
        pc=BASE+0x20
        dest=BASE+0xA0
        word(buf,pc,0xE59FF000)  # LDR pc,[pc,#0], literal at +8
        word(buf,pc+8,dest)
        word(buf,dest,0xE24DD010)
        trace,end,reason=m.trace_target(buf,BASE,pc)
        self.assertEqual(end,dest)
        self.assertEqual(trace[0]["next_address"],f"0x{dest:08X}")

    def test_arm_ip_bx_veneer(self):
        buf=bytearray(256)
        pc=BASE+0x20
        dest=BASE+0xC0
        word(buf,pc,0xE59FC004)
        word(buf,pc+4,0xE12FFF1C)  # BX ip
        word(buf,pc+12,dest)
        word(buf,dest,0xE92D4010)
        trace,end,reason=m.trace_target(buf,BASE,pc)
        self.assertEqual(end,dest)
        self.assertEqual(trace[0]["finding"],"ARM LDR ip + BX ip")

    def test_malformed_jump_fails_closed(self):
        buf=bytearray(256)
        pc=BASE+0x20
        word(buf,pc,0xE59FF000)
        word(buf,pc+8,0x03000000)
        trace,end,reason=m.trace_target(buf,BASE,pc)
        self.assertIsNone(end)
        self.assertEqual(reason,"outside static image")
        with self.assertRaises(m.EntryAuditError):
            m.read_arm(buf,BASE,BASE+257)
        with self.assertRaises(m.EntryAuditError):
            m.read_arm(buf,BASE,BASE+1)

    def test_does_not_treat_bl_entry_as_unconditional_veneer(self):
        buf=bytearray(256)
        pc=BASE+0x20
        word(buf,pc,0xEB000002)
        trace,end,_=m.trace_target(buf,BASE,pc)
        self.assertEqual(end,pc)
        self.assertIn("BL at entry",trace[0]["finding"])

    def test_comparison_never_grants_wifi_permission(self):
        def sample(code, hashval):
            return {"game_code":code,"rom_sha1":"abc",
                    "arm9_runtime_sha256":"fff",
                    "target_entries":{
                        name:{
                            "immediate_target":f"0x{dest:08X}",
                            "terminal_candidate_address":f"0x{dest:08X}",
                            "entry_trace":[{"code_window_sha256":hashval}],
                        } for name,dest in m.EXPECTED.items()
                    }}
        result=m.compare(sample("IPKE","a"),sample("IPGE","a"))
        self.assertEqual(len(result["comparisons"]),5)
        self.assertTrue(all(e["same_terminal_32byte_fingerprint"] for e in result["comparisons"]))
        self.assertFalse(result["wifi_abi_verified"])
        self.assertFalse(result["function_execution_allowed"])
        self.assertTrue(result["no_rom_bytes_exported"])

    def test_source_rom_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"file.nds"
            other=Path(t)/"other.nds"
            path.write_bytes(b"first ROM placeholder")
            other.write_bytes(b"second ROM placeholder")
            before=path.read_bytes()
            self.assertEqual(m.main([str(path),str(other),"--output",str(path)]),2)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(m.main([str(path),str(path)]),2)


if __name__=="__main__":
    unittest.main()
