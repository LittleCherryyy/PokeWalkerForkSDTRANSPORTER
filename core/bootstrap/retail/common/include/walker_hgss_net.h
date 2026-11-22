#ifndef WALKER_HGSS_NET_H
#define WALKER_HGSS_NET_H
#include <nds/ndstypes.h>
#define WALKER_HGSS_NET_MAGIC 0x324E5748u /* HWN2 */
typedef struct WalkerHgssNetApi {
    u32 magic;
    u32 ready;
    u32 wcmInit;
    u32 wcmStartupAsync;
    u32 wcmBeginSearchAsync;
    u32 wcmEndSearchAsync;
    u32 wcmConnectAsync;
    u32 wcmDisconnectAsync;
    u32 wcmCleanupAsync;
    u32 wcmGetPhase;
    u32 wcmCountApList;
    u32 wcmPointApList;
    u32 soclStartup;
    u32 socSocket;
    u32 socConnect;
    u32 socRecv;
    u32 socSend;
    u32 socClose;
    u32 socFcntl;
    u32 soclGatewayPtr;
} WalkerHgssNetApi;
/* V7.1 diagnostic mask: bit set means the corresponding entry is missing.
 * Do not change WalkerHgssNetApi layout: it is shared across cardengine CPUs.
 * A populated address alone does NOT prove ABI or runtime safety. */
enum {
    WALKER_NET_MISS_WCM_INIT = 1u << 0,
    WALKER_NET_MISS_WCM_START = 1u << 1,
    WALKER_NET_MISS_WCM_SEARCH = 1u << 2,
    WALKER_NET_MISS_WCM_CONNECT = 1u << 3,
    WALKER_NET_MISS_WCM_PHASE = 1u << 4,
    WALKER_NET_MISS_WCM_AP_LIST = 1u << 5,
    WALKER_NET_MISS_SOCL_START = 1u << 6,
    WALKER_NET_MISS_SOC_SOCKET = 1u << 7,
    WALKER_NET_MISS_SOC_CONNECT = 1u << 8,
    WALKER_NET_MISS_SOC_RECV = 1u << 9,
    WALKER_NET_MISS_SOC_SEND = 1u << 10,
    WALKER_NET_MISS_SOC_CLOSE = 1u << 11,
    WALKER_NET_MISS_GATEWAY = 1u << 12
};
static inline u32 walkerHgssNetMissingMask(const WalkerHgssNetApi *n) {
    if (!n || n->magic != WALKER_HGSS_NET_MAGIC) return (1u << 13) - 1u;
    return (!n->wcmInit ? WALKER_NET_MISS_WCM_INIT : 0u)
        | (!n->wcmStartupAsync ? WALKER_NET_MISS_WCM_START : 0u)
        | (!n->wcmBeginSearchAsync ? WALKER_NET_MISS_WCM_SEARCH : 0u)
        | (!n->wcmConnectAsync ? WALKER_NET_MISS_WCM_CONNECT : 0u)
        | (!n->wcmGetPhase ? WALKER_NET_MISS_WCM_PHASE : 0u)
        | (!n->wcmPointApList ? WALKER_NET_MISS_WCM_AP_LIST : 0u)
        | (!n->soclStartup ? WALKER_NET_MISS_SOCL_START : 0u)
        | (!n->socSocket ? WALKER_NET_MISS_SOC_SOCKET : 0u)
        | (!n->socConnect ? WALKER_NET_MISS_SOC_CONNECT : 0u)
        | (!n->socRecv ? WALKER_NET_MISS_SOC_RECV : 0u)
        | (!n->socSend ? WALKER_NET_MISS_SOC_SEND : 0u)
        | (!n->socClose ? WALKER_NET_MISS_SOC_CLOSE : 0u)
        | (!n->soclGatewayPtr ? WALKER_NET_MISS_GATEWAY : 0u);
}
static inline u32 walkerArmBlTarget(u32 pc,u32 insn){s32 off=(s32)(insn<<8)>>6;return pc+8+(u32)off;}
static inline int walkerArmIsBl(u32 insn){return (insn&0x0f000000u)==0x0b000000u;}
int walkerResolveHgssNet(const u32 *arm9,u32 arm9Address,u32 arm9Bytes,WalkerHgssNetApi *out,const char gameCode[4]);
#endif
