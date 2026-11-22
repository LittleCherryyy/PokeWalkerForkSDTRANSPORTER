#ifndef WALKER_DIRECT_BRIDGE_API_H
#define WALKER_DIRECT_BRIDGE_API_H
#include <nds/ndstypes.h>
#include "walker_emu.h"
void walkerDirectBridgeInit(WalkerControl *c);
void walkerDirectBridgeCommitted(WalkerControl *c,u32 seq);
void walkerDirectBridgeTick(void);
void walkerDirectBridgeRequestPull(void);
#endif
