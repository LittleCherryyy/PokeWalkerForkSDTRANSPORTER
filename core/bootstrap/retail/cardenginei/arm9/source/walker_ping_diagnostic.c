/* Experimental V7.1 resident ARM9 PING-only framing interface.
 * No network access, ROM changes, clock/interrupt changes or save I/O.
 * This unit is deliberately independent of the higher-risk ARM7 bridge.
 * GPL-3.0-or-later; preserve attribution to Shinygati and all upstream work.
 */
#include "walker_ping_only.h"

/* Returns number of bytes for the caller to transmit only after a vetted,
 * non-blocking resident network backend is linked and checked on hardware.
 * Never emits a data-transfer opcode or accesses the walker EEPROM. */
unsigned walkerV71MakePing(void *output, unsigned output_capacity) {
    if (!output || output_capacity < WALKER_DIRECT_HEADER_SIZE) return 0;
    walkerPingBuild((WalkerDirectHeader *)output);
    return WALKER_DIRECT_HEADER_SIZE;
}

/* Called only after the backend has received exactly frame_bytes.
 * Reject all non-PING acknowledgements, truncation and added payloads. */
int walkerV71CheckPingOk(const void *frame, unsigned frame_bytes) {
    if (!frame || frame_bytes != WALKER_DIRECT_HEADER_SIZE) return 0;
    return walkerPingAcceptOk((const WalkerDirectHeader *)frame);
}
