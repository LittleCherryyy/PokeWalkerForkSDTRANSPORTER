/* V7.1 diagnostic PING flow for a future *verified* HGSS resident Wi-Fi
 * backend. GPL-3.0-or-later; retain Shinygati/SD-Transporter attribution.
 *
 * This interface has no side effects until a caller explicitly invokes it
 * with nonblocking network callbacks. It never reads a ROM, .walker, or save.
 * The only outbound operation is PWDSI001 OP_PING (88 bytes).
 */
#ifndef WALKER_PING_FSM_H
#define WALKER_PING_FSM_H
#include "walker_directsync.h"

#define WALKER_PING_DEFAULT_TICKS 300u

enum {
    WALKER_PING_IDLE = 0,
    WALKER_PING_CONNECTING = 1,
    WALKER_PING_SENDING = 2,
    WALKER_PING_RECEIVING = 3,
    WALKER_PING_OK = 4,
    WALKER_PING_FAILED = 5,
    WALKER_PING_TIMEOUT = 6
};

/* Each callback MUST be nonblocking and perform bounded work.
 * connect_gateway connects to the Android hotspot's DHCP gateway, with
 * the supplied TCP port, returning: 1 connected, 0 pending, -1 failure.
 * Repeated calls while pending must poll the SAME in-flight connection.
 * send_some / recv_some return positive bytes processed, 0 pending,
 * -1 failure. Never return more bytes than the provided capacity.
 * close_connection must not block; it is called at most once on completion.
 *
 * Hardware network initialization, discovery of a valid gateway, Wi-Fi
 * ownership and callback implementations are explicitly NOT provided here.
 */
typedef struct WalkerPingIo {
    int (*connect_gateway)(void *context, unsigned port);
    int (*send_some)(void *context, const unsigned char *bytes, unsigned count);
    int (*recv_some)(void *context, unsigned char *bytes, unsigned count);
    void (*close_connection)(void *context);
} WalkerPingIo;

typedef struct WalkerPingFlow {
    unsigned state;
    unsigned ticks;
    unsigned tickLimit;
    unsigned sent;
    unsigned received;
    unsigned char request[WALKER_DIRECT_HEADER_SIZE];
    unsigned char response[WALKER_DIRECT_HEADER_SIZE];
} WalkerPingFlow;

void walkerPingStart(WalkerPingFlow *flow, unsigned tickLimit);
unsigned walkerPingStep(WalkerPingFlow *flow, const WalkerPingIo *io, void *context);

#endif
