/* Experimental HGSS Wi-Fi resolver: fail closed until vetted symbols exist.
 * Based on SD Transporter and nds-bootstrap; preserve upstream attribution.
 *
 * A frequent ARM BL target is not proof of a WCM/SOCL function. Some WCM
 * references in the public HGSS decompilation also occur in overlays; their
 * symbols must never be treated as always-resident addresses without an
 * independent proof for the exact game revision and runtime state.
 *
 * This implementation deliberately does NOT return callable addresses,
 * initialize Nintendo Wi-Fi, open sockets, or modify any save data.
 */
#if !defined(B4DS)
#include <string.h>
#include "walker_hgss_net.h"

int walkerResolveHgssNet(const u32 *arm9, u32 base, u32 bytes,
                         WalkerHgssNetApi *out, const char gameCode[4]) {
    (void)base;
    if (!out) return 0;
    memset(out, 0, sizeof(*out));

    /* Only recognize enough information for conservative diagnostics.
     * A valid HGSS game code still does not establish exact revision,
     * decompression state, linked library identity, or overlay residency. */
    if (!arm9 || bytes < 0x1000 || !gameCode) return 0;
    if (gameCode[0] != 'I' || gameCode[1] != 'P' ||
        (gameCode[2] != 'K' && gameCode[2] != 'G')) return 0;

    out->magic = WALKER_HGSS_NET_MAGIC;
    /* Never infer gSoclGateway from game code alone. Previously an
     * unverified US-specific address was published on this path.
     * WCM/SOCL pointers intentionally remain zero until a reviewed
     * revision-specific resolver is introduced with independent tests. */
    out->ready = 0;
    return 1;
}
#endif /* !B4DS */
