#include <nds.h>
#include <string.h>
#include "walker_emu.h"
#include "walker_directsync.h"
#include "walker_hgss_net.h"
#include "cardengine_header_arm9.h"
extern cardengineArm9 *ce9;
#define WCM_PHASE_DCF 9
#define DIRECT_PORT 30821
#define NET_IDLE 0
#define NET_WAIT_API 1
#define NET_SEARCH 2
#define NET_CONNECT 3
#define NET_TCP 4
#define NET_PUSH 5
#define NET_PULL 6
#define NET_ERROR 7
static u32 netState;
static WalkerControl *control(void){WalkerControl*c=(WalkerControl*)ce9->walkerControl;return c&&c->magic==WALKER_MAGIC&&c->version==WALKER_VERSION?c:0;}
static void buildHeader(WalkerDirectHeader*h,u8 op,const WalkerControl*c,u32 length,u32 crc){memset(h,0,sizeof(*h));memcpy(h->magic,WALKER_DIRECT_MAGIC,WALKER_DIRECT_MAGIC_SIZE);h->version=WALKER_DIRECT_VERSION;h->op=op;walkerDirectPut16(h->flagsBE,0);walkerDirectPut32(h->payloadLengthBE,length);walkerDirectPut32(h->crc32BE,crc);memcpy(h->session,c->direct.session,WALKER_DIRECT_SESSION_SIZE);memcpy(h->trainer,c->direct.trainer,WALKER_DIRECT_TRAINER_SIZE);}
static int apiComplete(const WalkerHgssNetApi*n){return walkerHgssNetMissingMask(n)==0u && n->ready;}
void walkerDirectTransportTickArm9(void){
    WalkerControl*c=control();if(!c||c->direct.magic!=WALKER_DIRECT_BRIDGE_MAGIC)return;WalkerHgssNetApi*n=&c->hgssNet;
    if(n->magic!=WALKER_HGSS_NET_MAGIC){netState=NET_WAIT_API;return;}
    /* V18: architecture is now WCM + SOCL, resident in main ARM9. The runtime
     * refuses to call any network function until every resolver slot is proven. */
    if(!apiComplete(n)){netState=NET_WAIT_API;return;}
    if(c->direct.state==WALKER_DIRECT_PUSH_READY&&netState==NET_IDLE)netState=NET_SEARCH;
    /* Actual calls are intentionally gated for the next pass; this prevents
     * a partially resolved API from corrupting HGSS. */
}
void walkerDirectBuildPushHeader(void*dst){WalkerControl*c=control();if(c)buildHeader((WalkerDirectHeader*)dst,WALKER_DIRECT_PUSH_TO_PHONE,c,WALKER_DIRECT_WALKER_SIZE,c->direct.crc32);}
