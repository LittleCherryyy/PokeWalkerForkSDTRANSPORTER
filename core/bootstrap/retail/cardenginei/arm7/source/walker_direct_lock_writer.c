/* DSi NTR resident ARM7 persistent direct-Pokewalker checkout fence.
 * GPL-3.0-or-later.
 *
 * Launcher preallocates <save>.walker.directlock (512 bytes) and hands
 * its FAT cluster to this cardengine. There are no runtime FAT directory
 * operations. This MUST run with the existing SD saveMutex held, and
 * the SD driver initialized / NDMA slot configured by the caller.
 *
 * We persist PENDING *before* the first TCP byte. After reboot the launcher
 * refuses HGSS if the Android may own the Pokémon. This is deliberately
 * fail-closed: network failure requires explicit recovery, not a silent
 * re-import from the SD image.
 */
#include <nds/ndstypes.h>
#include "my_fat.h"
#include "walker_emu.h"
#include "walker_direct_lock.h"

#ifndef TWLSDK
extern u32 walkerControl;
extern u32 walkerDirectLockCluster;
extern bool gen5CheckedIO(void *,aFile *,u32,u32,bool);

static aFile lockFile;
static bool lockOpened;
static unsigned char lockSector[WALKER_LOCK_SIZE];

static WalkerControl *lockControl(void) {
    WalkerControl *c=(WalkerControl *)walkerControl;
    if(!c || c->magic!=WALKER_MAGIC || c->version!=WALKER_VERSION ||
       c->direct.magic!=WALKER_DIRECT_BRIDGE_MAGIC ||
       !c->cluster || !walkerDirectLockCluster)return 0;
    return c;
}
bool walkerDirectLockDue(void) {
    WalkerControl *c=lockControl();
    return c && c->checkoutState==WALKER_CHECKOUT_COMPLETE &&
        c->direct.state==WALKER_DIRECT_PUSH_READY &&
        c->direct.lockRequested && !c->direct.lockReady &&
        c->writeSeq && c->writeSeq==c->flushedSeq &&
        c->writeSeq==c->direct.durableSeq &&
        c->writeSeq==c->direct.offeredSeq;
}
void walkerDirectLockWrite(void) {
    WalkerControl *c=lockControl();
    if(!c || !walkerDirectLockDue())return;
    if(!lockOpened) {
        getFileFromCluster(&lockFile,walkerDirectLockCluster,false);
        lockOpened=true;
    }
    /* Fail closed if a prior crashed checkout already owns the file. */
    if(!gen5CheckedIO(lockSector,&lockFile,0,WALKER_LOCK_SIZE,false) ||
       walkerLockDecode(lockSector)!=WALKER_LOCK_PREPARED) {
        c->direct.error=WALKER_DIRECT_ERR_STORAGE;
        return;
    }
    const u32 seq=c->writeSeq;
    if(!walkerLockPending(lockSector,seq,c->direct.crc32,
                          c->direct.session,c->direct.trainer)) {
        c->direct.error=WALKER_DIRECT_ERR_PROTOCOL;
        return;
    }
    /* gen5CheckedIO writes and physically verifies the full 512-byte
     * sector. No network ownership is advertised until this succeeds. */
    if(!gen5CheckedIO(lockSector,&lockFile,0,WALKER_LOCK_SIZE,true)) {
        c->direct.error=WALKER_DIRECT_ERR_STORAGE;
        return;
    }
    /* Verify the in-RAM record and the unchanged ownership offer after
     * the checked SD write; a changing game invalidates the transfer,
     * while the durable PENDING record remains safe across power loss. */
    if(walkerLockDecode(lockSector)!=WALKER_LOCK_PENDING ||
       c->direct.state!=WALKER_DIRECT_PUSH_READY ||
       c->writeSeq!=seq || c->flushedSeq!=seq ||
       c->direct.offeredSeq!=seq ||
       !c->direct.lockRequested){
        c->direct.error=WALKER_DIRECT_ERR_STORAGE;
        return;
    }
    c->direct.error=WALKER_DIRECT_ERR_NONE;
    c->direct.lockReady=1;
}
#else
bool walkerDirectLockDue(void){return false;}
void walkerDirectLockWrite(void){}
#endif
