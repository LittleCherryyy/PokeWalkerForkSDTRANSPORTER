#ifndef WALKER_HGSS_NET_H
#define WALKER_HGSS_NET_H
/* Shared by the regular ARM7/ARM9 cardengines and the freestanding
 * position-independent Pokéwalker ARM9 blob. Do not include libnds:
 * the blob is compiled without SDK headers and must stay portable. */
#include <stdint.h>
#define WALKER_HGSS_NET_MAGIC 0x324E5748u /* HWN2 */
typedef struct WalkerHgssNetApi {
    uint32_t magic;
    uint32_t ready;
    uint32_t wcmInit;
    uint32_t wcmStartupAsync;
    uint32_t wcmBeginSearchAsync;
    uint32_t wcmEndSearchAsync;
    uint32_t wcmConnectAsync;
    uint32_t wcmDisconnectAsync;
    uint32_t wcmCleanupAsync;
    uint32_t wcmGetPhase;
    uint32_t wcmCountApList;
    uint32_t wcmPointApList;
    uint32_t soclStartup;
    uint32_t socSocket;
    uint32_t socConnect;
    uint32_t socRecv;
    uint32_t socSend;
    uint32_t socClose;
    uint32_t socFcntl;
    uint32_t soclGatewayPtr;
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
static inline uint32_t walkerHgssNetMissingMask(const WalkerHgssNetApi *n) {
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
static inline uint32_t walkerArmBlTarget(uint32_t pc,uint32_t insn){int32_t off=(int32_t)(insn<<8)>>6;return pc+8+(uint32_t)off;}
static inline int walkerArmIsBl(uint32_t insn){return (insn&0x0f000000u)==0x0b000000u;}
int walkerResolveHgssNet(const uint32_t *arm9,uint32_t arm9Address,uint32_t arm9Bytes,WalkerHgssNetApi *out,const char gameCode[4]);
#endif
