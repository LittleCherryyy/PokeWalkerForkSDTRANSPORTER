/* HGSS game-managed post-Pokewalker networking overlay handoff.
 * GPL-3.0-or-later.
 *
 * NEVER call this from ARM7 VBlank, virtual IR SPI, cardRead/cardReadNormal
 * or another Nitro FS callback. HandleLoadOverlay performs NitroFS
 * reads and may itself invoke nds-bootstrap's cardRead -> recursion.
 * It is callable only from a verified MAIN THREAD application-frame
 * point AFTER OverlayManager_Run unloaded Pokewalker overlay 112.
 *
 * This does NOT associate the Wi-Fi radio or start Nintendo SOC.
 */
#ifndef WALKER_HGSS_POSTEXIT_H
#define WALKER_HGSS_POSTEXIT_H
#include <stdint.h>
#include "walker_hgss_soc_radio.h"

#define WALKER_POSTEXIT_MAGIC 0x31585050u /* 'PPX1' */
#define WALKER_POSTEXIT_REV 1u
#define WALKER_POSTEXIT_OV_NETWORK 0u
#define WALKER_POSTEXIT_OV_WALKER 112u
#define WALKER_POSTEXIT_LOAD_ASYNC 2u /* pret/pokeheartgold OVY_LOAD_ASYNC */

typedef struct WalkerHgssPostExit {
    uint32_t magic;
    uint32_t version;
    /* Original game's sOverlayRegions[3][8], verified exact ROM build.
     * Main menu overlay 74 occupies a different range from ov0; never
     * attempt to load ov13 here (it overlaps main menu overlay 74). */
    const WalkerHgssOverlaySlot *gameOverlaySlots;
    /* Return 1 only for a proven synchronous game-main-thread frame
     * callback, with the original IR app's exit handler completed,
     * interrupts enabled, and no NitroFS operation on the stack. */
    int (*safeMainThreadAfterExit)(void);
    /* Exact original game ABI from src/poke_overlay.c:
     * BOOL HandleLoadOverlay(FSOverlayID ovyId, PMOverlayLoadType how).
     * Verified callable ARM9 MAIN CODE address required; no ROM patch
     * offsets guessed from title code. */
    int (*handleLoadOverlay)(uint32_t overlayId, uint32_t how);
} WalkerHgssPostExit;

/* Returns:
 *   1 = original game manager reports network ov0 LIVE and ov112 ABSENT
 *   0 = not ready or failed safely (do not start a phone send)
 *  -1 = configuration is invalid; reject caller and ROM revision.
 * A missing game lifecycle hook must leave this function unused. */
int walkerHgssPostExitPrepare(const WalkerHgssPostExit *req);
#endif
