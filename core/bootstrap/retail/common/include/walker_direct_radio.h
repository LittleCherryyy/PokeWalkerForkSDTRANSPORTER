/* ARM9 resident Direct Sync radio abstraction for the virtual Pokéwalker.
 * Backends must perform nonblocking calls ONLY outside IRQ contexts.
 * GPL-3.0-or-later.
 */
#ifndef WALKER_DIRECT_RADIO_H
#define WALKER_DIRECT_RADIO_H
typedef struct WalkerDirectRadioOps {
    /* 1 ready to connect, 0 not available. Never guess Wi-Fi symbol ABI. */
    int (*available)(void);
    /* 1 connected, 0 in progress, -1 fatal. Idempotent per connection.
     * Destination is the phone's hotspot gateway, TCP port 30821. */
    int (*connect)(unsigned port);
    /* Partial I/O: >0 bytes, 0 would block, <0 fatal. */
    int (*write)(const unsigned char *data, unsigned size);
    int (*read)(unsigned char *data, unsigned size);
    void (*close)(void);
} WalkerDirectRadioOps;

/* A verified hardware-specific backend supplies a STRONG definition.
 * Without one, the default returns NULL and outbound checkout is
 * safely left on the SD rather than claiming a successful transfer. */
const WalkerDirectRadioOps *walkerDirectRadioBackend(void);
#endif
