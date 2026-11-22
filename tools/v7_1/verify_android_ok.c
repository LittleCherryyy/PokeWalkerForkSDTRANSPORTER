/* Validate a real Android V18 Java OP_OK file with the same decoder used
 * by the experimental DSi PING path. No network, ROM, save or file writes.
 * GPL-3.0-or-later; preserve upstream SD Transporter attribution.
 */
#include <stdio.h>
#include "walker_ping_only.h"

int main(int argc, char **argv) {
    unsigned char bytes[WALKER_DIRECT_HEADER_SIZE];
    FILE *f;
    size_t n;
    if (argc != 2) return 2;
    f = fopen(argv[1], "rb");
    if (!f) return 3;
    n = fread(bytes, 1, sizeof(bytes), f);
    if (n != sizeof(bytes) || fgetc(f) != EOF) { fclose(f); return 4; }
    if (fclose(f)) return 5;
    if (!walkerPingAcceptOk((const WalkerDirectHeader *)bytes)) return 6;
    bytes[9] = WALKER_DIRECT_PUSH_TO_PHONE;
    if (walkerPingAcceptOk((const WalkerDirectHeader *)bytes)) return 7;
    bytes[9] = WALKER_DIRECT_OK;
    bytes[20] = '1';
    if (walkerPingAcceptOk((const WalkerDirectHeader *)bytes)) return 8;
    puts("PASS: DSi C validated actual Java Android OP_OK response; forbidden opcodes rejected.");
    return 0;
}
