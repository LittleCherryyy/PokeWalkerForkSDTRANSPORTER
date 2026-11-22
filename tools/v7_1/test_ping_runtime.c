/* Host fixture executes exactly the PING framing code linked to the
 * experimental DSi ARM9 cardengine. No network or save is involved. */
#include <stdio.h>
#include <string.h>
#include "walker_directsync.h"
#include "walker_ping_runtime.h"

int main(void) {
    WalkerDirectHeader h, response;
    unsigned char short_out[WALKER_DIRECT_HEADER_SIZE];
    memset(short_out, 0xA5, sizeof(short_out));

    if (walkerV71MakePing(0, WALKER_DIRECT_HEADER_SIZE) != 0) return 1;
    if (walkerV71MakePing(short_out, WALKER_DIRECT_HEADER_SIZE - 1) != 0) return 2;
    for (unsigned i = 0; i < sizeof(short_out); ++i)
        if (short_out[i] != 0xA5) return 3;

    if (walkerV71MakePing(&h, sizeof(h)) != WALKER_DIRECT_HEADER_SIZE) return 4;
    if (memcmp(h.magic, WALKER_DIRECT_MAGIC, WALKER_DIRECT_MAGIC_SIZE)) return 5;
    if (h.op != WALKER_DIRECT_PING || h.version != WALKER_DIRECT_VERSION) return 6;
    response = h;
    response.op = WALKER_DIRECT_OK;
    if (!walkerV71CheckPingOk(&response, sizeof(response))) return 7;

    if (walkerV71CheckPingOk(&response, sizeof(response) - 1)) return 8;
    if (walkerV71CheckPingOk(&response, sizeof(response) + 1)) return 9;
    if (walkerV71CheckPingOk(0, sizeof(response))) return 10;
    response.crc32BE[3] = 1;
    if (walkerV71CheckPingOk(&response, sizeof(response))) return 11;
    response.crc32BE[3] = 0;
    response.op = WALKER_DIRECT_PUSH_TO_PHONE;
    if (walkerV71CheckPingOk(&response, sizeof(response))) return 12;
    response.op = WALKER_DIRECT_OK;
    response.session[0] = '1';
    if (walkerV71CheckPingOk(&response, sizeof(response))) return 13;
    response.session[0] = 0;
    response.trainer[0] = '1';
    if (walkerV71CheckPingOk(&response, sizeof(response))) return 14;

    puts("PASS: DSi ARM9 PING-only runtime framing rejects save operations and malformed responses.");
    return 0;
}
