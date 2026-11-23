#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "walker_hgss_net.h"
int main(void) {
    static u32 arm9[1024];
    WalkerHgssNetApi n;
    const char hg[4]={'I','P','K','E'};
    const char ss[4]={'I','P','G','E'};
    const char bad[4]={'A','B','C','E'};
    assert(walkerResolveHgssNet(arm9,0x02000000u,sizeof(arm9),&n,hg)==1);
    assert(n.magic==WALKER_HGSS_NET_MAGIC && n.ready==0);
    assert(n.soclGatewayPtr==0x021D464Cu && n.socConnect==0);
    assert(walkerResolveHgssNet(arm9,0x02000000u,sizeof(arm9),&n,ss)==1);
    assert(n.soclGatewayPtr==0x021D464Cu && n.ready==0);
    assert(walkerResolveHgssNet(arm9,0x02000000u,sizeof(arm9),&n,bad)==1);
    assert(n.soclGatewayPtr==0 && n.ready==0);
    assert(walkerResolveHgssNet(arm9,0x02000000u,12,&n,hg)==0);
    assert(n.ready==0 && n.soclGatewayPtr==0);
    assert(walkerResolveHgssNet(arm9,0xfffff000u,sizeof(arm9),&n,hg)==1);
    assert(walkerResolveHgssNet(arm9,0xfffff001u,sizeof(arm9),&n,hg)==0);
    assert(walkerResolveHgssNet(arm9,0xfffffffcu,sizeof(arm9),&n,hg)==0);
    assert(walkerResolveHgssNet(0,0x02000000u,sizeof(arm9),&n,hg)==0);
    assert(walkerResolveHgssNet(arm9,0x02000000u,sizeof(arm9),0,hg)==0);
    return 0;
}
