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
#define WALKER_POSTEXIT_REV 2u
#define WALKER_POSTEXIT_STATE_MAGIC 0x31535050u /* 'PPS1' */
#define WALKER_POSTEXIT_OV_NETWORK 0u
#define WALKER_POSTEXIT_OV_WALKER 112u
#define WALKER_POSTEXIT_LOAD_ASYNC 2u /* pret/pokeheartgold OVY_LOAD_ASYNC */

/* Caller-owned, per-session state: an async overlay load may not become
 * active in the same frame. Once accepted, NEVER enqueue a duplicate load.
 * Reset only after the game's original overlay manager has completed
 * teardown, never while an async load could still be pending. */
typedef struct WalkerHgssPostExitState {
    uint32_t magic;
    uint32_t loadRequested; /* 0=never requested, 1=accepted/in-flight */
} WalkerHgssPostExitState;

typedef struct WalkerHgssPostExit {
    uint32_t magic;
    uint32_t version;
    /* Required persistent state across consecutive game-main-thread frames.
     * A local/temporary state would reissue OVY_LOAD_ASYNC on every tick. */
    WalkerHgssPostExitState *state;
    /* Original game's sOverlayRegions[3][8], verified exact ROM build.
     * Main menu overlay 74 occupies a different range from ov0; never
     * attempt to load ov13 here (it overlaps main menu overlay 74). */
    const WalkerHgssOverlaySlot *gameOverlaySlots;
    /* Return 1 only for a proven synchronous game-main-thread frame
     * callback, with the original IR app's exit handler completed,
     * interrupts enabled, and no NitroFS operation on the stack. */
    int (*safeMainThreadAfterExit)(void);
    /* The game has actually checked out a Pokémon to the virtual
     * EEPROM and ARM7 has durably committed it to SD. No unrelated
     * main-menu action should load the network overlay automatically. */
    int (*verifiedCheckoutPending)(void);
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
 * A missing game lifecycle hook must leave this function unused.
 * The caller must initialize state.magic=... and state.loadRequested=0
 * before the first safe frame; state must outlive all async callbacks. */
int walkerHgssPostExitPrepare(const WalkerHgssPostExit *req);
#endif
