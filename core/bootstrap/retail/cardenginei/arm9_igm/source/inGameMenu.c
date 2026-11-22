#include "inGameMenu.h"

#include <nds/bios.h>
#include <nds/ndstypes.h>
#include <nds/input.h>
#include <nds/interrupts.h>
#include <nds/timers.h>
#include <nds/system.h>
#include <nds/arm9/background.h>
#include <nds/arm9/video.h>

#include "igm_text.h"
#include "locations.h"
#include "cardengine_header_arm9.h"
#include "walker_arm9_snapshot.h"
#include "walker_arm9_wifi_sig.h"
#include "nds_header.h"
#include "tonccpy.h"

void DC_InvalidateRange(const void *base, u32 size);
void DC_FlushRange(const void *base, u32 size);

#ifndef B4DS
	#define MAX_BRIGHTNESS 5
#else
	#define MAX_BRIGHTNESS 4
#endif

static u8 bgBak[sizeof(igmText.font) * 4];
static u16 bgMapBak[0x300];
static u16 palBak[256];

// For RAM viewer, global so it's persistant
vu32 *address = (vu32*)0x02000000;
static bool arm7Ram = false;
static u8 arm7RamBak[0xC0];

#ifndef B4DS
static u16* vramBak = (u16*)INGAME_MENU_EXT_LOCATION+(0x18200/sizeof(u16));
static u16* bmpBuffer = (u16*)INGAME_MENU_EXT_LOCATION;

#define refreshRateCount 5
static const char* refreshRateText[refreshRateCount] = {"29.9 Hz", "44.9 Hz", "50 Hz", "59.9 Hz", "74.9 Hz"};
static int refreshRates[refreshRateCount] = {30000, 45000, 50, 60000, 75000};
static int refreshRate = 3;
#else
cardengineArm9* volatile ce9 = NULL;

static u16* vramBak = (u16*)INGAME_MENU_EXT_LOCATION_B4DS+(0x18200/sizeof(u16));
static u16* bmpBuffer = (u16*)INGAME_MENU_EXT_LOCATION_B4DS;
#endif

// Header for a 256x192 16 bit (RGBA 565) BMP
const static u8 bmpHeader[] = {
	0x42, 0x4D, 0x46, 0x80, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46, 0x00,
	0x00, 0x00, 0x38, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0xC0, 0x00,
	0x00, 0x00, 0x01, 0x00, 0x10, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x80,
	0x01, 0x00, 0x13, 0x0B, 0x00, 0x00, 0x13, 0x0B, 0x00, 0x00, 0x00, 0x00,
	0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xF8, 0x00, 0x00, 0xE0, 0x07,
	0x00, 0x00, 0x1F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

#define KEYS sharedAddr[5]

bool swiDelayEnabled = true;
void mySwiDelay(int delay) {
	if (!swiDelayEnabled) {
		return;
	}

	swiDelay(delay);
}

void SetBrightness(u8 screen, s8 bright) {
	u8 mode = 1;

	if (bright < 0) {
		mode = 2;
		bright = -bright;
	}
	if (bright > 31) {
		bright = 31;
	}
	*(vu16*)(0x0400006C + (0x1000 * screen)) = bright | (mode << 14);
}

void print(int x, int y, const unsigned char *str, FontPalette palette, bool main) {
	u16 *dst = (main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15)) + y * 0x20 + x;
	while(*str)
		*(dst++) = *(str++) | palette << 12;
}

void printCenter(int x, int y, const unsigned char *str, FontPalette palette, bool main) {
	u16 *dst = (main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15)) + y * 0x20 + x;
	const unsigned char *start = str;
	while(*str)
		str++;
	dst += (str - start) / 2;
	while(str != start)
		*(--dst) = *(--str) | palette << 12;
}

void printRight(int x, int y, const unsigned char *str, FontPalette palette, bool main) {
	u16 *dst = (main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15)) + y * 0x20 + x;
	const unsigned char *start = str;
	while(*str)
		str++;
	while(str != start)
		*(dst--) = *(--str) | palette << 12;
}

int printMsg(int y, const unsigned char *str, FontPalette palette, bool main) {
	u16 *dst = main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15);
	while(*str) {
		bool endFound = false;
		int lineLen = 0;
		if (str[0] == 0x20) {
			str++;
		}
		for (int i = 0; i < 0x20; i++) {
			endFound = str[i] == 0;
			if (endFound) {
				break;
			}
			lineLen++;
		}
		if (!endFound) {
			for (int i = 0x20; i >= 0; i--) {
				if (str[i] == 0x20) {
					lineLen = i;
					break;
				}
			}
		}
		if (lineLen > 0) {
			if (igmText.rtl) {
				for (int i = 0; i < lineLen; i++) {
					dst[(y * 0x20) + (0x20 - lineLen) + i] = *(str++) | palette << 12;
				}
			} else {
				for (int i = 0; i < lineLen; i++) {
					dst[(y * 0x20) + i] = *(str++) | palette << 12;
				}
			}
			y++;
		}
		if (y == 0x18) break;
	}
	return y;
}

void printChar(int x, int y, unsigned char c, FontPalette palette, bool main) {
	(main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15))[y * 0x20 + x] = c | palette << 12;
}

void printDec(int x, int y, u32 val, int digits, FontPalette palette, bool main) {
	u16 *dst = (main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15)) + y * 0x20 + x;
	for(int i = digits - 1; i >= 0; i--) {
		*(dst + i) = ('0' + (val % 10)) | palette << 12;
		val /= 10;
	}
}

void printHex(int x, int y, u32 val, u8 bytes, FontPalette palette, bool main) {
	u16 *dst = (main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15)) + y * 0x20 + x;
	for(int i = bytes * 2 - 1; i >= 0; i--) {
		*(dst + i) = ((val & 0xF) >= 0xA ? 'A' + (val & 0xF) - 0xA : '0' + (val & 0xF)) | palette << 12;
		val >>= 4;
	}
}

static void printTime(void) {
	while (!(sharedAddr[7] & 0x10000000)) { // Wait for time to be received
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	}
	#ifndef B4DS
	#define timeYpos 3
	#else
	#define timeYpos 2
	#endif

	u8 hours = (u8)sharedAddr[7];
	u8 minutes = (u8)sharedAddr[8];
	printDec(0x20 - 6, 0x18 - timeYpos, hours, 2, FONT_LIGHT_BLUE, false);
	printChar(0x20 - 4, 0x18 - timeYpos, ':', FONT_LIGHT_BLUE, false);
	printDec(0x20 - 3, 0x18 - timeYpos, minutes, 2, FONT_LIGHT_BLUE, false);
}

#ifndef B4DS
static void printBattery(void) {
	while ((u8)sharedAddr[6] == 0) { // Wait for battery level to be received
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	}
	u8 batteryLevel = (u8)sharedAddr[6];
	const char *bars = "\3\3";
	if (batteryLevel & BIT(7)) {
		bars = "\6\6";	// Charging
	} else {
		switch (batteryLevel) {
			default:
				break;
			case 0x1:
			case 0x3:
				bars = "\3\4";
				break;
			case 0x7:
				bars = "\3\5";
				break;
			case 0xB:
				bars = "\4\5";
				break;
			case 0xF:
				bars = "\5\5";
				break;
		}
	}
	print(0x20 - 4, 0x18 - 2, (const unsigned char *)bars, FONT_LIGHT_BLUE, false);
}
#endif

static void waitKeys(u16 keys) {
	// Prevent key repeat for 10 frames
	for(int i = 0; i < 10 && (KEYS & keys); i++) {
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	}

	u32 status = sharedAddr[6]; // Battery, brightness, volume
	u8 hours = (u8)sharedAddr[7];
	u8 minutes = (u8)sharedAddr[8];

	do {
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	} while(!(KEYS & keys) && sharedAddr[6] == status && (u8)sharedAddr[7] == hours && (u8)sharedAddr[8] == minutes);
}

void clearScreen(bool main) {
	toncset16(main ? BG_MAP_RAM(15) : BG_MAP_RAM_SUB(15), 0, 0x300);
}

bool boolQuestion(const unsigned char *str) {
	clearScreen(false);

	const int y = printMsg(0, str, FONT_WHITE, false) + 1;
	if (igmText.rtl) {
		printRight(0x20 - 1, y, igmText.aYes, FONT_WHITE, false);
		printRight(0x20 - 1, y + 1, igmText.bNo, FONT_WHITE, false);
	} else {
		print(0, y, igmText.aYes, FONT_WHITE, false);
		print(0, y + 1, igmText.bNo, FONT_WHITE, false);
	}

	do {
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	} while(KEYS & KEY_A);

	waitKeys(KEY_A | KEY_B);

	if (KEYS & KEY_A) {
		do {
			while (REG_VCOUNT != 191) mySwiDelay(100);
			while (REG_VCOUNT == 191) mySwiDelay(100);
		} while(KEYS & KEY_A);
		return true;
	} else {
		do {
			while (REG_VCOUNT != 191) mySwiDelay(100);
			while (REG_VCOUNT == 191) mySwiDelay(100);
		} while(KEYS & KEY_B);
	}
	return false;
}

#define VRAM_x(bank) ((u16*)(0x6800000 + (0x0020000 * (bank))))
#define VRAM_x_CR(bank) (((vu8*)0x04000240)[bank])

static void screenshot(void) {
	// Try to find the safest bank to capture to
	u8 vramBank = 2;
	if((VRAM_D_CR & 1) == 0) {
		vramBank = 3;
	} else if((VRAM_C_CR & 1) == 0) {
		vramBank = 2;
	} else if((VRAM_B_CR & 7) == 0) {
		vramBank = 1;
	} else if((VRAM_A_CR & 7) == 0) {
		vramBank = 0;
	}

	// Use capture mode B if no banks are mapped for main engine
	u8 captureMode = DCAP_MODE_B;
	for(int i = 0; i <= 6; i++) {
		if(VRAM_x_CR(i) & 1)
			captureMode = DCAP_MODE_A;
	}

	u8 vramCr = VRAM_x_CR(vramBank);

	// Select bank
	u8 cursorPosition = vramBank;
	while(1) {
		// Configure VRAM
		VRAM_x_CR(vramBank) = vramCr; // LCD
		vramCr = VRAM_x_CR(cursorPosition);
		VRAM_x_CR(cursorPosition) = VRAM_ENABLE; // LCD
		vramBank = cursorPosition;

		clearScreen(false);

		toncset16(BG_MAP_RAM_SUB(15) + 0x20 * 9 + 5, '-', 20);
		printCenter(15, 10, igmText.selectBank, FONT_WHITE, false);
		printChar(15, 12, 'A' + vramBank, FONT_LIGHT_BLUE, false);
		toncset16(BG_MAP_RAM_SUB(15) + 0x20 * 13 + 5, '-', 20);

		FontPalette color = igmText.currentScreenshot == 50 ? FONT_RED : FONT_LIME;
		if(igmText.rtl) {
			printDec(6, 14, igmText.currentScreenshot, 2, color, false);
			printChar(8, 14, '/', color, false);
			printDec(9, 14, 50, 2, color, false);
			printRight(23, 14, igmText.count, 0, false);
		} else {
			print(6, 14, igmText.count, 0, false);
			printDec(19, 14, igmText.currentScreenshot, 2, color, false);
			printChar(21, 14, '/', color, false);
			printDec(22, 14, 50, 2, color, false);

		}

		waitKeys(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_A | KEY_B);

		if (KEYS & (KEY_UP | KEY_LEFT)) {
			if(vramBank > 0)
				cursorPosition--;
		} else if (KEYS & (KEY_DOWN | KEY_RIGHT)) {
			if(vramBank < 3)
				cursorPosition++;
		} else if(KEYS & KEY_A && igmText.currentScreenshot < 50) {
			break;
		} else if(KEYS & KEY_B) {
			VRAM_x_CR(vramBank) = vramCr;
			return;
		}
	}

	#ifdef B4DS
	codeJumpWord = ce9->prepareScreenshot;
	(*codeJump)();
	#else
	sharedAddr[4] = 0x50505353;
	while (sharedAddr[4] == 0x50505353) {
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	}
	#endif

	// Backup VRAM bank
	tonccpy(vramBak, VRAM_x(vramBank), 0x18000);

	REG_DISPCAPCNT = DCAP_BANK(vramBank) | DCAP_SIZE(DCAP_SIZE_256x192) | DCAP_MODE(captureMode) | DCAP_ENABLE;
	while(REG_DISPCAPCNT & DCAP_ENABLE);

	tonccpy(bmpBuffer, bmpHeader, sizeof(bmpHeader));

	// ABGR 1555 -> RGB 565
	for (int i = 0; i < 256 * 192; i++) {
		u16 val = VRAM_x(vramBank)[i];
		VRAM_x(vramBank)[i] = ((val >> 10) & 31) | ((val & (31 << 5)) << 1) | ((val & 31) << 11);
	}

	// Write image data, upside down as that's how BMPs want it
	u16 *bmp = bmpBuffer + sizeof(bmpHeader) / sizeof(u16);
	for(int i = 191; i >= 0; i--) {
		tonccpy(bmp, VRAM_x(vramBank) + (i * 256), 256 * sizeof(u16));
		bmp += 256;
	}

	// Restore VRAM bank
	tonccpy(VRAM_x(vramBank), vramBak, 0x18000);
	VRAM_x_CR(vramBank) = vramCr;

	#ifdef B4DS
	codeJumpWord = ce9->saveScreenshot;
	(*codeJump)();
	#else
	sharedAddr[4] = 0x544F4853;
	while (sharedAddr[4] == 0x544F4853) {
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	}
	DC_InvalidateRange(&igmText.currentScreenshot, 1);
	DC_InvalidateRange((char*)INGAME_MENU_EXT_LOCATION, 0x40000);
	#endif
}

static void manual(void) {
	#ifdef B4DS
	codeJumpWord = ce9->prepareManual;
	(*codeJump)();
	#else
	sharedAddr[4] = 0x4E414D50; // PMAN
	do {
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	} while (sharedAddr[4] == 0x4E414D50);
	#endif

	while (1) {
		#ifdef B4DS
		codeJumpWord = ce9->readManual;
		(*codeJump1)(igmText.manualLine);

		print(0, 0, (unsigned char *)0x027FF200, FONT_WHITE, false);
		#else
		DC_InvalidateRange((unsigned char *)INGAME_MENU_EXT_LOCATION, 32 * 24);
		sharedAddr[0] = igmText.manualLine;
		sharedAddr[4] = 0x554E414D; // MANU
		do {
			while (REG_VCOUNT != 191) mySwiDelay(100);
			while (REG_VCOUNT == 191) mySwiDelay(100);
		} while (sharedAddr[4] == 0x554E414D);

		print(0, 0, (unsigned char *)INGAME_MENU_EXT_LOCATION, FONT_WHITE, false);
		#endif

		waitKeys(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_B);
		if(KEYS & KEY_UP) {
			igmText.manualLine -= (KEYS & KEY_R) ? 100 : 1;
		} else if(KEYS & KEY_DOWN) {
			igmText.manualLine += (KEYS & KEY_R) ? 100 : 1;
		} else if(KEYS & KEY_LEFT) {
			igmText.manualLine -= (KEYS & KEY_R) ? 1000 : 23;
			
		} else if(KEYS & KEY_RIGHT) {
			igmText.manualLine += (KEYS & KEY_R) ? 1000 : 23;
		} else if(KEYS & KEY_B) {
			break;
		}

		if(igmText.manualLine < 0)
			igmText.manualLine = 0;
		else if(igmText.manualLine > igmText.manualMaxLine - 23)
			igmText.manualLine = igmText.manualMaxLine - 23 > 0 ? igmText.manualMaxLine - 23 : 0;
	}

	#ifdef B4DS
	codeJumpWord = ce9->restorePreManual;
	(*codeJump)();
	#else
	sharedAddr[4] = 0x4E414D52; // RMAN
	do {
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	} while (sharedAddr[4] == 0x4E414D52);
	#endif
}

static void drawCursor(u8 line) {
	u8 pos = igmText.rtl ? 0x1F : 0;
	// Clear other cursors
	for(int i = 0; i < 0x18; i++)
		BG_MAP_RAM_SUB(15)[i * 0x20 + pos] = 0;

	// Set cursor on the selected line
	BG_MAP_RAM_SUB(15)[line * 0x20 + pos] = igmText.rtl ? '<' : '>';
}

static void drawMainMenu(MenuItem *menuItems, int menuItemCount) {
	clearScreen(false);

	// Print labels
	for(int i = 0; i < menuItemCount; i++) {
		if(igmText.rtl)
			printRight(0x1D, i, menuItems[i] == MENU_VIRTUAL_POKEWALKER ? (const unsigned char *)"Virtual Pokewalker" : igmText.menu[menuItems[i]], FONT_WHITE, false);
		else
			print(2, i, menuItems[i] == MENU_VIRTUAL_POKEWALKER ? (const unsigned char *)"Virtual Pokewalker" : igmText.menu[menuItems[i]], FONT_WHITE, false);
	}

	// Print info
	print(1, 0x18 - 3, igmText.ndsBootstrap, FONT_LIGHT_GRAY, false);
	print(1, 0x18 - 2, igmText.version, FONT_LIGHT_GRAY, false);

	#ifndef B4DS
	// Print battery
	printChar(0x20 - 5, 0x18 - 2, '\2', FONT_LIGHT_BLUE, false);
	printChar(0x20 - 2, 0x18 - 2, '\7', FONT_LIGHT_BLUE, false);
	#endif
}

/* V7.1 read-only diagnostics. Requests a bounded snapshot from the ARM7
 * coordinator using the existing menu command channel. No Wi-Fi start, no
 * ROM/save mutation, and no changes to the fixed IgmText layout. */
#ifndef B4DS
#define WALKER_DIAG_REQUEST 0x47445057u /* WPDG */
#define WALKER_DIAG_REPLY   0x4B445057u /* WPDK */
#define WALKER_DIAG_MENU    0x554E454Du /* MENU */
#endif
/* V7.1.3: codes are shared with WALKER_BOOT_* in walker_emu.h. */
static const unsigned char* walkerBootReason(u32 code) {
    switch(code) {
        case 0u:   return (const unsigned char*)"Boot was not attempted";
        case 1u:   return (const unsigned char*)"No .walker file selected";
        case 2u:   return (const unsigned char*)"No Walker RAM reserved";
        case 3u:   return (const unsigned char*)"No file + no RAM area";
        case 0x10u:return (const unsigned char*)"IR receive pattern missing";
        case 0x11u:return (const unsigned char*)"IR write pattern missing";
        case 0x12u:return (const unsigned char*)"IR chip pattern missing";
        case 0x13u:return (const unsigned char*)"IR init pattern missing";
        case 0x14u:return (const unsigned char*)"EEPROM read failed";
        case 0xFFu:return (const unsigned char*)"Hook installed; ptr lost";
        default:   return (const unsigned char*)"Unknown boot status";
    }
}

/* V7.2: a read-only pre-menu snapshot of ARM7 IRQ and timer registers.
 * This is NOT a Wi-Fi capability probe. IRQ enable masks cannot establish
 * which function owns the handler, and we never touch radio registers. */
/* V7.2.1: ARM7 DMA3 values sampled before the game was paused,
 * whereas ARM9 values are observed in the menu context only.
 * Neither observation establishes ownership or permits DSWifi startup. */
/* ARM9 NTR IGM receives these values via r3 from the resident cardengine,
 * with a pointer to a live stack record. Never touch ARM7 IPC mailbox slots
 * for this handoff. Other builds see an unavailable snapshot. */
static WalkerArm9Snapshot walkerArm9PreWrapper = {0,0,0,0};

/* V7.8: the menu enters from IRQ, so do not mistake its IME for the
 * earlier ROM callback state. This reports snapshots captured at cardRead
 * entry before the existing ROM-read code performs critical sections.
 */
static void walkerArm9PreWrapperMenu(void) {
    clearScreen(false);
    print(1,1,(const unsigned char*)"V7.8 ARM9 ROM TASKS",FONT_LIME,false);
    if(walkerArm9PreWrapper.magic == WALKER_ARM9_SNAPSHOT_MAGIC) {
        print(1,4,(const unsigned char*)"ROM reads: 0x",FONT_WHITE,false);
        printHex(14,4,walkerArm9PreWrapper.romReadCalls,4,FONT_LIGHT_BLUE,false);
        print(1,7,(const unsigned char*)"NonIRQ+IME:0x",FONT_WHITE,false);
        printHex(14,7,walkerArm9PreWrapper.eligibleReadCalls,4,FONT_LIGHT_BLUE,false);
        print(1,10,(const unsigned char*)"Last CPSR: 0x",FONT_WHITE,false);
        printHex(15,10,walkerArm9PreWrapper.lastReadCpsrMode,1,FONT_LIGHT_BLUE,false);
        print(1,13,(const unsigned char*)"Read IME: 0x",FONT_WHITE,false);
        printHex(15,13,walkerArm9PreWrapper.lastReadIme,1,FONT_LIGHT_BLUE,false);
    } else {
        print(1,6,(const unsigned char*)"ARM9 snapshot unavailable",FONT_RED,false);
    }
    print(1,17,(const unsigned char*)"Not a periodic worker",FONT_LIGHT_GRAY,false);
    print(1,19,(const unsigned char*)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,21,(const unsigned char*)"B: Back",FONT_WHITE,false);
    waitKeys(KEY_B);
    do {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
    } while(KEYS & KEY_B);
}

static void walkerRadioResourcesMenu(void) {
    u32 dma[4]={0,0,0,0};
    bool answered=false;
    const u16 arm9Timer3AtMenu=TIMER_CR(3);
    const u32 arm9IeAtMenu=REG_IE;
    const u32 arm9ImeAtMenu=REG_IME;
#ifndef B4DS
    sharedAddr[4]=0x44535057u; /* WPSD */
    for(unsigned frames=0;frames<90;frames++) {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
        const u32 response=sharedAddr[4];
        if(response==0x4B535057u) { /* WPSK */
            for(unsigned i=0;i<4;i++) dma[i]=sharedAddr[i];
            answered=true;
            break;
        }
        if(response==WALKER_DIAG_MENU) {
            sharedAddr[4]=0x44535057u;
        } else if(response!=0x44535057u) {
            break;
        }
    }
    if(sharedAddr[4]==0x44535057u || sharedAddr[4]==0x4B535057u)
        sharedAddr[4]=WALKER_DIAG_MENU;
#endif
    clearScreen(false);
    print(1,1,(const unsigned char *)"V7.2.2 DMA3 / ARM9 AUDIT",FONT_LIME,false);
    if(!answered) {
        print(1,4,(const unsigned char *)"ARM7 DMA3: no IPC reply",FONT_RED,false);
    } else {
        print(1,4,(const unsigned char *)"ARM7 DMA3_CR: 0x",FONT_WHITE,false);
        printHex(18,4,dma[0],4,FONT_LIGHT_BLUE,false);
        print(1,6,(const unsigned char *)"ARM7 DMA3_SRC:0x",FONT_WHITE,false);
        printHex(18,6,dma[1],4,FONT_LIGHT_BLUE,false);
        print(1,8,(const unsigned char *)"ARM7 DMA3_DST:0x",FONT_WHITE,false);
        printHex(18,8,dma[2],4,FONT_LIGHT_BLUE,false);
        print(1,10,(const unsigned char *)((dma[0]&0x80000000u) ?
            "DMA3 ENABLED at snapshot" : "DMA3 not enabled at snapshot"),
            FONT_LIGHT_GRAY,false);
    }
    print(1,12,(const unsigned char *)"ARM9 TMR3 (menu): 0x",FONT_WHITE,false);
    printHex(22,12,arm9Timer3AtMenu,2,FONT_LIGHT_BLUE,false);
    print(1,14,(const unsigned char *)"ARM9 IE (menu): 0x",FONT_WHITE,false);
    printHex(20,14,arm9IeAtMenu,4,FONT_LIGHT_BLUE,false);
    print(1,16,(const unsigned char *)"ARM9 IME (menu):0x",FONT_WHITE,false);
    printHex(20,16,arm9ImeAtMenu,1,FONT_LIGHT_BLUE,false);
    print(1,18,(const unsigned char *)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,19,(const unsigned char *)"No IRQ/DMA ownership proof",FONT_LIGHT_GRAY,false);
    print(1,20,(const unsigned char *)"A: ARM9 pre-wrapper view",FONT_WHITE,false);
    print(1,21,(const unsigned char *)"B: Back to main menu",FONT_WHITE,false);
    do {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
    } while(KEYS & KEY_Y);
    waitKeys(KEY_A | KEY_B);
    if(KEYS & KEY_A) {
        walkerArm9PreWrapperMenu();
    } else {
        do {
            while(REG_VCOUNT!=191) mySwiDelay(100);
            while(REG_VCOUNT==191) mySwiDelay(100);
        } while(KEYS & KEY_B);
    }
}

static void walkerRadioSnapshotMenu(void) {
    u32 regs[4]={0,0,0,0};
    bool answered=false;
#ifndef B4DS
    sharedAddr[4]=0x44525057u; /* WPRD */
    for(unsigned frames=0;frames<90;frames++) {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
        const u32 response=sharedAddr[4];
        if(response==0x4B525057u) { /* WPRK */
            for(unsigned i=0;i<4;i++)regs[i]=sharedAddr[i];
            answered=true;
            break;
        }
        if(response==WALKER_DIAG_MENU) {
            sharedAddr[4]=0x44525057u;
        } else if(response!=0x44525057u) break;
    }
    if(sharedAddr[4]==0x44525057u || sharedAddr[4]==0x4B525057u)
        sharedAddr[4]=WALKER_DIAG_MENU;
#endif
    clearScreen(false);
    print(1,1,(const unsigned char *)"V7.2 ARM7 IRQ/TIMER SNAPSHOT",FONT_LIME,false);
    if(!answered) {
        print(1,4,(const unsigned char *)"ARM7 radio probe: no reply",FONT_RED,false);
    } else {
        print(1,4,(const unsigned char *)"REG_IE:  0x",FONT_WHITE,false);
        printHex(13,4,regs[0],4,FONT_LIGHT_BLUE,false);
        print(1,6,(const unsigned char *)"REG_IME: 0x",FONT_WHITE,false);
        printHex(13,6,regs[1],1,FONT_LIGHT_BLUE,false);
        print(1,8,(const unsigned char *)"TIMER0: 0x",FONT_WHITE,false);
        printHex(13,8,regs[2]&0xFFFFu,2,FONT_LIGHT_BLUE,false);
        print(1,9,(const unsigned char *)"TIMER1: 0x",FONT_WHITE,false);
        printHex(13,9,regs[2]>>16,2,FONT_LIGHT_BLUE,false);
        print(1,10,(const unsigned char *)"TIMER2: 0x",FONT_WHITE,false);
        printHex(13,10,regs[3]&0xFFFFu,2,FONT_LIGHT_BLUE,false);
        print(1,11,(const unsigned char *)"TIMER3: 0x",FONT_WHITE,false);
        printHex(13,11,regs[3]>>16,2,FONT_LIGHT_BLUE,false);
    }
    print(1,14,(const unsigned char *)"Captured before menu pause",FONT_WHITE,false);
    print(1,16,(const unsigned char *)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,18,(const unsigned char *)"IRQ ownership NOT verified",FONT_LIGHT_GRAY,false);
    print(1,19,(const unsigned char *)"Y: DMA3 + ARM9 snapshot",FONT_WHITE,false);
    print(1,21,(const unsigned char *)"B: Back to main menu",FONT_WHITE,false);
    do {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
    } while(KEYS & KEY_X);
    bool openResources=false;
    while(1) {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
        if(KEYS & KEY_B) break;
        if(KEYS & KEY_Y) { openResources=true; break; }
    }
    if(openResources) {
        walkerRadioResourcesMenu();
    } else {
        do {
            while(REG_VCOUNT!=191) mySwiDelay(100);
            while(REG_VCOUNT==191) mySwiDelay(100);
        } while(KEYS & KEY_B);
    }
}

/* V7.2.5: obtain the REAL bootloaderi IRQ-table location selected at
 * HGSS startup. Never dereference a table entry here, especially slot 24.
 * Only four boot metadata words cross the already-tested bounded IPC. */
/* V7.2.7 boot-vs-live comparison. Both responses come from the existing
 * menu IPC; the ARM7 reads only the already-bounded words 0 and 16 and
 * returns boot-time snapshots of the original bootstrap hooks.
 * In particular, this does NOT resolve IRQ_WIFI or authorize any IRQ write.
 */
static bool walkerReadFourWords(u32 request, u32 acknowledge, u32 words[4]) {
#ifndef B4DS
    sharedAddr[4] = request;
    bool answered = false;
    for (unsigned frame=0; frame<90; frame++) {
        while (REG_VCOUNT!=191) mySwiDelay(100);
        while (REG_VCOUNT==191) mySwiDelay(100);
        const u32 command = sharedAddr[4];
        if (command == acknowledge) {
            for (unsigned i=0; i<4; i++) words[i] = sharedAddr[i];
            answered = true;
            break;
        }
        if (command == WALKER_DIAG_MENU)
            sharedAddr[4] = request;
        else if (command != request)
            break;
    }
    if (sharedAddr[4] == request || sharedAddr[4] == acknowledge)
        sharedAddr[4] = WALKER_DIAG_MENU;
    return answered;
#else
    (void)request; (void)acknowledge; (void)words;
    return false;
#endif
}

static void walkerIrqLifetimeMenu(void) {
    u32 boot[4]={0,0,0,0};
    u32 live[4]={0,0,0,0};
    const bool bootOk=walkerReadFourWords(0x51435057u, 0x4B435057u, boot); /* WPCQ/WPCK */
    const bool liveOk=walkerReadFourWords(0x514B5057u, 0x4B4B5057u, live); /* WPKQ/WPKK */
    const bool bounded=liveOk && (live[0] & 1u);
    clearScreen(false);
    print(1,1,(const unsigned char *)"V7.2.7 IRQ BOOT vs LIVE",FONT_LIME,false);
    if (!bootOk) {
        print(1,5,(const unsigned char *)"ARM7 boot snapshot absent",FONT_RED,false);
    } else if (!liveOk) {
        print(1,5,(const unsigned char *)"ARM7 live reply absent",FONT_RED,false);
    } else if (!bounded) {
        print(1,5,(const unsigned char *)"Live RAM read BLOCKED",FONT_RED,false);
    } else {
        print(1,3,(const unsigned char *)"V0 before: 0x",FONT_WHITE,false);
        printHex(16,3,boot[0],4,FONT_LIGHT_BLUE,false);
        print(1,5,(const unsigned char *)"V0 hooked: 0x",FONT_WHITE,false);
        printHex(16,5,boot[2],4,FONT_LIGHT_BLUE,false);
        print(1,7,(const unsigned char *)"V0 live:   0x",FONT_WHITE,false);
        printHex(16,7,live[1],4,FONT_LIGHT_BLUE,false);
        print(1,9,(const unsigned char *)"I16 before:0x",FONT_WHITE,false);
        printHex(16,9,boot[1],4,FONT_LIGHT_BLUE,false);
        print(1,11,(const unsigned char *)"I16 hooked:0x",FONT_WHITE,false);
        printHex(16,11,boot[3],4,FONT_LIGHT_BLUE,false);
        print(1,13,(const unsigned char *)"I16 live:  0x",FONT_WHITE,false);
        printHex(16,13,live[2],4,FONT_LIGHT_BLUE,false);
        print(1,15,(const unsigned char *)(boot[2]==live[1] ?
            "VBlank slot: unchanged" : "VBlank slot: CHANGED"),FONT_LIGHT_GRAY,false);
        print(1,16,(const unsigned char *)(boot[3]==live[2] ?
            "IPC slot: unchanged" : "IPC slot: CHANGED"),FONT_LIGHT_GRAY,false);
    }
    print(1,18,(const unsigned char *)"No IRQ ownership proof",FONT_LIGHT_GRAY,false);
    print(1,20,(const unsigned char *)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,22,(const unsigned char *)"B: Back to IRQ words",FONT_WHITE,false);
    do {
        while (REG_VCOUNT!=191) mySwiDelay(100);
        while (REG_VCOUNT==191) mySwiDelay(100);
    } while (KEYS & KEY_X);
    waitKeys(KEY_B);
    do {
        while (REG_VCOUNT!=191) mySwiDelay(100);
        while (REG_VCOUNT==191) mySwiDelay(100);
    } while (KEYS & KEY_B);
}

/* V7.2.8: passive proof of whether the resident ARM7 callbacks execute.
 * This reads counters only. Neither this menu nor the counter instrumentation
 * installs IRQ handlers, touches WLAN registers, or accesses the game save.
 */
static void walkerHeartbeatMenu(void) {
    u32 counts[4]={0,0,0,0};
    const bool answered=walkerReadFourWords(0x51485057u,0x4B485057u,counts); /* WPHQ/WPHK */
    clearScreen(false);
    print(1,1,(const unsigned char *)"V7.2.8 ARM7 HEARTBEAT",FONT_LIME,false);
    if (!answered) {
        print(1,5,(const unsigned char *)"ARM7: no heartbeat reply",FONT_RED,false);
    } else {
        print(1,4,(const unsigned char *)"VBlank calls: 0x",FONT_WHITE,false);
        printHex(19,4,counts[0],4,FONT_LIGHT_BLUE,false);
        print(1,6,(const unsigned char *)"Bridge ticks: 0x",FONT_WHITE,false);
        printHex(19,6,counts[1],4,FONT_LIGHT_BLUE,false);
        print(1,8,(const unsigned char *)"IPC callbacks:0x",FONT_WHITE,false);
        printHex(19,8,counts[2],4,FONT_LIGHT_BLUE,false);
        print(1,11,(const unsigned char *)(counts[3] & 1u ?
            "Walker ptr: present" : "Walker ptr: not set"),FONT_LIGHT_GRAY,false);
        print(1,13,(const unsigned char *)"Compare after 10s gameplay",FONT_WHITE,false);
        print(1,15,(const unsigned char *)"Delta > 0 = callback ran",FONT_LIGHT_GRAY,false);
    }
    print(1,17,(const unsigned char *)"No Wi-Fi/IRQ ownership proof",FONT_LIGHT_GRAY,false);
    print(1,19,(const unsigned char *)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,21,(const unsigned char *)"B: Back to IRQ words",FONT_WHITE,false);
    do {
        while (REG_VCOUNT != 191) mySwiDelay(100);
        while (REG_VCOUNT == 191) mySwiDelay(100);
    } while (KEYS & KEY_Y);
    waitKeys(KEY_B);
    do {
        while (REG_VCOUNT != 191) mySwiDelay(100);
        while (REG_VCOUNT == 191) mySwiDelay(100);
    } while (KEYS & KEY_B);
}

/* V7.2.6: show raw, bounded ARM7 words. Slot24 might be ordinary data!
 * Do not interpret raw words as an IRQ_WIFI handler or authorize a write. */
static void walkerIrqWordsMenu(void) {
    u32 reply[4]={0,0,0,0};
    bool answered=false;
#ifndef B4DS
    sharedAddr[4]=0x514B5057u; /* WPKQ */
    for(unsigned frame=0;frame<90;frame++) {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
        const u32 command=sharedAddr[4];
        if(command==0x4B4B5057u) { /* WPKK */
            for(unsigned i=0;i<4;i++)reply[i]=sharedAddr[i];
            answered=true;
            break;
        }
        if(command==WALKER_DIAG_MENU)
            sharedAddr[4]=0x514B5057u;
        else if(command!=0x514B5057u)
            break;
    }
    if(sharedAddr[4]==0x514B5057u || sharedAddr[4]==0x4B4B5057u)
        sharedAddr[4]=WALKER_DIAG_MENU;
#endif
    clearScreen(false);
    print(1,1,(const unsigned char *)"V7.2.6 ARM7 IRQ WORDS",FONT_LIME,false);
    if(!answered) {
        print(1,5,(const unsigned char *)"ARM7: no word reply",FONT_RED,false);
    } else if(!(reply[0] & 1u)) {
        print(1,5,(const unsigned char *)"READ BLOCKED: no safe span",FONT_RED,false);
    } else {
        print(1,4,(const unsigned char *)"Slot 0 raw: 0x",FONT_WHITE,false);
        printHex(17,4,reply[1],4,FONT_LIGHT_BLUE,false);
        print(1,6,(const unsigned char *)"Slot16 raw: 0x",FONT_WHITE,false);
        printHex(17,6,reply[2],4,FONT_LIGHT_BLUE,false);
        print(1,8,(const unsigned char *)"Slot24 raw: 0x",FONT_WHITE,false);
        printHex(17,8,reply[3],4,FONT_LIGHT_BLUE,false);
        print(1,11,(const unsigned char *)"Slot24 may NOT be IRQ_WIFI",FONT_LIGHT_GRAY,false);
    }
    print(1,14,(const unsigned char *)"Raw RAM, NOT handler proof",FONT_LIGHT_GRAY,false);
    print(1,16,(const unsigned char *)"No IRQ values changed",FONT_WHITE,false);
    print(1,19,(const unsigned char *)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,20,(const unsigned char *)"Y: ARM7 heartbeat counters",FONT_WHITE,false);
    print(1,21,(const unsigned char *)"X: Boot vs live IRQ words",FONT_WHITE,false);
    print(1,22,(const unsigned char *)"B: Back to menu",FONT_WHITE,false);
    do {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
    } while(KEYS & KEY_A);
    waitKeys(KEY_B | KEY_X | KEY_Y);
    if (KEYS & KEY_Y) {
        walkerHeartbeatMenu();
    } else if (KEYS & KEY_X) {
        walkerIrqLifetimeMenu();
    } else {
        do {
            while(REG_VCOUNT!=191) mySwiDelay(100);
            while(REG_VCOUNT==191) mySwiDelay(100);
        } while(KEYS & KEY_B);
    }
}

static void walkerIrqTableMenu(void) {
    u32 record[4]={0,0,0,0};
    bool answered=false;
#ifndef B4DS
    sharedAddr[4]=0x51545057u; /* WPTQ */
    for(unsigned frame=0;frame<90;frame++) {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
        const u32 response=sharedAddr[4];
        if(response==0x4B545057u) { /* WPTK */
            for(unsigned i=0;i<4;i++)record[i]=sharedAddr[i];
            answered=true;
            break;
        }
        if(response==WALKER_DIAG_MENU)
            sharedAddr[4]=0x51545057u;
        else if(response!=0x51545057u)
            break;
    }
    if(sharedAddr[4]==0x51545057u || sharedAddr[4]==0x4B545057u)
        sharedAddr[4]=WALKER_DIAG_MENU;
#endif
    clearScreen(false);
    print(1,1,(const unsigned char *)"V7.2.6 ARM7 BOOT IRQ MAP",FONT_LIME,false);
    if(!answered) {
        print(1,4,(const unsigned char *)"ARM7: no table report",FONT_RED,false);
    } else {
        print(1,4,(const unsigned char *)"IRQ table: 0x",FONT_WHITE,false);
        printHex(15,4,record[0],4,FONT_LIGHT_BLUE,false);
        print(1,6,(const unsigned char *)"ARM7 image:0x",FONT_WHITE,false);
        printHex(15,6,record[1],4,FONT_LIGHT_BLUE,false);
        print(1,8,(const unsigned char *)"Image bytes:0x",FONT_WHITE,false);
        printHex(15,8,record[2],4,FONT_LIGHT_BLUE,false);
        print(1,10,(const unsigned char *)"Method:",FONT_WHITE,false);
        const unsigned char *method =
            record[3]==1u?(const unsigned char *)"Cached IRQ location" :
            record[3]==2u?(const unsigned char *)"SDK-known location" :
            record[3]==3u?(const unsigned char *)"Marker scan" :
            record[3]==4u?(const unsigned char *)"Relative IRQ literal" :
                           (const unsigned char *)"Unknown / no location";
        print(1,12,method,FONT_LIGHT_BLUE,false);
        /* Arithmetic-only footprint test. The source method, writable
         * extent, interrupt chaining and actual Wi-Fi IRQ owner are
         * still NOT verified. Never touch record[0] as a pointer. */
        bool inImage = record[0]>=record[1] &&
                       record[2]>=100u &&
                       record[0]-record[1]<=record[2]-100u &&
                       (record[0]&3u)==0u;
        print(1,15,(const unsigned char *)(inImage ?
            "25 slots fit image" : "25 slots NOT proven"),FONT_LIGHT_GRAY,false);
    }
    print(1,17,(const unsigned char *)"A: Read bounded IRQ words",FONT_WHITE,false);
    print(1,19,(const unsigned char *)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,21,(const unsigned char *)"B: Back to menu",FONT_WHITE,false);
    do {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
    } while(KEYS & KEY_Y);
    waitKeys(KEY_A | KEY_B);
    if(KEYS & KEY_A) {
        walkerIrqWordsMenu();
    } else {
        do {
            while(REG_VCOUNT!=191) mySwiDelay(100);
            while(REG_VCOUNT==191) mySwiDelay(100);
        } while(KEYS & KEY_B);
    }
}

/* V7.7 NTR ARM9 live-code audit of the same fixed five windows
 * identified by V7.6. On-console CRC32 must be compared to the offline
 * ROM CRC32 for the same code window. PRO means plausible ARM prologue,
 * not Wi-Fi/ABI proof. No WCM/SOC calls, IRQ or save writes.
 */
#ifndef B4DS
static void walkerArm9WifiCodeMenu(void) {
    u32 crc[WALKER_WIFI_SIG_COUNT]={0,0,0,0,0};
    const u32 mask = walkerWifiCheckStaticCode(crc);
    const unsigned char* names[WALKER_WIFI_SIG_COUNT] = {
        (const unsigned char*)"WCM_Init",
        (const unsigned char*)"WCM_Startup",
        (const unsigned char*)"WCM_GetPhase",
        (const unsigned char*)"SOC_Socket",
        (const unsigned char*)"SOC_Connect"
    };
    clearScreen(false);
    print(1,1,(const unsigned char*)"V7.7 ARM9 LIVE CRC",FONT_LIME,false);
    unsigned good=0;
    for (unsigned i=0; i<WALKER_WIFI_SIG_COUNT; i++) {
        const int row = 4 + 2 * i;
        print(1,row,names[i],FONT_WHITE,false);
        printHex(16,row,crc[i],4,FONT_LIGHT_BLUE,false);
        if (mask & (1u<<i)) good++;
        print(26,row,(const unsigned char*)((mask & (1u<<i)) ?
              "PRO" : "?"),(mask & (1u<<i))?FONT_LIME:FONT_RED,false);
    }
    print(1,15,(const unsigned char*)"ARM prologues:",FONT_WHITE,false);
    printDec(17,15,good,1,FONT_LIGHT_BLUE,false);
    print(18,15,(const unsigned char*)"/5",FONT_LIGHT_BLUE,false);
    print(1,20,(const unsigned char*)"Wi-Fi: NOT ENABLED",FONT_RED,false);
    print(1,22,(const unsigned char*)"B: Back",FONT_WHITE,false);
    do {
        while(REG_VCOUNT != 191) mySwiDelay(100);
        while(REG_VCOUNT == 191) mySwiDelay(100);
    } while(KEYS & KEY_L);
    waitKeys(KEY_B);
    do {
        while(REG_VCOUNT != 191) mySwiDelay(100);
        while(REG_VCOUNT == 191) mySwiDelay(100);
    } while(KEYS & KEY_B);
}
#endif

static void virtualPokewalkerMenu(void) {
    u32 diag[4]={0,0,0,0};
    bool answered=false;
    u32 lastCommand=0;
    #ifndef B4DS
    sharedAddr[4]=WALKER_DIAG_REQUEST;
    /* ARM7's menu loop can restore MENU after processing the previous
     * command in the same frame as our first WPDG write. A one-shot
     * request is therefore lossy. Retry only when that *idle* MENU
     * state is observed; never overwrite other service commands.
     * WPDK is held by ARM7 until we acknowledge it with MENU. */
    for(unsigned frames=0;frames<90;frames++) {
        while (REG_VCOUNT != 191) mySwiDelay(100);
        while (REG_VCOUNT == 191) mySwiDelay(100);
        const u32 response=sharedAddr[4];
        if(response==WALKER_DIAG_REPLY) {
            for(unsigned i=0;i<4;i++) diag[i]=sharedAddr[i];
            answered=true;
            break;
        }
        if(response==WALKER_DIAG_MENU) {
            /* The ARM7 menu is idle, so resubmit the read-only query. */
            sharedAddr[4]=WALKER_DIAG_REQUEST;
        } else if(response!=WALKER_DIAG_REQUEST) {
            /* Unrelated command owns the mailbox. Do not clobber it. */
            break;
        }
    }
    lastCommand=sharedAddr[4];
    /* Restore the normal in-game-menu command even after timeout, but never
     * overwrite a different command issued by another menu component. */
    if(sharedAddr[4]==WALKER_DIAG_REQUEST ||
       sharedAddr[4]==WALKER_DIAG_REPLY) sharedAddr[4]=WALKER_DIAG_MENU;
    #endif

    clearScreen(false);
    print(1, 1, (const unsigned char *)"VIRTUAL POKEWALKER V7.2.6", FONT_LIME, false);
    print(1, 3, (const unsigned char *)"HeartGold / SoulSilver", FONT_WHITE, false);
    print(1, 5, (const unsigned char *)"Android TCP: 30821", FONT_WHITE, false);
    if(!answered) {
        print(1, 7, (const unsigned char *)"ARM7: no diagnostic reply", FONT_RED, false);
        print(1, 9, (const unsigned char *)"Last IPC: 0x", FONT_WHITE, false);
        printHex(14,9,lastCommand,4,FONT_LIGHT_BLUE,false);
        print(1, 11, (const unsigned char *)"Wi-Fi: NOT ENABLED", FONT_RED, false);
    } else if(diag[0]&8u) {
        /* ARM7 acknowledges the DSi pointer without reading its contents.
         * Mapping of the 0x0C mirror must be validated separately on ARM9. */
        print(1, 7, (const unsigned char *)"Walker: DSi RAM unprobed", FONT_WHITE, false);
        print(1, 9, (const unsigned char *)"Walker ptr: 0x", FONT_WHITE, false);
        printHex(15,9,diag[2],4,FONT_LIGHT_BLUE,false);
        print(1, 11, (const unsigned char *)"Wi-Fi: NOT ENABLED", FONT_RED, false);
    } else if((diag[0]&1u)==0u) {
        if((diag[0]&2u)==0u) {
            print(1, 7, (const unsigned char *)"Walker: hook not published", FONT_RED, false);
        } else if((diag[0]&4u)==0u) {
            print(1, 7, (const unsigned char *)"Walker: RAM addr rejected", FONT_RED, false);
        } else {
            print(1, 7, (const unsigned char *)"Walker: invalid header", FONT_RED, false);
        }
        print(1, 9, (const unsigned char *)"Boot stage: 0x", FONT_WHITE, false);
        printHex(15,9,diag[3]&0xFFu,1,FONT_LIGHT_BLUE,false);
        print(1, 11, walkerBootReason(diag[3]), FONT_LIGHT_BLUE, false);
        print(1, 13, (const unsigned char *)"Wi-Fi: NOT ENABLED", FONT_RED, false);
        if(diag[3] == 3u || diag[3] == 1u)
            print(1, 15, (const unsigned char *)"Check Walker error log", FONT_LIGHT_BLUE, false);
    } else {
        print(1, 7, (const unsigned char *)"Missing net APIs: 0x", FONT_WHITE, false);
        printHex(21,7,diag[1]&0x1FFFu,2,FONT_RED,false);
        print(1, 9, (const unsigned char *)"Resolver:", FONT_WHITE, false);
        print(11,9,(const unsigned char *)((diag[0] & (1u<<16)) ?
            "FLAG SET (unverified)" : "NOT READY"),FONT_RED,false);
        print(1, 11, (const unsigned char *)"Bridge state:", FONT_WHITE, false);
        printDec(17,11,(diag[0]>>8)&0xFFu,2,FONT_LIGHT_BLUE,false);
        print(1, 13, (const unsigned char *)"Write seq:   0x", FONT_WHITE, false);
        printHex(16,13,diag[2],4,FONT_LIGHT_BLUE,false);
        print(1, 14, (const unsigned char *)"Flushed seq: 0x", FONT_WHITE, false);
        printHex(16,14,diag[3],4,FONT_LIGHT_BLUE,false);
        print(1, 16, (const unsigned char *)"Wi-Fi: NOT ENABLED", FONT_RED, false);
    }
    print(1, 18, (const unsigned char *)"X: ARM7 IRQ/timer snapshot", FONT_WHITE, false);
    print(1, 19, (const unsigned char *)"Y: ARM7 boot IRQ table", FONT_WHITE, false);
#ifndef B4DS
    print(1, 20, (const unsigned char *)"L: ARM9 Wi-Fi code audit", FONT_WHITE, false);
    print(1, 22, (const unsigned char *)"R: ARM9 task context", FONT_WHITE, false);
#endif
    print(1, 21, (const unsigned char *)"B: Back to menu", FONT_WHITE, false);
    /* Wait for initial A release, then accept X (snapshot) or B. */
    do {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
    } while(KEYS & KEY_A);
    bool showRadio=false;
    bool showTable=false;
    bool showWifiCode=false;
    bool showTaskContext=false;
    while(1) {
        while(REG_VCOUNT!=191) mySwiDelay(100);
        while(REG_VCOUNT==191) mySwiDelay(100);
        if(KEYS & KEY_B) break;
        if(KEYS & KEY_X){showRadio=true;break;}
        if(KEYS & KEY_Y){showTable=true;break;}
#ifndef B4DS
        if(KEYS & KEY_L){showWifiCode=true;break;}
        if(KEYS & KEY_R){showTaskContext=true;break;}
#endif
    }
    if(showRadio) {
        walkerRadioSnapshotMenu();
    } else if(showTable) {
        walkerIrqTableMenu();
#ifndef B4DS
    } else if(showWifiCode) {
        walkerArm9WifiCodeMenu();
    } else if(showTaskContext) {
        walkerArm9PreWrapperMenu();
#endif
    } else {
        do {
            while(REG_VCOUNT!=191) mySwiDelay(100);
            while(REG_VCOUNT==191) mySwiDelay(100);
        } while(KEYS & KEY_B);
    }
}

static void optionsMenu(s32 *mainScreen, u32 consoleModel) {
	OptionsItem optionsItems[8];
	int optionsItemCount = 0;
	optionsItems[optionsItemCount++] = OPTIONS_MAIN_SCREEN;
	#ifndef B4DS
	if(consoleModel < 2) // Not on 3DS
	#endif
		optionsItems[optionsItemCount++] = OPTIONS_BRIGHTNESS;
	#ifndef B4DS
	optionsItems[optionsItemCount++] = OPTIONS_VOLUME;
	optionsItems[optionsItemCount++] = OPTIONS_REFRESH_RATE;
	optionsItems[optionsItemCount++] = OPTIONS_CLOCK_SPEED;
	optionsItems[optionsItemCount++] = OPTIONS_VRAM_MODE;
	#endif

	bool mainScreenChanged = false;

	u8 cursorPosition = 0;
	while(1) {
		clearScreen(false);

		// Print options
		for(int i = 0; i < optionsItemCount; i++) {
			const unsigned char *optionValue = NULL;
			int optionPercent = 0;
			bool isString = true;
			switch(optionsItems[i]) {
				case OPTIONS_MAIN_SCREEN:
					optionValue = igmText.optionsValues[*mainScreen];
					break;
				case OPTIONS_BRIGHTNESS:
					optionPercent = (u8)(sharedAddr[6] >> 8) * 100 / MAX_BRIGHTNESS;
					isString = false;
					break;
				#ifndef B4DS
				case OPTIONS_VOLUME:
					optionPercent = (u8)(sharedAddr[6] >> 16) * 100 / 31;
					isString = false;
					break;
				case OPTIONS_REFRESH_RATE:
					optionValue = (unsigned char*)refreshRateText[refreshRate];
					break;
				case OPTIONS_CLOCK_SPEED:
					optionValue = igmText.optionsValues[3 + ((REG_SCFG_CLK == 0 ? scfgClkBak : REG_SCFG_CLK) & 1)];
					break;
				case OPTIONS_VRAM_MODE:
					optionValue = igmText.optionsValues[5 + (((REG_SCFG_EXT == 0 ? scfgExtBak : REG_SCFG_EXT) & BIT(13)) >> 13)];
					break;
				#endif
			}

			int digits = optionPercent == 100 ? 3 : (optionPercent >= 10 ? 2 : 1);
			if(igmText.rtl) {
				printRight(0x1D, i, igmText.optionsLabels[optionsItems[i]], FONT_WHITE, false);
				if(isString) {
					print(0, i, optionValue, FONT_WHITE, false);
				} else {
					printDec(0, i, optionPercent, digits, FONT_WHITE, false);
					printChar(0 + digits, i, '%', FONT_WHITE, false);
				}
			} else {
				print(2, i, igmText.optionsLabels[optionsItems[i]], FONT_WHITE, false);
				if(isString) {
					printRight(0x1E, i, optionValue, FONT_WHITE, false);
				} else {
					printDec(0x1E - digits, i, optionPercent, digits, FONT_WHITE, false);
					printChar(0x1E, i, '%', FONT_WHITE, false);
				}
			}
		}
		drawCursor(cursorPosition);
		printMsg(17, igmText.optionsDescriptions[cursorPosition], FONT_WHITE, false);

		waitKeys(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_B | KEY_SELECT);

		if (KEYS & KEY_UP) {
			if(cursorPosition > 0)
				cursorPosition--;
			else
				cursorPosition = optionsItemCount - 1;
		} else if (KEYS & KEY_DOWN) {
			if(cursorPosition < (optionsItemCount - 1))
				cursorPosition++;
			else
				cursorPosition = 0;
		} else if (KEYS & (KEY_LEFT | KEY_RIGHT)) {
			switch(optionsItems[cursorPosition]) {
				case OPTIONS_MAIN_SCREEN:
					(KEYS & KEY_LEFT) ? (*mainScreen)-- : (*mainScreen)++;
					if(*mainScreen > 2)
						*mainScreen = 0;
					else if(*mainScreen < 0)
						*mainScreen = 2;
					mainScreenChanged = true;
					break;
				case OPTIONS_BRIGHTNESS:
				{
					u8 brightness = (u8)(sharedAddr[6] >> 8);
					if(KEYS & KEY_LEFT && brightness > 0)
						brightness--;
					else if (KEYS & KEY_RIGHT && brightness < MAX_BRIGHTNESS)
						brightness++;

					sharedAddr[0] = brightness;
					sharedAddr[4] = 0x4554494C; // LITE
					while(sharedAddr[4] == 0x4554494C) {
						while (REG_VCOUNT != 191) mySwiDelay(100);
						while (REG_VCOUNT == 191) mySwiDelay(100);
					}
					break;
				}
				#ifndef B4DS
				case OPTIONS_VOLUME:
				{
					u8 volume = (u8)(sharedAddr[6] >> 16);
					if(KEYS & KEY_LEFT && volume > 0)
						volume--;
					else if (KEYS & KEY_RIGHT && volume < 31)
						volume++;

					sharedAddr[0] = volume;
					sharedAddr[4] = 0x554C4F56; // VOLU
					while(sharedAddr[4] == 0x554C4F56) {
						while (REG_VCOUNT != 191) mySwiDelay(100);
						while (REG_VCOUNT == 191) mySwiDelay(100);
					}
					break;
				}
				case OPTIONS_REFRESH_RATE:
					const int prevRefreshRate = refreshRate;
					if (KEYS & KEY_LEFT) {
						refreshRate--;
						if (refreshRate < 0) refreshRate = 0;
					} else {
						refreshRate++;
						if (refreshRate == refreshRateCount) refreshRate = refreshRateCount-1;
					}
					if (refreshRate != prevRefreshRate) {
						sharedAddr[0] = refreshRates[refreshRate];
						sharedAddr[4] = 0x41535046; // FPSA
						while(sharedAddr[4] == 0x41535046) {
							while (REG_VCOUNT != 191) mySwiDelay(100);
							while (REG_VCOUNT == 191) mySwiDelay(100);
						}
						if (sharedAddr[0] == 0xFFFFFFFF) {
							refreshRate = prevRefreshRate;
						} else {
							DC_FlushRange(&refreshRate, 4);
						}
					}
					break;
				case OPTIONS_CLOCK_SPEED:
					REG_SCFG_CLK ^= 1;
					if (waitSysCyclesLoc) {
						if (waitSysCyclesLoc[0] == 0xE92D4008) {
							waitSysCyclesLoc[1] = (REG_SCFG_CLK & BIT(1)) ? 0xE1A00100 : 0xE1A00080;
						} else {
							u16* offsetThumb = (u16*)waitSysCyclesLoc;
							offsetThumb[1] = (REG_SCFG_CLK & BIT(1)) ? 0x0080 : 0x0040;
						}
					}
					break;
				case OPTIONS_VRAM_MODE:
					REG_SCFG_EXT ^= BIT(13);
					break;
				#endif
				default:
					break;
			}
		} else if (KEYS & KEY_B) {
			if (mainScreenChanged) {
				sharedAddr[0] = *mainScreen;
				sharedAddr[4] = 0x53435049; // IPCS
				while(sharedAddr[4] == 0x53435049) {
					while (REG_VCOUNT != 191) mySwiDelay(100);
					while (REG_VCOUNT == 191) mySwiDelay(100);
				}
				#ifdef B4DS
				codeJumpWord = ce9->saveMainScreenSetting;
				(*codeJump)();
				#endif
			}
			return;
		}
	}
}

static void jumpToAddress(void) {
	clearScreen(false);

	u8 cursorPosition = 0;
	while(1) {
		toncset16(BG_MAP_RAM_SUB(15) + 0x20 * 9 + 5, '-', 20);
		printCenter(15, 10, igmText.jumpAddress, FONT_WHITE, false);
		printHex(11, 12, (u32)address, 4, FONT_LIGHT_BLUE, false);
		BG_MAP_RAM_SUB(15)[0x20 * 12 + 11 + 6 - cursorPosition] = (BG_MAP_RAM_SUB(15)[0x20 * 12 + 11 + 6 - cursorPosition] & ~(0xF << 12)) | 4 << 12;
		toncset16(BG_MAP_RAM_SUB(15) + 0x20 * 13 + 5, '-', 20);

		waitKeys(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_A | KEY_B);

		if(KEYS & KEY_UP) {
			address = (vu32*)(((u32)address & ~(0xF0 << cursorPosition * 4)) | (((u32)address + (0x10 << (cursorPosition * 4))) & (0xF0 << cursorPosition * 4)));
		} else if(KEYS & KEY_DOWN) {
			address = (vu32*)(((u32)address & ~(0xF0 << cursorPosition * 4)) | (((u32)address - (0x10 << (cursorPosition * 4))) & (0xF0 << cursorPosition * 4)));
		} else if(KEYS & KEY_LEFT) {
			if(cursorPosition < 6)
				cursorPosition++;
		} else if(KEYS & KEY_RIGHT) {
			if(cursorPosition > 0)
				cursorPosition--;
		} else if(KEYS & (KEY_A | KEY_B)) {
			return;
		}
	}
}

static void ramViewer(void) {
	clearScreen(false);
	(*changeMpu)();

	u8 *arm7RamBuffer = ((u8*)sharedAddr) - 0x74C;
	tonccpy(arm7RamBak, arm7RamBuffer, 0xC0);
	bool ramLoaded = false;
	u8 cursorPosition = 0, mode = 0;
	while(1) {
		u8 *ramPtr = arm7Ram ? arm7RamBuffer : (u8*)address;

		unsigned char armText[5] = {'A', 'R', 'M', arm7Ram ? '7' : '9', 0};
		printCenter(14, 0, igmText.ramViewer, FONT_WHITE, false);
		print(27, 0, armText, FONT_LIGHT_BLUE, false);
		printHex(0, 0, (u32)address >> 0x10, 2, FONT_LIGHT_BLUE, false);

		if (arm7Ram && !ramLoaded) {
			sharedAddr[0] = (vu32)arm7RamBuffer;
			sharedAddr[1] = (vu32)address;
			sharedAddr[4] = 0x524D4152; // RAMR
			while (sharedAddr[4] == 0x524D4152) {
				while (REG_VCOUNT != 191) mySwiDelay(100);
				while (REG_VCOUNT == 191) mySwiDelay(100);
			}
		}
		ramLoaded = true;

		for(int i = 0; i < 23; i++) {
			printHex(0, i + 1, (u32)(address + (i * 2)) & 0xFFFF, 2, FONT_LIGHT_BLUE, false);
			for(int j = 0; j < 4; j++)
				printHex(5 + (j * 2), i + 1, ramPtr[(i * 8) + j], 1, 1 + j % 2, false);
			for(int j = 0; j < 4; j++)
				printHex(14 + (j * 2), i + 1, ramPtr[4 + (i * 8) + j], 1, 1 + j % 2, false);
			for(int j = 0; j < 8; j++)
				printChar(23 + j, i + 1, ramPtr[i * 8 + j], FONT_WHITE, false);
		}

		// Change color of selected byte
		if(mode > 0) {
			// Hex
			u16 loc = 0x20 * (1 + (cursorPosition / 8)) + 5 + ((cursorPosition % 8) * 2) + (cursorPosition % 8 >= 4);
			BG_MAP_RAM_SUB(15)[loc] = (BG_MAP_RAM_SUB(15)[loc] & ~(0xF << 12)) | (3 + mode) << 12;
			BG_MAP_RAM_SUB(15)[loc + 1] = (BG_MAP_RAM_SUB(15)[loc + 1] & ~(0xF << 12)) | (3 + mode) << 12;

			// Text
			loc = 0x20 * (1 + (cursorPosition / 8)) + 23 + (cursorPosition % 8);
			BG_MAP_RAM_SUB(15)[loc] = (BG_MAP_RAM_SUB(15)[loc] & ~(0xF << 12)) | (3 + mode) << 12;
		}

		waitKeys(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_A | KEY_B | KEY_Y | KEY_SELECT);

		if(mode == 0) {
			if(KEYS & KEY_R && KEYS & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT)) {
				if (KEYS & KEY_UP) {
					address -= 0x400;
					ramLoaded = false;
				} else if (KEYS & KEY_DOWN) {
					address += 0x400;
					ramLoaded = false;
				} else if (KEYS & KEY_LEFT) {
					address -= 0x4000;
					ramLoaded = false;
				} else if (KEYS & KEY_RIGHT) {
					address += 0x4000;
					ramLoaded = false;
				}
			} else {
				if (KEYS & KEY_UP) {
					address -= 2;
					ramLoaded = false;
				} else if (KEYS & KEY_DOWN) {
					address += 2;
					ramLoaded = false;
				} else if (KEYS & KEY_LEFT) {
					address -= 2 * 23;
					ramLoaded = false;
				} else if (KEYS & KEY_RIGHT) {
					address += 2 * 23;
					ramLoaded = false;
				} else if (KEYS & KEY_A) {
					mode = 1;
				} else if (KEYS & KEY_B) {
					return;
				} else if(KEYS & KEY_Y) {
					jumpToAddress();
					clearScreen(false);
					ramLoaded = false;
				}else if (KEYS & KEY_SELECT) {
					arm7Ram = !arm7Ram;
					ramLoaded = false;
				}
			}
		} else if(mode == 1) {
			if (KEYS & KEY_UP) {
				if(cursorPosition >= 8)
					cursorPosition -= 8;
				else
					address -= 2;
			} else if (KEYS & KEY_DOWN) {
				if(cursorPosition < 8 * 22)
					cursorPosition += 8;
				else
					address += 2;
			} else if (KEYS & KEY_LEFT) {
				if(cursorPosition > 0)
					cursorPosition--;
			} else if (KEYS & KEY_RIGHT) {
				if(cursorPosition < 8 * 23 - 1)
					cursorPosition++;
			} else if (KEYS & KEY_A) {
				mode = 2;
			} else if (KEYS & KEY_B) {
				mode = 0;
			} else if(KEYS & KEY_Y) {
				jumpToAddress();
				clearScreen(false);
			}
		} else if(mode == 2) {
			if (KEYS & KEY_UP) {
				ramPtr[cursorPosition]++;
			} else if (KEYS & KEY_DOWN) {
				ramPtr[cursorPosition]--;
			} else if (KEYS & KEY_LEFT) {
				ramPtr[cursorPosition] -= 0x10;
			} else if (KEYS & KEY_RIGHT) {
				ramPtr[cursorPosition] += 0x10;
			} else if (KEYS & (KEY_A | KEY_B)) {
				if(arm7Ram) {
					sharedAddr[0] = (vu32)arm7RamBuffer;
					sharedAddr[1] = (vu32)address;
					sharedAddr[2] = cursorPosition;
					sharedAddr[4] = 0x574D4152; // RAMW
					while (sharedAddr[4] == 0x574D4152) {
						while (REG_VCOUNT != 191) mySwiDelay(100);
						while (REG_VCOUNT == 191) mySwiDelay(100);
					}
					ramLoaded = false;
				}
				mode = 1;
			}
		}
	}
	tonccpy(arm7RamBuffer, arm7RamBak, 0xC0);
	(*revertMpu)();
}

#if !defined(B4DS) && !defined(TWLSDK)
u32 inGameMenu(s32 *mainScreen, u32 consoleModel, s32 *exceptionRegisters,
               const WalkerArm9Snapshot *preMenu9) {
    if(preMenu9 && preMenu9->magic == WALKER_ARM9_SNAPSHOT_MAGIC)
        walkerArm9PreWrapper = *preMenu9;
    else
        walkerArm9PreWrapper.magic=0u;
#else
u32 inGameMenu(s32 *mainScreen, u32 consoleModel, s32 *exceptionRegisters) {
    walkerArm9PreWrapper.magic=0u;
#endif
	// If we were given exception registers, then we're handling an exception
	bool exception = (exceptionRegisters != 0);

	#ifdef B4DS
	static bool ce9Set = false;
	if (!ce9Set) {
		ce9 = (cardengineArm9*)consoleModel;
		ce9Set = true;
	}
	#endif

	u32 res = 0;

	u32 dispcnt = REG_DISPCNT_SUB;
	u16 bg0cnt = REG_BG0CNT_SUB;
	u16 bg1cnt = REG_BG1CNT_SUB;
	u16 bg2cnt = REG_BG2CNT_SUB;
	u16 bg3cnt = REG_BG3CNT_SUB;

	u8 vramCCr = VRAM_C_CR;
	u8 vramHCr = VRAM_H_CR;

	u16 powercnt = REG_POWERCNT;

	u16 masterBright = *(vu16*)0x0400106C;

	REG_DISPCNT_SUB = MODE_0_2D | DISPLAY_BG3_ACTIVE;
	REG_BG0CNT_SUB = 0;
	REG_BG1CNT_SUB = 0;
	REG_BG2CNT_SUB = 0;
	REG_BG3CNT_SUB = (u16)(BG_MAP_BASE(15) | BG_TILE_BASE(0) | BgSize_T_256x256);

	if(VRAM_C_CR & 4) // If VRAM C is mapped to sub bg, unmap it
		VRAM_C_CR = VRAM_C_LCD;
	VRAM_H_CR = VRAM_ENABLE | VRAM_H_SUB_BG;

	REG_BG3VOFS_SUB = 0;
	REG_BG3HOFS_SUB = 0;

	// If main screen is on auto, then force the bottom
	REG_POWERCNT |= POWER_SWAP_LCDS;

	SetBrightness(1, 0);
	REG_MOSAIC_SUB = 0; // Register is write only, can't back up
	REG_BLDCNT_SUB = 0; // Register is write only, can't back up
	REG_BLDALPHA_SUB = 0; // Register is write only, can't back up
	REG_BLDY_SUB = 0; // Register is write only, can't back up

	tonccpy(bgMapBak, BG_MAP_RAM_SUB(15), sizeof(bgMapBak));	// Backup BG_MAP_RAM
	clearScreen(false);

	tonccpy(palBak, BG_PALETTE_SUB, sizeof(palBak));	// Backup the palette
	toncset16(BG_PALETTE_SUB, igmPal[exception ? 7 : 6], 256);
	for(int i = 0; i < 6; i++) {
		BG_PALETTE_SUB[i * 0x10 + 1] = igmPal[i];
	}

	tonccpy(bgBak, BG_GFX_SUB, sizeof(igmText.font) * 4);	// Backup the original graphics
	for(int i = 0; i < sizeof(igmText.font); i++) {	// Load font from 1bpp to 4bpp
		u8 val = igmText.font[i];
		BG_GFX_SUB[i * 2]     = (val & 1) | ((val & 2) << 3) | ((val & 4) << 6) | ((val & 8) << 9);
		val >>= 4;
		BG_GFX_SUB[i * 2 + 1] = (val & 1) | ((val & 2) << 3) | ((val & 4) << 6) | ((val & 8) << 9);
	}

	// Let ARM7 know the menu loaded
	sharedAddr[5] = 0x59444552; // 'REDY'

	MenuItem menuItems[9];
	int menuItemCount = 0;
	if(!exception)
		menuItems[menuItemCount++] = MENU_EXIT;
	menuItems[menuItemCount++] = MENU_RESET;
	menuItems[menuItemCount++] = MENU_SCREENSHOT;
	if(igmText.manualMaxLine > 0 && !exception)
		menuItems[menuItemCount++] = MENU_MANUAL;
	menuItems[menuItemCount++] = MENU_RAM_DUMP;
	if(!exception)
		menuItems[menuItemCount++] = MENU_OPTIONS;
	menuItems[menuItemCount++] = MENU_RAM_VIEWER;
	#ifndef B4DS
	if(!exception) menuItems[menuItemCount++] = MENU_VIRTUAL_POKEWALKER;
	#endif
	menuItems[menuItemCount++] = MENU_QUIT;

	if(exception) {
		showException(exceptionRegisters);
	}

	// Wait for keys to be released
	drawMainMenu(menuItems, menuItemCount);
	drawCursor(0);
	do {
		printTime();
		#ifndef B4DS
		printBattery();
		#endif
		while (REG_VCOUNT != 191) mySwiDelay(100);
		while (REG_VCOUNT == 191) mySwiDelay(100);
	} while(KEYS & igmText.hotkey);

	u8 cursorPosition = 0;
	while (sharedAddr[4] == 0x554E454D) {
		drawMainMenu(menuItems, menuItemCount);
		drawCursor(cursorPosition);
		printTime();
#ifndef B4DS
		printBattery();
#endif

		if(exception)
			waitKeys(KEY_UP | KEY_DOWN | KEY_A);
		else
			waitKeys(KEY_UP | KEY_DOWN | KEY_A | KEY_B);

		if (KEYS & KEY_UP) {
			if (cursorPosition > 0)
				cursorPosition--;
			else
				cursorPosition = menuItemCount - 1;
		} else if (KEYS & KEY_DOWN) {
			if (cursorPosition < (menuItemCount - 1))
				cursorPosition++;
			else
				cursorPosition = 0;
		} else if (KEYS & KEY_A) {
			switch(menuItems[cursorPosition]) {
				case MENU_EXIT:
					do {
						while (REG_VCOUNT != 191) mySwiDelay(100);
						while (REG_VCOUNT == 191) mySwiDelay(100);
					} while(KEYS & KEY_A);
					// sharedAddr[1] = 0;
					sharedAddr[4] = 0x54495845; // EXIT
					while (sharedAddr[4] != 0) swiDelay(100);
					break;
				case MENU_RESET:
					if (boolQuestion(igmText.resetGameMessage)) {
						extern bool exceptionPrinted;
						exceptionPrinted = false;
						res = 0x52534554; // TESR
						sharedAddr[3] = res;
						sharedAddr[4] = 0x54455352; // RSET
					}
					break;
				case MENU_SCREENSHOT:
					screenshot();
					break;
				case MENU_MANUAL:
					manual();
					break;
				case MENU_RAM_DUMP:
					#ifndef B4DS
					sharedAddr[4] = 0x444D4152; // RAMD
					while (sharedAddr[4] == 0x444D4152) {
						while (REG_VCOUNT != 191) mySwiDelay(100);
						while (REG_VCOUNT == 191) mySwiDelay(100);
					}
					#else
					// sharedAddr[1] = 0;
					res = 0x444D4152; // RAMD
					sharedAddr[3] = res;
					sharedAddr[4] = 0x54495845; // EXIT
					while (sharedAddr[4] != 0) swiDelay(100);
					#endif
					break;
				case MENU_OPTIONS:
					optionsMenu(mainScreen, consoleModel);
					break;
				case MENU_RAM_VIEWER:
					ramViewer();
					break;
				case MENU_VIRTUAL_POKEWALKER:
					virtualPokewalkerMenu();
					break;
				case MENU_QUIT:
					if (boolQuestion(igmText.quitGameMessage)) {
						res = 0x54495845; // EXIT
						sharedAddr[3] = res;
						sharedAddr[4] = 0x54495551; // QUIT
					}
					break;
				default:
					break;
			}
		} else if (KEYS & KEY_B && !exception) {
			do {
				while (REG_VCOUNT != 191) mySwiDelay(100);
				while (REG_VCOUNT == 191) mySwiDelay(100);
			} while(KEYS & KEY_B);
			// sharedAddr[1] = 0;
			sharedAddr[4] = 0x54495845; // EXIT
			while (sharedAddr[4] != 0) swiDelay(100);
		} /* else if (KEYS & KEY_R && !exception) {
			do {
				while (REG_VCOUNT != 191) mySwiDelay(100);
				while (REG_VCOUNT == 191) mySwiDelay(100);
			} while(KEYS & KEY_R);
			sharedAddr[1] = 1;
			sharedAddr[4] = 0x54495845; // EXIT
			while (sharedAddr[4] != 0) swiDelay(100);
		} */
	}

	tonccpy(BG_MAP_RAM_SUB(15), bgMapBak, sizeof(bgMapBak));	// Restore BG_MAP_RAM
	tonccpy(BG_PALETTE_SUB, palBak, sizeof(palBak));	// Restore the palette
	tonccpy(BG_GFX_SUB, bgBak, sizeof(igmText.font) * 4);	// Restore the original graphics

	*(vu16*)0x0400106C = masterBright;

	REG_DISPCNT_SUB = dispcnt;
	REG_BG0CNT_SUB = bg0cnt;
	REG_BG1CNT_SUB = bg1cnt;
	REG_BG2CNT_SUB = bg2cnt;
	REG_BG3CNT_SUB = bg3cnt;

	VRAM_C_CR = vramCCr;
	VRAM_H_CR = vramHCr;

	REG_POWERCNT = powercnt;

	if(*mainScreen == 1)
		REG_POWERCNT &= ~POWER_SWAP_LCDS;
	else if(*mainScreen == 2)
		REG_POWERCNT |= POWER_SWAP_LCDS;

	return res;
}