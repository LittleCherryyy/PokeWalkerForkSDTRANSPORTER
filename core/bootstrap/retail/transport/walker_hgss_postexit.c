/* Safe handoff to game-owned Nitro overlay manager, source-only until an
 * actual original-HGSS main-frame callback has been resolved/verified.
 * GPL-3.0-or-later.
 *
 * The original src/overlay_manager.c unloads overlay 112 AFTER the
 * application's exit handler; src/poke_overlay.c handles overlay 0
 * with HandleLoadOverlay(0,OVY_LOAD_ASYNC).
 *
 * This code never guesses a retail function address, changes the
 * game's overlay table by hand, or calls game functions in cardRead.
 */
#if defined(WALKER_HGSS_POSTEXIT_HOST_TEST) || ( \
    defined(WALKER_HGSS_SOC_EXACT_ROM_VERIFIED) && \
    defined(WALKER_HGSS_POST_UNLOAD_HOOK_VERIFIED) && \
    defined(WALKER_HGSS_WFC_LIFECYCLE_VERIFIED) && \
    defined(WALKER_HGSS_RAM_MAPPED_VERIFIED))
#include "walker_hgss_postexit.h"
#include <stddef.h>
#include <stdint.h>

static int correctMainThread(const WalkerHgssPostExit *req) {
    return req->safeMainThreadAfterExit &&
           req->safeMainThreadAfterExit()>0;
}
static int originalManagerFunction(const WalkerHgssPostExit *req) {
    if(!req->handleLoadOverlay)return 0;
#if !defined(WALKER_HGSS_POSTEXIT_HOST_TEST)
    uintptr_t entry=((uintptr_t)req->handleLoadOverlay)&~(uintptr_t)1u;
    /* Validated US Rev0 uncompressed ARM9 MAIN image: 0x02000000..
     * 0x02111ef8; this broad window is only one prerequisite, not a
     * unique binary signature. The loader MUST separately verify SHA. */
    if(entry<0x02000000u || entry>=0x02112000u)return 0;
#endif
    return 1;
}
static int overlayStates(const WalkerHgssOverlaySlot *slots){
    if(!slots)return -1;
#if !defined(WALKER_HGSS_POSTEXIT_HOST_TEST)
    uintptr_t p=(uintptr_t)slots;
    if((p&3u)!=0 || p<0x02000000u ||
       p>0x02400000u-WALKER_HGSS_OVERLAY_SLOTS*sizeof(*slots))
        return -1;
#endif
    int network=0, walker=0;
    for(unsigned i=0;i<WALKER_HGSS_OVERLAY_SLOTS;i++){
        if(slots[i].active>1u)return -1;
        if(!slots[i].active)continue;
        if(slots[i].id==WALKER_POSTEXIT_OV_NETWORK)network++;
        if(slots[i].id==WALKER_POSTEXIT_OV_WALKER)walker++;
    }
    if(network>1 || walker>1)return -1;
    if(walker)return 0; /* never overwrite loaded Pokewalker IR code */
    return network?1:2; /* 2 means safe to request game-managed load */
}
int walkerHgssPostExitPrepare(const WalkerHgssPostExit *req){
    if(!req || req->magic!=WALKER_POSTEXIT_MAGIC ||
       req->version!=WALKER_POSTEXIT_REV ||
       !req->state || req->state->magic!=WALKER_POSTEXIT_STATE_MAGIC ||
       req->state->loadRequested>1u ||
       !req->gameOverlaySlots || !originalManagerFunction(req))
        return -1;
    /* Never risk HandleLoadOverlay() from inside cardRead(), where it
     * would recursively read NitroFS with a filesystem lock held. */
    if(!correctMainThread(req) || !req->verifiedCheckoutPending ||
       req->verifiedCheckoutPending()<=0)return 0;
    int state=overlayStates(req->gameOverlaySlots);
    if(state<=0)return state<0?-1:0;
    if(state==1)return 1;
    /* OVY_LOAD_ASYNC may return success before the manager marks ov0
     * active. Poll the original table on later main-thread frames,
     * without requesting the same overlay twice. A lost/incomplete
     * request fails closed; the caller must not reset this state until
     * the game's manager has finished teardown. */
    if(req->state->loadRequested)return 0;
    /* The game owns overlay-manager refcounts, region collision checks,
     * game heap and async filesystem completion. All handled by original
     * HandleLoadOverlay, never reimplemented in nds-bootstrap. */
    if(req->handleLoadOverlay(WALKER_POSTEXIT_OV_NETWORK,
                             WALKER_POSTEXIT_LOAD_ASYNC)<=0)return 0;
    req->state->loadRequested=1u;
    /* Return success only when the actual game reports ov0 active. */
    return overlayStates(req->gameOverlaySlots)==1?1:0;
}
#endif
