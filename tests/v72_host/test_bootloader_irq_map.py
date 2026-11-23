"""V7.2.5: check NTR HGSS bootloader-to-IGM read-only IRQ metadata.

Static tests do NOT prove the runtime table's ownership or legal size.
They ensure the actual bootloaderi hook, not the Gen5-only cardengine
patcher, publishes metadata without dereferencing IRQ slot 24.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]/"core/bootstrap/retail"
LOADER=ROOT/"bootloaderi/source/arm7/hook_arm7.c"
HDR=ROOT/"common/include/cardengine_header_arm7.h"
ASM=ROOT/"cardenginei/arm7/source/card_engine_header.s"
A7=ROOT/"cardenginei/arm7/source/inGameMenu.c"
A9=ROOT/"cardenginei/arm9_igm/source/inGameMenu.c"

class BootIrqReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loader=LOADER.read_text()
        cls.hdr=HDR.read_text()
        cls.asm=ASM.read_text()
        cls.a7=A7.read_text()
        cls.a9=A9.read_text()

    def test_metadata_append_only_in_ce7_c_and_asm(self):
        hdr=self.hdr
        asm=self.asm
        fields=("walkerIrqTableAddress","walkerIrqImageStart",
                "walkerIrqImageSize","walkerIrqTableMethod")
        self.assertLess(hdr.index("u32 walkerBootStatus;"),
                        hdr.index("u32 walkerIrqTableAddress;"))
        self.assertIn("u32 walkerDirectLockCluster;", hdr)
        self.assertLess(hdr.index("u32 walkerIrqBootInstalledIpc;"),
                        hdr.index("u32 walkerDirectLockCluster;"))
        self.assertRegex(hdr, r"u32 walkerDirectLockCluster;\s*}\s*cardengineArm7;")
        self.assertLess(hdr.index("u32 walkerIrqTableMethod;"),
                        hdr.index("u32 walkerIrqBootOriginalVblank;"))
        for name in fields:
            self.assertIn("u32 "+name+";",hdr)
            self.assertIn(".global "+name,asm)
            self.assertIn(name+": .word 0",asm)
        self.assertLess(asm.index("walkerBootStatus: .word 0"),
                        asm.index("walkerIrqTableAddress: .word 0"))
        for left,right in zip(fields,fields[1:]):
            self.assertLess(asm.index(left+": .word 0"),
                            asm.index(right+": .word 0"))

    def test_actual_ntr_loader_records_existing_table_no_new_irq_write(self):
        code=self.loader
        self.assertIn("patchOffsetCache.a7IrqHookOffset",code)
        for fragment in (
            "ce7->walkerIrqTableAddress = (u32)hookLocation;",
            "ce7->walkerIrqImageStart = (u32)ndsHeader->arm7destination;",
            "ce7->walkerIrqImageSize = newArm7binarySize;",
            "ce7->walkerIrqTableMethod = walkerIrqMethod;",
            "walkerIrqMethod = 4u;",
            "walkerIrqMethod = 3u;",
        ):
            self.assertIn(fragment,code)
        self.assertLess(code.index("ce7->walkerIrqTableAddress"),
                        code.index("u32* vblankHandler = hookLocation;"))
        self.assertNotIn("hookLocation + 24",code)
        self.assertNotIn("hookLocation[24]",code)

    def test_arm7_readonly_ipc_holds_ack(self):
        a7=self.a7
        section=a7[a7.index("static void walkerIrqTableReadOnlyDiagnostics"):
                    a7.index("static u32 radioIeBeforeMenu")]
        for field in ("walkerIrqTableAddress","walkerIrqImageStart",
                      "walkerIrqImageSize","walkerIrqTableMethod"):
            self.assertIn(field,section)
        self.assertIn("sharedAddr[4]=WALKER_TABLE_REPLY;",section)
        self.assertIn("case WALKER_TABLE_REQUEST:",a7)
        self.assertIn("&& sharedAddr[4] != WALKER_TABLE_REPLY",a7)
        self.assertNotIn("*(u32*)",section)
        self.assertNotIn("Wifi_Init",section)

    def test_arm9_only_prints_boot_metadata(self):
        a9=self.a9
        section=a9[a9.index("static void walkerIrqTableMenu(void)"):
                   a9.index("static void virtualPokewalkerMenu(void)")]
        self.assertIn("WPTQ",section)
        self.assertIn("WPTK",section)
        self.assertIn("frame<90",section)
        self.assertIn("25 slots NOT proven",section)
        self.assertIn("A: Read bounded IRQ words",section)
        self.assertIn("Wi-Fi: NOT ENABLED",section)
        self.assertNotIn("*(u32*)",section)
        self.assertIn("Y: ARM7 boot IRQ table",a9)
        self.assertIn("VIRTUAL POKEWALKER V7.2.6",a9)

if __name__=="__main__":
    unittest.main()
