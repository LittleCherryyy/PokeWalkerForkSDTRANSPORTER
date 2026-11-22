/* Synthetic PING frame built with nds-bootstrap's shared C wire header.
 * Native-host test only; GPL-3.0-or-later (derived from SD Transporter).
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "../../core/bootstrap/retail/common/include/walker_directsync.h"

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    WalkerDirectHeader ping;
    memset(&ping, 0, sizeof(ping));
    memcpy(ping.magic, WALKER_DIRECT_MAGIC, WALKER_DIRECT_MAGIC_SIZE);
    ping.version = WALKER_DIRECT_VERSION;
    ping.op = WALKER_DIRECT_PING;
    walkerDirectPut16(ping.flagsBE, 0);
    walkerDirectPut32(ping.payloadLengthBE, 0);
    walkerDirectPut32(ping.crc32BE, 0);
    if (sizeof(ping) != 88 || WALKER_DIRECT_PORT != 30821 ||
        walkerDirectBe16(ping.flagsBE) != 0 ||
        walkerDirectBe32(ping.payloadLengthBE) != 0 ||
        walkerDirectBe32(ping.crc32BE) != 0) return 3;
    FILE *output=fopen(argv[1], "wb");
    if (!output) return 4;
    int written = fwrite(&ping, 1, sizeof(ping), output)==sizeof(ping);
    if (fclose(output)) return 5;
    return written ? 0 : 6;
}
