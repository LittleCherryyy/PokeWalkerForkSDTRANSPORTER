/* Portable ABI/lifecycle regression for original HGSS post-Pokewalker
 * game-managed overlay-0 load. Synthetic overlay slots, NO ROM/save.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "walker_hgss_postexit.h"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL: %s line %d\n",#x,__LINE__);return 1;}}while(0)
static WalkerHgssOverlaySlot slots[WALKER_HGSS_OVERLAY_SLOTS];
static int mainThreadSafe=0;
static int checkoutDurable=0;
static int shouldFailLoad=0;
static unsigned calls=0;
static int safeCallback(void){return mainThreadSafe;}
static int checkoutCallback(void){return checkoutDurable;}
static int loadCallback(uint32_t id,uint32_t how){
    calls++;
    if(id!=0 || how!=2 || !mainThreadSafe || shouldFailLoad)return 0;
    slots[0].id=0;slots[0].active=1;
    return 1;
}
int main(void){
    WalkerHgssPostExit req;
    memset(&req,0,sizeof(req));
    req.magic=WALKER_POSTEXIT_MAGIC;
    req.version=WALKER_POSTEXIT_REV;
    req.gameOverlaySlots=slots;
    req.safeMainThreadAfterExit=safeCallback;
    req.verifiedCheckoutPending=checkoutCallback;
    req.handleLoadOverlay=loadCallback;
    CHECK(walkerHgssPostExitPrepare(NULL)==-1);
    req.magic=0;CHECK(walkerHgssPostExitPrepare(&req)==-1);
    req.magic=WALKER_POSTEXIT_MAGIC;
    CHECK(walkerHgssPostExitPrepare(&req)==0); /* wrong scheduler */
    CHECK(calls==0);
    mainThreadSafe=1;
    CHECK(walkerHgssPostExitPrepare(&req)==0); /* not checked out */
    CHECK(calls==0);
    checkoutDurable=1;
    slots[1].id=112;slots[1].active=1;
    CHECK(walkerHgssPostExitPrepare(&req)==0); /* IR still loaded */
    CHECK(calls==0);
    slots[1].active=0;
    shouldFailLoad=1;
    CHECK(walkerHgssPostExitPrepare(&req)==0); /* game denies */
    CHECK(calls==1 && !slots[0].active);
    shouldFailLoad=0;
    CHECK(walkerHgssPostExitPrepare(&req)==1);
    CHECK(calls==2 && slots[0].id==0 && slots[0].active==1);
    CHECK(walkerHgssPostExitPrepare(&req)==1); /* reuse only */
    CHECK(calls==2);
    slots[1].active=1;
    CHECK(walkerHgssPostExitPrepare(&req)==0); /* corrupted lifetime */
    CHECK(calls==2);
    slots[1].active=0;
    slots[2].id=0;slots[2].active=1;
    CHECK(walkerHgssPostExitPrepare(&req)==-1); /* duplicate registration */
    slots[2].active=0;
    slots[1].active=5;
    CHECK(walkerHgssPostExitPrepare(&req)==-1); /* malformed active field */
    slots[1].active=0;
    mainThreadSafe=0;
    CHECK(walkerHgssPostExitPrepare(&req)==0);
    CHECK(calls==2);
    puts("PASS: post-IR game-managed overlay0 load only in verified normal main frame");
    puts("LIMIT: overlay manager callback simulated; no live HGSS app hook yet");
    return 0;
}
