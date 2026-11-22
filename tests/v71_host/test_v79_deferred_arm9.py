"""V7.9 bounded ARM9 post-cardRead dry-run scheduling contracts.

Static validation only. The runnable cross-compiler workflow independently
checks Nintendo DSi ARM/Thumb builds and the fixed memory/linker regions.
"""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]/"core/bootstrap/retail"
ARM9=(ROOT/"cardenginei/arm9/source/cardengine.c").read_text(encoding="utf-8")
IGM=(ROOT/"cardenginei/arm9_igm/source/inGameMenu.c").read_text(encoding="utf-8")
HEADER=(ROOT/"common/include/walker_arm9_snapshot.h").read_text(encoding="utf-8")

NTR_GATE="#if !defined(TWLSDK) && !defined(B4DS) && !defined(DLDI) && !defined(GSDD)"


class V79DeferredArm9(unittest.TestCase):
    def test_snapshot_tail_append_only(self):
        fields=re.findall(r"\bu32 (\w+);",HEADER)
        self.assertEqual(fields[:8],[
            "magic","timer3","ie","ime",
            "romReadCalls","eligibleReadCalls","lastReadCpsrMode","lastReadIme",
        ])
        self.assertEqual(fields[8:],[
            "postReadEligibleCalls","dryRunQueued","dryRunDone","dryRunPending",
        ])
        self.assertIn("walkerArm9DryRunQueued,",ARM9)
        self.assertIn("walkerArm9DryRunDone,",ARM9)

    def test_menu_exit_queues_but_does_not_complete(self):
        start=ARM9.index("void inGameMenu(s32* exRegisters) {")
        end=ARM9.index("void myIrqHandlerVcount(void)",start)
        menu=ARM9[start:end]
        self.assertIn("leaveCriticalSection(oldIME);",menu)
        self.assertIn("walkerArm9DryRunPending=1u;",menu)
        self.assertIn("walkerArm9DryRunQueued++;",menu)
        self.assertIn("!exRegisters",menu)
        self.assertIn("!walkerArm9DryRunPending",menu)
        self.assertLess(menu.index("leaveCriticalSection(oldIME);"),
                        menu.index("walkerArm9DryRunPending=1u;"))
        self.assertNotIn("walkerArm9DryRunDone++",menu)
        self.assertNotIn("Wifi_Init(",menu)
        self.assertNotIn("SOC_Connect(",menu)

    def test_read_completion_consumes_dry_run_in_constant_time(self):
        a=ARM9.index("void cardRead(u32* cacheStruct")
        b=ARM9.index("/*void cardPullOut",a)
        fn=ARM9[a:b]
        io=fn.index("cardReadNormal(dst, src, len);")
        hook=fn.index("walkerArm9PostEligibleCalls++")
        self.assertLess(io,hook)
        self.assertIn("postMode=walkerArm9GetCpsrMode();",fn)
        self.assertIn("postMode==0x10u || postMode==0x13u || postMode==0x1fu",fn)
        self.assertIn("(REG_IME & 1u)",fn)
        self.assertIn("if (walkerArm9DryRunPending)",fn)
        self.assertIn("walkerArm9DryRunPending=0u;",fn)
        self.assertIn("walkerArm9DryRunDone++;",fn)
        self.assertLess(fn.index("walkerArm9DryRunPending=0u;"),
                        fn.index("walkerArm9DryRunDone++;"))
        tail=fn[fn.index("/* Read/write operations above have returned."): ]
        for banned in ("waitForArm7(","IPC_SendSync(","SOC_","WCM_",
                       "fileRead(","fileWrite(","walkerWrite(","swiDelay(",
                       "REG_IE =","REG_IME ="):
            self.assertNotIn(banned,tail)

    def test_all_observation_code_is_ntr_only(self):
        self.assertEqual(ARM9.count(NTR_GATE),4)
        self.assertIn("#if defined(DLDI) || defined(GSDD)",ARM9)
        self.assertIn("(const WalkerArm9Snapshot*)0",ARM9)

    def test_igm_screen_cannot_claim_wifi_ready(self):
        self.assertIn("V7.9 ARM9 DEFERRED",IGM)
        self.assertIn("walkerArm9PreWrapper.postReadEligibleCalls",IGM)
        self.assertIn("walkerArm9PreWrapper.dryRunQueued",IGM)
        self.assertIn("walkerArm9PreWrapper.dryRunDone",IGM)
        self.assertIn("Dry run: no network I/O",IGM)
        self.assertIn("Wi-Fi: NOT ENABLED",IGM)
        self.assertNotIn("Wifi_InitDefault(",IGM)


if __name__=="__main__":
    unittest.main()
