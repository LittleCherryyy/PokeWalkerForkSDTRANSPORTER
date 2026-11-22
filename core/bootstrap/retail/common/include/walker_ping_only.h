/* V7.1 diagnostic-only PING framing for Android Direct DSi Sync.
 * No sockets, Wi-Fi initialization, save or ROM access.
 * Derived from the GPL-3.0-or-later SD-Transporter fork; retain upstream
 * developer attribution in ATTRIBUTION.md and CREDITS-UPSTREAM.md.
 */
#ifndef WALKER_PING_ONLY_H
#define WALKER_PING_ONLY_H

#include "walker_directsync.h"

/* No libc calls: safe for ARM7, ARM9, and portable host fixtures.
 * Every byte is initialized to avoid revealing RAM through the network. */
static inline void walkerPingBuild(WalkerDirectHeader *h) {
    unsigned char *p = (unsigned char *)h;
    unsigned i;
    if (!h) return;
    for (i = 0; i < WALKER_DIRECT_HEADER_SIZE; ++i) p[i] = 0;
    for (i = 0; i < WALKER_DIRECT_MAGIC_SIZE; ++i)
        h->magic[i] = (unsigned char)WALKER_DIRECT_MAGIC[i];
    h->version = WALKER_DIRECT_VERSION;
    h->op = WALKER_DIRECT_PING;
}

/* Response must be exactly the 88-byte header and carry no save payload.
 * PING/OK is the only operation accepted by this stage of the integration.
 * The stream reader is responsible for enforcing exactly 88 bytes received.
 * This routine does not attempt to parse or trust packets of other lengths. */
static inline int walkerPingAcceptOk(const WalkerDirectHeader *h) {
    unsigned i;
    if (!h || h->version != WALKER_DIRECT_VERSION ||
        h->op != WALKER_DIRECT_OK ||
        walkerDirectBe16(h->flagsBE) != 0 ||
        walkerDirectBe32(h->payloadLengthBE) != 0 ||
        walkerDirectBe32(h->crc32BE) != 0) return 0;
    for (i = 0; i < WALKER_DIRECT_MAGIC_SIZE; ++i)
        if (h->magic[i] != (unsigned char)WALKER_DIRECT_MAGIC[i]) return 0;
    for (i = 0; i < WALKER_DIRECT_SESSION_SIZE; ++i)
        if (h->session[i] != 0) return 0;
    for (i = 0; i < WALKER_DIRECT_TRAINER_SIZE; ++i)
        if (h->trainer[i] != 0) return 0;
    return 1;
}

#endif
