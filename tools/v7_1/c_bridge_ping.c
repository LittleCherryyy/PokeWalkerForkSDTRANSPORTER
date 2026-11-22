/* Synthetic PING frame built with nds-bootstrap's shared C wire header.
 * Native-host test only; GPL-3.0-or-later (derived from SD Transporter).
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "../../core/bootstrap/retail/common/include/walker_ping_only.h"

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    WalkerDirectHeader ping;
    walkerPingBuild(&ping);
    if (sizeof(ping) != 88 || WALKER_DIRECT_PORT != 30821 ||
        walkerDirectBe16(ping.flagsBE) != 0 ||
        walkerDirectBe32(ping.payloadLengthBE) != 0 ||
        walkerDirectBe32(ping.crc32BE) != 0) return 3;
    WalkerDirectHeader ok = ping;
    ok.op = WALKER_DIRECT_OK;
    if (!walkerPingAcceptOk(&ok)) return 7;
    ok.crc32BE[3] = 1;
    if (walkerPingAcceptOk(&ok)) return 8;
    ok.crc32BE[3] = 0;
    ok.op = WALKER_DIRECT_PUSH_TO_PHONE;
    if (walkerPingAcceptOk(&ok)) return 9;
    ok.op = WALKER_DIRECT_OK;
    ok.session[0] = '1';
    if (walkerPingAcceptOk(&ok)) return 10;
    FILE *output=fopen(argv[1], "wb");
    if (!output) return 4;
    int written = fwrite(&ping, 1, sizeof(ping), output)==sizeof(ping);
    if (fclose(output)) return 5;
    return written ? 0 : 6;
}
