/* Resolve the resident HGSS Wi-Fi API into WalkerControl. GPL-3.0-or-later. */
#include <nds/ndstypes.h>
#include <string.h>
#include "nds_header.h"
#include "walker_emu.h"
#include "walker_hgss_net.h"

extern u32 iUncompressedSize;

void walkerResolveNetworkApi(WalkerControl *c,const tNDSHeader *h){
    if(!c||!h)return;
    memset(&c->hgssNet,0,sizeof(c->hgssNet));
    /* Scan the decompressed resident image (the same bytes the IR hook sees)
     * only when its range is fully within main DS RAM. Never scan beyond RAM.
     * The resolver is fail-closed and does not call any found functions. */
    const u32 base=(u32)h->arm9destination;
    const u32 bytes=(iUncompressedSize>h->arm9binarySize) ?
        iUncompressedSize : h->arm9binarySize;
    if(base<0x02000000u || base>=0x02400000u ||
       bytes<0x1000u || bytes>0x02400000u-base) return;
    walkerResolveHgssNet((const u32 *)base,base,bytes,
                         &c->hgssNet,(const char *)h->gameCode);
}
