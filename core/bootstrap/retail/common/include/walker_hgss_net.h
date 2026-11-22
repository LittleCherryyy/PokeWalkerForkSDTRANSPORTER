#ifndef WALKER_HGSS_NET_H
#define WALKER_HGSS_NET_H
#include <nds/ndstypes.h>
#include "walker_emu.h"
#define WALKER_HGSS_NET_MAGIC 0x324E5748u /* HWN2 */

static inline u32 walkerArmBlTarget(u32 pc,u32 insn){s32 off=(s32)(insn<<8)>>6;return pc+8+(u32)off;}
static inline int walkerArmIsBl(u32 insn){return (insn&0x0f000000u)==0x0b000000u;}
int walkerResolveHgssNet(const u32 *arm9,u32 arm9Address,u32 arm9Bytes,WalkerHgssNetApi *out,const char gameCode[4]);
#endif
