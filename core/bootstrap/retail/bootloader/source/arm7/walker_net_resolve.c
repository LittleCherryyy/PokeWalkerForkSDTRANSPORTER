/* The WCM/SOCL resolver only belongs to DSi's NTR bootstrap path.
 * B4DS cardengines have smaller linker regions and no resident DSi Wi-Fi
 * transport. Exclude this unused code from B4DS without affecting NTR.
 */
#ifndef B4DS
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

#endif /* !B4DS */
