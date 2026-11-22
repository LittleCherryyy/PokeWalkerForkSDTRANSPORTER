/* Diagnostic-only resident ARM9 PING state machine. No save, ROM or
 * EEPROM access. No blocking Wi-Fi operations or guessed WCM/SOCL calls.
 * GPL-3.0-or-later, derived from the SD-Transporter fork.
 */
/* The primary HGSS cardengine has no spare VRAM for a full socket FSM yet:
 * linking this experimental component overflowed its reserved region by
 * 592 bytes. Compile this unit for host/cross-toolchain tests only until an
 * audited resident memory plan exists. This deliberately leaves the proven
 * PING header-only functions linked in the primary DSi cardengine. */
#if defined(WALKER_PING_FSM_EXPERIMENT) && !defined(DLDI) && !defined(GSDD) && !defined(TWLSDK)
#include "walker_ping_fsm.h"
#include "walker_ping_only.h"

/* Transition to a separate cleanup step so each call performs at most
 * one nonblocking network callback, including the final close. */
static unsigned finish(WalkerPingFlow *flow, unsigned state) {
    flow->finalState = state;
    flow->state = WALKER_PING_CLOSING;
    return flow->state;
}

void walkerPingStart(WalkerPingFlow *flow, unsigned tickLimit) {
    unsigned i;
    if (!flow) return;
    flow->state = WALKER_PING_CONNECTING;
    flow->ticks = 0;
    flow->finalState = WALKER_PING_FAILED;
    flow->tickLimit = tickLimit ? tickLimit : WALKER_PING_DEFAULT_TICKS;
    flow->sent = 0;
    flow->received = 0;
    walkerPingBuild((WalkerDirectHeader *)flow->request);
    for (i = 0; i < WALKER_DIRECT_HEADER_SIZE; ++i)
        flow->response[i] = 0;
}

/* One transport operation per invocation, never a busy loop. */
unsigned walkerPingStep(WalkerPingFlow *flow, const WalkerPingIo *io, void *context) {
    unsigned left;
    int n;
    if (!flow) return WALKER_PING_FAILED;
    if (flow->state == WALKER_PING_IDLE || flow->state == WALKER_PING_OK ||
        flow->state == WALKER_PING_FAILED || flow->state == WALKER_PING_TIMEOUT)
        return flow->state;
    if (!io || !io->connect_gateway || !io->send_some ||
        !io->recv_some || !io->close_connection) {
        flow->state = WALKER_PING_FAILED;
        return flow->state; /* No connection is known to exist. */
    }
    if (flow->state == WALKER_PING_CLOSING) {
        io->close_connection(context);
        flow->state = flow->finalState;
        return flow->state;
    }
    if (flow->ticks >= flow->tickLimit)
        return finish(flow, WALKER_PING_TIMEOUT);
    flow->ticks++;

    if (flow->state == WALKER_PING_CONNECTING) {
        n = io->connect_gateway(context, WALKER_DIRECT_PORT);
        if (n < 0 || n > 1)
            return finish(flow, WALKER_PING_FAILED);
        if (n == 1) flow->state = WALKER_PING_SENDING;
        return flow->state;
    }
    if (flow->state == WALKER_PING_SENDING) {
        left = WALKER_DIRECT_HEADER_SIZE - flow->sent;
        if (left == 0) { flow->state = WALKER_PING_RECEIVING; return flow->state; }
        n = io->send_some(context, flow->request + flow->sent, left);
        if (n < 0 || (unsigned)n > left)
            return finish(flow, WALKER_PING_FAILED);
        flow->sent += (unsigned)n;
        if (flow->sent == WALKER_DIRECT_HEADER_SIZE)
            flow->state = WALKER_PING_RECEIVING;
        return flow->state;
    }
    if (flow->state == WALKER_PING_RECEIVING) {
        left = WALKER_DIRECT_HEADER_SIZE - flow->received;
        if (left == 0)
            return finish(flow,
                          walkerPingAcceptOk((const WalkerDirectHeader *)flow->response)
                          ? WALKER_PING_OK : WALKER_PING_FAILED);
        n = io->recv_some(context, flow->response + flow->received, left);
        if (n < 0 || (unsigned)n > left)
            return finish(flow, WALKER_PING_FAILED);
        flow->received += (unsigned)n;
        if (flow->received == WALKER_DIRECT_HEADER_SIZE)
            return finish(flow,
                          walkerPingAcceptOk((const WalkerDirectHeader *)flow->response)
                          ? WALKER_PING_OK : WALKER_PING_FAILED);
        return flow->state;
    }
    return finish(flow, WALKER_PING_FAILED);
}
#endif /* primary DSi NTR cardengine only */
