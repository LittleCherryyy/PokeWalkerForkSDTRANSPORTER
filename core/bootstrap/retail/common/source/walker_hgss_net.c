#include <string.h>
#include "walker_hgss_net.h"

/* Resident HGSS networking is a candidate backend, not a proven API.
 * Never infer callable addresses from BL frequency or overlay-relative offsets.
 * This resolver intentionally fails closed until verified ABI bindings exist. */
static int walkerIsUsHgss(const char gameCode[4]) {
    if (!gameCode) return 0;
    return gameCode[0] == 'I' && gameCode[1] == 'P' &&
           (gameCode[2] == 'K' || gameCode[2] == 'G') &&
           gameCode[3] == 'E';
}

int walkerResolveHgssNet(const u32 *arm9, u32 base, u32 bytes,
                         WalkerHgssNetApi *out, const char gameCode[4]) {
    if (!out) return 0;
    memset(out, 0, sizeof(*out));
    out->magic = WALKER_HGSS_NET_MAGIC;
    /* Refuse malformed images and addresses; never read an unverified ROM buffer. */
    if (!arm9 || bytes < 0x1000u || (bytes & 3u) || (base & 3u) ||
        base > 0xffffffffu - bytes) return 0;

    /* The US HGSS gateway candidate is a data pointer only, NOT proof
     * that WCM, SOC, DHCP, or TCP is initialized or resident. */
    if (walkerIsUsHgss(gameCode))
        out->soclGatewayPtr = 0x021D464Cu;

    /* No callable symbols have yet been established from a verified
     * revision-specific map. The caller must not initiate networking. */
    out->ready = 0;
    return 1;
}
