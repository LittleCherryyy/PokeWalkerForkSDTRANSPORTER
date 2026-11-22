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
static inline u32 walkerArmBlTarget(u32 pc,u32 insn){s32 off=(s32)(insn<<8)>>6;return pc+8+(u32)off;}
static inline int walkerArmIsBl(u32 insn){return (insn&0x0f000000u)==0x0b000000u;}
int walkerResolveHgssNet(const u32 *arm9,u32 arm9Address,u32 arm9Bytes,WalkerHgssNetApi *out,const char gameCode[4]);
#endif
