/* Diagnostic-only ARM compile check for shared PING encoding.
 * This is not linked into game yet; it has no Wi-Fi or save dependencies. */
#include "walker_ping_only.h"

unsigned walkerV71PingOnlySelfCheck(void) {
    WalkerDirectHeader ping;
    WalkerDirectHeader response;
    unsigned i;
    walkerPingBuild(&ping);
    response = ping;
    response.op = WALKER_DIRECT_OK;
    if (!walkerPingAcceptOk(&response)) return 0;
    response.op = WALKER_DIRECT_PUSH_TO_PHONE;
    if (walkerPingAcceptOk(&response)) return 0;
    response.op = WALKER_DIRECT_OK;
    for (i = 0; i < WALKER_DIRECT_HEADER_SIZE; ++i) {
        if (((unsigned char *)&ping)[i] !=
             ((i < 8) ? (unsigned char)WALKER_DIRECT_MAGIC[i] :
             (i == 8 ? WALKER_DIRECT_VERSION :
             (i == 9 ? WALKER_DIRECT_PING : 0)))) return 0;
    }
    return 1;
}
