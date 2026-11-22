/* The WCM/SOCL resolver only belongs to DSi's NTR bootstrap path.
 * B4DS cardengines have smaller linker regions and no resident DSi Wi-Fi
 * transport. Exclude this unused code from B4DS without affecting NTR.
 */
#ifndef B4DS
/* HGSS resident network resolver (V7.1, fail-closed). GPL-3.0-or-later.
 *
 * A title code or known RAM address is NOT a callable Wi-Fi API. Until an
 * exact binary signature and ABI are independently validated, function
 * pointers remain zero and networking stays disabled.
 */
#include <string.h>
#include "walker_hgss_net.h"

int walkerResolveHgssNet(const u32 *arm9, u32 base, u32 bytes,
                         WalkerHgssNetApi *out, const char gameCode[4]) {
    if (!out) return 0;
    /* Reset even on malformed inputs; never leak a stale ready=1 state. */
    memset(out, 0, sizeof(*out));
    out->magic = WALKER_HGSS_NET_MAGIC;
    if (!arm9 || bytes < 0x1000u || (bytes & 3u) || (base & 3u)) return 0;

    /* Address from the matching US HGSS decomp is only a candidate global.
     * This DOES NOT imply an associated Wi-Fi network or an available socket.
     * Never treat the game code alone as proof of a matching binary revision. */
    if (gameCode &&
        gameCode[0] == 'I' && gameCode[1] == 'P' &&
        (gameCode[2] == 'K' || gameCode[2] == 'G') &&
        gameCode[3] == 'E') {
        out->soclGatewayPtr = 0x021D464Cu;
    }

    /* Required callable WCM/SOCL/SOC functions remain unresolved by design.
     * No heuristic/guessed jump target is considered safe enough to call. */
    out->ready = walkerHgssNetMissingMask(out) == 0u;
    return 1;
}

#endif /* !B4DS */
