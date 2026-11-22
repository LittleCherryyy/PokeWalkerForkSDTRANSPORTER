/* Native behavioral tests for the *exact* ARM9 PING FSM source.
 * Synthetic transport only; never opens Wi-Fi, reads a ROM or touches saves.
 */
#include <stdio.h>
#include <string.h>
#include "walker_ping_fsm.h"
#include "walker_ping_only.h"

typedef struct Fake {
    unsigned connect_calls, close_calls, sent, received, port, io_calls;
    unsigned connect_waits, send_limit, recv_limit;
    int never_connect, malformed_reply, fail_send, oversend, fail_recv;
    unsigned char outbound[WALKER_DIRECT_HEADER_SIZE];
    unsigned char reply[WALKER_DIRECT_HEADER_SIZE];
} Fake;

static void init(Fake *f) {
    WalkerDirectHeader h;
    memset(f, 0, sizeof(*f));
    f->connect_waits = 2;
    f->send_limit = 7;
    f->recv_limit = 11;
    walkerPingBuild(&h);
    h.op = WALKER_DIRECT_OK;
    memcpy(f->reply, &h, sizeof(h));
}
static int connect_gateway(void *arg, unsigned port) {
    Fake *f = (Fake *)arg;
    f->io_calls++;
    f->port = port;
    ++f->connect_calls;
    return f->never_connect || f->connect_calls <= f->connect_waits ? 0 : 1;
}
static int send_some(void *arg, const unsigned char *buf, unsigned count) {
    Fake *f = (Fake *)arg;
    f->io_calls++;
    if (f->fail_send) return -1;
    if (f->oversend) return (int)count + 1;
    if (count > f->send_limit) count = f->send_limit;
    memcpy(f->outbound + f->sent, buf, count);
    f->sent += count;
    return (int)count;
}
static int recv_some(void *arg, unsigned char *buf, unsigned count) {
    Fake *f = (Fake *)arg;
    f->io_calls++;
    if (f->fail_recv) return -1;
    if (count > f->recv_limit) count = f->recv_limit;
    memcpy(buf, f->reply + f->received, count);
    f->received += count;
    return (int)count;
}
static void close_connection(void *arg) {
    Fake *f = (Fake *)arg;
    f->io_calls++;
    ++f->close_calls;
}
static const WalkerPingIo OPS = {
    connect_gateway, send_some, recv_some, close_connection
};

#define CHECK(cond, msg) do { if(!(cond)) {fprintf(stderr, "FAIL: %s\n",msg);return 1;} } while(0)

static int run(Fake *f, WalkerPingFlow *flow, unsigned max) {
    unsigned step;
    for (step = 0; step < max; ++step) {
        unsigned before=f->io_calls;
        unsigned state=walkerPingStep(flow,&OPS,f);
        CHECK(f->io_calls - before <= 1u, "at most one callback per step");
        if (state == WALKER_PING_OK || state == WALKER_PING_FAILED ||
            state == WALKER_PING_TIMEOUT) return 0;
    }
    return 2;
}

int main(void) {
    Fake f;
    WalkerPingFlow flow;
    WalkerDirectHeader expected;
    unsigned after;

    init(&f);
    walkerPingStart(&flow, 300);
    CHECK(run(&f, &flow, 100) == 0, "good flow completes");
    CHECK(flow.state == WALKER_PING_OK, "PING receives OP_OK");
    CHECK(f.port == 30821, "correct Android server port");
    CHECK(f.sent == 88 && f.received == 88, "complete 88-byte frames");
    CHECK(f.close_calls == 1, "one nonblocking close on completion");
    walkerPingBuild(&expected);
    CHECK(memcmp(f.outbound,&expected,sizeof(expected)) == 0, "outbound PING exact byte match");
    after=f.io_calls;
    CHECK(walkerPingStep(&flow,&OPS,&f)==WALKER_PING_OK && f.io_calls==after,
          "terminal state does not redo I/O");

    init(&f);
    f.never_connect=1;
    walkerPingStart(&flow,3);
    CHECK(run(&f,&flow,10)==0 && flow.state==WALKER_PING_TIMEOUT,"bounded connection timeout");
    CHECK(f.sent==0 && f.close_calls==1,"timeout cannot send any data");

    init(&f);
    f.reply[9]=WALKER_DIRECT_PUSH_TO_PHONE;
    walkerPingStart(&flow,300);
    CHECK(run(&f,&flow,100)==0 && flow.state==WALKER_PING_FAILED,
          "reject PUSH response during ping");
    CHECK(f.close_calls==1,"close after invalid response");

    init(&f);
    f.reply[19]=0x80;
    walkerPingStart(&flow,300);
    CHECK(run(&f,&flow,100)==0 && flow.state==WALKER_PING_FAILED,
          "reject CRC mismatch");

    init(&f);
    f.fail_send=1;
    walkerPingStart(&flow,300);
    CHECK(run(&f,&flow,100)==0 && flow.state==WALKER_PING_FAILED,
          "reject negative send");

    init(&f);
    f.oversend=1;
    walkerPingStart(&flow,300);
    CHECK(run(&f,&flow,100)==0 && flow.state==WALKER_PING_FAILED,
          "reject backend out-of-bounds send result");

    init(&f);
    f.fail_recv=1;
    walkerPingStart(&flow,300);
    CHECK(run(&f,&flow,100)==0 && flow.state==WALKER_PING_FAILED,
          "reject negative recv");

    init(&f);
    walkerPingStart(&flow,300);
    CHECK(walkerPingStep(&flow,0,&f)==WALKER_PING_FAILED,
          "missing backend fails closed");
    CHECK(f.sent==0, "without backend no data sent");

    puts("PASS: bounded PING-only FSM handles partial I/O, pending connection, timeout and invalid replies.");
    return 0;
}
