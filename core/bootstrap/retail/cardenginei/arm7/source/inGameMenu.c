#include <nds/ndstypes.h>
#include <nds/ipc.h>
#include <nds/interrupts.h>
#include <nds/timers.h>
#include <nds/input.h>
#include <nds/arm7/audio.h>
#include <nds/arm7/clock.h>
#include <nds/arm7/i2c.h>
#include <time.h>

#include "igm_text.h"
#include "locations.h"
#include "cardengine.h"
#include "fpsAdjust.h"
#include "nds_header.h"
#include "walker_emu.h"
#include "walker_hgss_net.h"
#include "tonccpy.h"

#define sleepMode BIT(17)

#define REG_EXTKEYINPUT (*(vuint16*)0x04000136)

extern u32 valueBits;
extern s32 mainScreen;


extern u8 consoleModel;

extern vu32* volatile sharedAddr;

/* Read-only Virtual Pokewalker diagnostics; the ARM7 owns the live control
 * address. No network calls and no changes to the walker or save. */
#ifndef TWLSDK
extern u32 walkerControl;
extern u32 walkerBootStatus;
#define WALKER_DIAG_REQUEST 0x47445057u /* WPDG */
#define WALKER_DIAG_REPLY   0x4B445057u /* WPDK */
/* V7.2 register snapshot only; no Wi-Fi initialization or register writes. */
#define WALKER_RADIO_REQUEST 0x44525057u /* WPRD */
#define WALKER_RADIO_REPLY   0x4B525057u /* WPRK */
static u32 radioIeBeforeMenu, radioImeBeforeMenu;
static u16 radioTimersBeforeMenu[4];

static void walkerRadioReadOnlyDiagnostics(void) {
    sharedAddr[0]=radioIeBeforeMenu;
    sharedAddr[1]=radioImeBeforeMenu;
    sharedAddr[2]=(u32)radioTimersBeforeMenu[0] |
                  ((u32)radioTimersBeforeMenu[1]<<16);
    sharedAddr[3]=(u32)radioTimersBeforeMenu[2] |
                  ((u32)radioTimersBeforeMenu[3]<<16);
    sharedAddr[4]=WALKER_RADIO_REPLY;
}
static void walkerReadOnlyDiagnostics(void) {
    /* Query result in sharedAddr[0..3]: presence/state/ready, missing mask,
     * write sequence, flushed sequence (or loader boot outcome if absent).
     * This menu protocol is temporary:
     * only used while the in-game menu is active on both processors. */
    sharedAddr[0] = 0u;
    sharedAddr[1] = 0x1FFFu; /* 13 missing network functions by default. */
    sharedAddr[3] = walkerBootStatus; /* Read-only boot status until header valid. */
    const u32 address=walkerControl;
    sharedAddr[2] = address; /* Show raw pointer if header is not inspected. */
    /* Status bits: bit0 valid header, bit1 hook address was published,
     * bit2 safely inspected in DS RAM, bit3 DSi extended pointer deferred.
     * V7.1.2 MUST NOT dereference the 0x0C mirror from the ARM7 menu:
     * the mapping is not proven for this NTR runtime configuration. */
    if(address) sharedAddr[0] |= 2u;
    if(walkerControlAddressIsDsiMirror(address)) {
        sharedAddr[0] |= 8u; /* Pointer published; contents NOT inspected. */
    } else if(walkerControlAddressReadable(address)) {
        sharedAddr[0] |= 4u;
        const WalkerControl *c=(const WalkerControl *)address;
        if(c->magic==WALKER_MAGIC && c->version==WALKER_VERSION) {
            const u32 state = c->direct.magic==WALKER_DIRECT_BRIDGE_MAGIC ?
                (c->direct.state & 0xFFu) : 0u;
            const u32 ready = c->hgssNet.magic==WALKER_HGSS_NET_MAGIC ?
                (c->hgssNet.ready & 1u) : 0u;
            sharedAddr[0] |= 1u | (state << 8) | (ready << 16);
            sharedAddr[1] = walkerHgssNetMissingMask(&c->hgssNet);
            sharedAddr[2] = c->writeSeq;
            sharedAddr[3] = c->flushedSeq;
        }
    }
    sharedAddr[4] = WALKER_DIAG_REPLY;
}
#endif
// extern bool returnToMenu;
extern int afterSwapTimer;

extern struct IgmText *igmText;

extern void reset(const bool downloadedSrl);
extern void dumpRam(void);
extern void returnToLoader(bool reboot);
extern void prepareScreenshot(void);
extern void saveScreenshot(void);
extern void prepareManual(void);
extern void readManual(int line);
extern void restorePreManual(void);
extern void saveMainScreenSetting(void);
extern void loadInGameMenu(void);
extern void unloadInGameMenu(void);

extern u16 biosRead16(u32 addr);

void biosRead(void* dst, const void* src, u32 len)
{
	u16* _dst = (u16*)dst;
	
	for (u32 i = 0; i < len; i+=2)
	{
		_dst[i>>1] = biosRead16(((u32)src) + i);
	}
}

volatile int timeTillStatusRefresh = 7;

void inGameMenu(void) {
    /* Snapshot BEFORE the menu masks interrupts. This is diagnostic only;
     * a captured IRQ enable bit never proves who owns the IRQ handler. */
#ifndef TWLSDK
    radioIeBeforeMenu=REG_IE;
    radioImeBeforeMenu=REG_IME;
    for(unsigned i=0;i<4;i++) radioTimersBeforeMenu[i]=TIMER_CR(i);
#endif
	// returnToMenu = false;
	sharedAddr[4] = 0x554E454D; // 'MENU'
	const u32 errorBak = sharedAddr[0];
	IPC_SendSync(0x9);
	REG_MASTER_VOLUME = 0;
	int oldIME = enterCriticalSection();

	loadInGameMenu();

	int timeOut = 0;
	while (sharedAddr[5] != 0x59444552) { // 'REDY'
		while (REG_VCOUNT != 191) swiDelay(100);
		while (REG_VCOUNT == 191) swiDelay(100);

		timeOut++;
		if (timeOut == 60*2) {
			returnToLoader(true);
			timeOut = 0;
		}
	}

	if (sharedAddr[4] == 0x554E454D) {
		bool exitMenu = false;
		while (!exitMenu) {
			sharedAddr[5] = ~REG_KEYINPUT & 0x3FF;
			sharedAddr[5] |= ((~REG_EXTKEYINPUT & 0x3) << 10) | ((~REG_EXTKEYINPUT & 0xC0) << 6);
			if ((REG_EXTKEYINPUT & BIT(7)) && (valueBits & sleepMode) && (consoleModel < 2)) {
				// Save current power state.
				int power = readPowerManagement(PM_CONTROL_REG);
				// Set sleep LED. (Does not work)
				writePowerManagement(PM_CONTROL_REG, PM_LED_CONTROL(1));

				// Power down till we get our interrupt.
				swiSleep();

				while (REG_EXTKEYINPUT & BIT(7)) {
					//100ms
					swiDelay(838000);
				}

				// Restore power state.
				writePowerManagement(PM_CONTROL_REG, power);
			}
			timeTillStatusRefresh++;
			if (timeTillStatusRefresh >= 8) {
				timeTillStatusRefresh = 0;

				u8 brightness = i2cReadRegister(I2C_PM, 0x41);
				u32 pmControl = readPowerManagement(PM_CONTROL_REG);
				if(brightness && !(pmControl & 0xC)) { // Turn on backlights if SELECT+volume used
					pmControl |= 0xC;
					writePowerManagement(PM_CONTROL_REG, pmControl);
				}

				sharedAddr[6] = i2cReadRegister(I2C_PM, I2CREGPM_BATTERY); // Battery
				sharedAddr[6] |= (brightness + ((pmControl & 0xC) != 0)) << 8; // Brightness
				sharedAddr[6] |= i2cReadRegister(I2C_PM, I2CREGPM_VOL) << 16; // Volume

				RTCtime dstime;
				rtcGetTimeAndDate((uint8 *)&dstime);
				sharedAddr[7] = dstime.hours;
				sharedAddr[8] = dstime.minutes;
				sharedAddr[7] += 0x10000000; // Set time receive flag
			}

			while (REG_VCOUNT != 191) swiDelay(100);
			while (REG_VCOUNT == 191) swiDelay(100);

			/* Snapshot the command actually dispatched this frame. A new
			 * ARM9 request may arrive between dispatch and the idle reset. */
			const u32 menuCommandSeen=sharedAddr[4];
			switch (menuCommandSeen) {
				/* case 0x54495845: // EXIT
					exitMenu = true;
					break; */
				case 0x54455352: // RSET
					exitMenu = true;
					timeTillStatusRefresh = 7;
					unloadInGameMenu();
					#ifdef TWLSDK
					i2cWriteRegister(0x4A, 0x12, 0x01);
					#endif
					reset(false);
					break;
				case 0x54495551: // QUIT
					unloadInGameMenu();
					returnToLoader(false);
					exitMenu = true;
					break;
				case 0x53435049: // IPCS
					mainScreen = sharedAddr[0];
					saveMainScreenSetting();
					afterSwapTimer = 0;
					break;
				case 0x41535046: // FPSA
					#ifndef TWLSDK
					extern fpsa_t sActiveFpsa;

					const u32 num = sharedAddr[0];
					if (num == 60000) {
						fpsa_stop(&sActiveFpsa);
					} else {
						fpsa_init(&sActiveFpsa);
						fpsa_setTargetFpsFraction(&sActiveFpsa, num, num >= 1000 ? 1001 : 1);
						fpsa_start(&sActiveFpsa);
					}
					#else
					sharedAddr[0] = 0xFFFFFFFF;
					#endif
					break;
				case 0x444D4152: // RAMD
					dumpRam();
					exitMenu = true;
					break;
				/* case 0x50455453: // STEP
					returnToMenu = true;
					exitMenu = true;
					break; */
				case 0x50505353: // SSPP
					prepareScreenshot();
					break;
				case 0x544F4853: // SHOT
					saveScreenshot();
					break;
				case 0x4E414D50: // PMAN
					prepareManual();
					break;
				case 0x554E414D: // MANU
					readManual(sharedAddr[0]);
					break;
				case 0x4E414D52: // RMAN
					restorePreManual();
					break;

                #ifndef TWLSDK
                case WALKER_DIAG_REQUEST: // WPDG: read-only diagnostics
                    walkerReadOnlyDiagnostics();
                    break;
                case WALKER_RADIO_REQUEST: // WPRD: read-only IRQ/timer snapshot
                    walkerRadioReadOnlyDiagnostics();
                    break;
                #endif
				case 0x524D4152: // RAMR
					u32* dst = (u32*)((u32)sharedAddr[0]);
					u32* src = (u32*)((u32)sharedAddr[1]);
					for (int i = 0; i < 0xC0/8; i++) {
						if ((u32)src >= 0x8000) {
							tonccpy(dst, src, 8);
						} else {
							biosRead(dst, src, 8);
						}
						dst++;
						dst++;
						src++;
						src++;
					}
					break;
				case 0x574D4152: // RAMW
					if (sharedAddr[1]+sharedAddr[2] >= 0x8000) {
						tonccpy((u8*)((u32)sharedAddr[1])+sharedAddr[2], (u8*)((u32)sharedAddr[0])+sharedAddr[2], 1);
					}
					break;
				case 0x4554494C: // LITE
					if(sharedAddr[0] == 0) {
						writePowerManagement(PM_CONTROL_REG, readPowerManagement(PM_CONTROL_REG) & ~0xC);
					} else {
						i2cWriteRegister(I2C_PM, 0x41, sharedAddr[0] - 1);
						writePowerManagement(PM_CONTROL_REG, readPowerManagement(PM_CONTROL_REG) | 0xC);
					}
					timeTillStatusRefresh = 7;
					break;
				case 0x554C4F56: // VOLU
					i2cWriteRegister(I2C_PM, I2CREGPM_VOL, sharedAddr[0]);
					timeTillStatusRefresh = 7;
					break;
				default:
					break;
			}

			if (sharedAddr[4] == 0x54495845) { // EXIT
				// returnToMenu = (sharedAddr[1]);
				exitMenu = true;
			} else if (!exitMenu
                #ifndef TWLSDK
                && sharedAddr[4] != WALKER_DIAG_REPLY
                && sharedAddr[4] != WALKER_RADIO_REPLY
                #endif
                && sharedAddr[4] == menuCommandSeen
            ) {
                /* Don't discard a fresh WPDG posted after the switch. */
				sharedAddr[4] = 0x554E454D; // MENU
			}
		}
	}

	sharedAddr[0] = errorBak;
	sharedAddr[4] = 0;
	sharedAddr[7] -= 0x10000000; // Clear time receive flag
	timeTillStatusRefresh = 7;

	unloadInGameMenu();

	leaveCriticalSection(oldIME);
	REG_MASTER_VOLUME = 127;
}
