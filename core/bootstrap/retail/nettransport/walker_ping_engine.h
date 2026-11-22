/* V7.2 resident transport: PING-only framing state machine.
 * GPL-3.0-or-later. No sockets, radio hardware, ROM or save operations here.
 *
 * Future ARM9 adapter supplies NON-BLOCKING send/receive callbacks and calls
 * walkerPingStep() from a normal (not IRQ/VBlank) menu/cooperative context.
 * Callbacks: >0 bytes transferred, 0 would-block, <0 unrecoverable failure.
 */
#ifndef WALKER_PING_ENGINE_H
#define WALKER_PING_ENGINE_H
#include <stdint.h>
#include "walker_directsync.h"

enum {
    WALKER_PING_IDLE=0,
    WALKER_PING_SENDING=1,
    WALKER_PING_RECEIVING=2,
    WALKER_PING_OK=3,
    WALKER_PING_FAILED=4
};
enum {
    WALKER_PING_ERROR_NONE=0,
    WALKER_PING_ERROR_ARGUMENT=1,
    WALKER_PING_ERROR_TIMEOUT=2,
    WALKER_PING_ERROR_SEND=3,
    WALKER_PING_ERROR_RECV=4,
    WALKER_PING_ERROR_REPLY=5
};

typedef int (*WalkerPingIoFn)(void *user, uint8_t *bytes, unsigned length);
typedef struct {
    void *user;
    WalkerPingIoFn send;
    WalkerPingIoFn recv;
} WalkerPingIo;

typedef struct {
    uint8_t tx[WALKER_DIRECT_HEADER_SIZE];
    uint8_t rx[WALKER_DIRECT_HEADER_SIZE];
    uint32_t started;
    uint32_t timeoutFrames;
    unsigned sent;
    unsigned received;
    int state;
    int error;
} WalkerPing;

void walkerPingStart(WalkerPing *p, uint32_t frame, uint32_t timeoutFrames);
/* At most ONE I/O callback invocation per step; never loops or sleeps.
 * Caller MUST use a real non-blocking transport and a monotonic frame tick. */
int walkerPingStep(WalkerPing *p, const WalkerPingIo *io, uint32_t frame);
#endif
