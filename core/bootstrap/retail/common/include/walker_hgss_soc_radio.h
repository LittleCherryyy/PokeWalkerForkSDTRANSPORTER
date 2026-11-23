/* HGSS native Nitro SOC adapter for an in-game Android Pokewalker checkout.
 * Copyright (C) 2026 PokeWalker Virtual contributors.
 * GPL-3.0-or-later.
 *
 * This describes the actual (NOT BSD!) Nintendo SOC ABI, as observed in
 * original HGSS's ov39_02229AD4 / ov39_02229BE4 and NitroDWC overlay 0:
 *   SOC_Socket(2,1,0);
 *   SOC_Fcntl(fd,3,0), SOC_Fcntl(fd,4,flags|4);
 *   SOC_Connect(fd,&SOCSockAddrIn);     // two args, not three
 *   SOC_Send / SOC_Recv(fd,buf,len,flags);
 *
 * No function pointers are supplied here. They must be independently
 * resolved and their game ROM revision, overlay lifetime, and ABI proved.
 * This header and its host tests do not initialize the actual DSi radio.
 */
#ifndef WALKER_HGSS_SOC_RADIO_H
#define WALKER_HGSS_SOC_RADIO_H
#include <stdint.h>
#include "walker_direct_radio.h"

#define WALKER_HGSS_SOC_BIND_MAGIC 0x31574E50u /* 'PNW1' */
#define WALKER_HGSS_SOC_BIND_VERSION 1u
#define WALKER_HGSS_SOC_OV0_START 0x021E5900u
#define WALKER_HGSS_SOC_OV0_END   0x0221BA00u

/* Nitro's IPv4 sockaddr is length, family, port (network order),
 * address (network order): exactly 8 bytes; not glibc sockaddr_in. */
typedef struct WalkerHgssSocAddress {
    uint8_t length;
    uint8_t family;
    uint8_t portBE[2];
    uint8_t ip[4];
} WalkerHgssSocAddress;
typedef char walker_hgss_sockaddr_size[
    sizeof(WalkerHgssSocAddress)==8 ? 1:-1
];

/* From pret/pokeheartgold/src/poke_overlay.c: static
 * PMiLoadedOverlay sOverlayRegions[3][8], {FSOverlayID, BOOL active}.
 * This is the GAME'S own overlay-manager state, not a reconstructed
 * memory-signature or a guess based on bytes left after unloading. */
typedef struct WalkerHgssOverlaySlot {
    uint32_t id;
    uint32_t active;
} WalkerHgssOverlaySlot;
#define WALKER_HGSS_OVERLAY_SLOTS 24u
typedef char walker_hgss_overlay_slot_size[
    sizeof(WalkerHgssOverlaySlot)==8 ? 1:-1
];

typedef struct WalkerHgssSocBindings {
    uint32_t magic;
    uint32_t version;
    /* Exact observed active ROM overlay-0 image bounds. */
    uint32_t overlayStart;
    uint32_t overlayEnd;
    /* 1 only AFTER verified Pokewalker overlay-112 unload, game-native
     * overlay-0 load, WCM + SOC startup and ARM7 Wi-Fi initialization.
     * These are asserted by independently verified game lifecycle hooks;
     * a game title code or static overlay table alone is NOT evidence. */
    uint32_t pokewalkerUnloaded;
    uint32_t networkingLoaded;
    uint32_t socStarted;
    uint32_t arm7WifiReady;
    /* Must refer to the actual 3*8-slot game overlay manager table after
     * a ROM-specific verified lookup. Re-checked before every socket call:
     * ov0 active, ov112 inactive. Never derive this from stale RAM code. */
    const WalkerHgssOverlaySlot *gameOverlaySlots;
    /* Phone hotspot gateway address in NETWORK BYTE ORDER.
     * Must come from the game's live DHCP state, not a fixed 192.168.x.x. */
    uint8_t gateway[4];
    int (*socSocket)(int domain,int type,int protocol);
    int (*socFcntl)(int fd,int command,int arg);
    int (*socConnect)(int fd,const WalkerHgssSocAddress *address);
    int (*socSend)(int fd,const void *data,int length,int flags);
    int (*socRecv)(int fd,void *data,int length,int flags);
    int (*socShutdown)(int fd,int how);
    int (*socClose)(int fd);
    /* Must return 1 only while same overlay generation and DHCP
     * association remain live. Checked before EVERY native SOC call. */
    int (*stillReady)(void);
} WalkerHgssSocBindings;

/* The loader/overlay lifecycle service is not yet implemented. Until it
 * calls this with verified ROM-specific runtime evidence, the native
 * backend is absent and no socket call is attempted. */
int walkerHgssSocBind(const WalkerHgssSocBindings *api);
void walkerHgssSocInvalidate(void);
const WalkerDirectRadioOps *walkerHgssSocRadioOps(void);
#endif
