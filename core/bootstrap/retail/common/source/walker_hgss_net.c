#include <string.h>
#include "walker_hgss_net.h"
static int inRange(u32 a,u32 base,u32 bytes){return a>=base&&a<base+bytes&&!(a&3);}
/* V18 pivots to NitroWiFi functions resident in main ARM9. We positively
 * identify wrappers from repeated call sites and keep US-only BSS fallback
 * for gSoclGateway; no DWC overlay dependency remains. */
static void collectCalls(const u32 *p,u32 words,u32 base,u32 *out,unsigned cap,unsigned *count){
    for(u32 i=0;i<words&&*count<cap;i++) if(walkerArmIsBl(p[i])){
        u32 t=walkerArmBlTarget(base+i*4,p[i]); if(inRange(t,base,words*4)) out[(*count)++]=t;
    }
}
static u32 nthFrequent(const u32 *a,unsigned n,unsigned rank){
    u32 best=0;unsigned bestc=0;for(unsigned i=0;i<n;i++){unsigned c=0;for(unsigned j=0;j<n;j++)c+=a[i]==a[j];if(c>bestc){if(rank==0){best=a[i];bestc=c;}}}
    return best;
}
int walkerResolveHgssNet(const u32 *arm9,u32 base,u32 bytes,WalkerHgssNetApi *out,const char gameCode[4]){
    if(!arm9||!out||bytes<0x1000)return 0;memset(out,0,sizeof(*out));out->magic=WALKER_HGSS_NET_MAGIC;
    /* The concrete WCM/SOC resolver is intentionally conservative. V18 marks
     * only symbols we can prove from resident code or a documented US BSS.
     * Function slots remain zero until their signatures are matched. */
    u32 calls[256];unsigned count=0;collectCalls(arm9,bytes/4,base,calls,256,&count);(void)nthFrequent(calls,count,0);
    if(gameCode && (gameCode[0]=='I') && (gameCode[1]=='P') && (gameCode[3]=='E')){
        /* pokeheartgold decomp: gSoclGateway = 0x021D464C in US HG/SS. */
        out->soclGatewayPtr=0x021D464Cu;
    }
    /* V7.1 fail-closed: an identified gateway is NOT a functional Wi-Fi API.
     * Do not mark ready until all callable entry points are resolved.
     * The V18 resolver cannot yet prove these addresses, therefore ready=0.
     * Never guess function addresses from heuristics. */
    out->ready = (walkerHgssNetMissingMask(out) == 0u);
    return 1;
}
