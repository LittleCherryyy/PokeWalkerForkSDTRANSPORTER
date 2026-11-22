/* Resolve the resident HGSS Wi-Fi API into WalkerControl. GPL-3.0-or-later. */
#include <nds/ndstypes.h>
#include <string.h>
#include "nds_header.h"
#include "walker_emu.h"
#include "walker_hgss_net.h"

void walkerResolveNetworkApi(WalkerControl *c,const tNDSHeader *h){
    if(!c||!h)return;
    memset(&c->hgssNet,0,sizeof(c->hgssNet));
    walkerResolveHgssNet((const u32 *)h->arm9destination,h->arm9destination,h->arm9binarySize,&c->hgssNet,(const char *)h->gameCode);
}
