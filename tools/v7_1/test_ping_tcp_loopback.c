/* Loopback TCP integration test of the exact V7.1 ARM9 PING state machine.
 * This program is for Linux CI only; the destination port is dynamically
 * assigned by the local Java test fixture. The FSM itself requests 30821,
 * exactly as it would for the Android hotspot. No ROM, SD or save access.
 */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>
#include "walker_ping_fsm.h"

typedef struct Loopback {
    int fd, connected;
    unsigned port, callbacks, closes, requestedPort;
} Loopback;

static int connect_gateway(void *arg, unsigned requestedPort) {
    Loopback *c=(Loopback *)arg;
    struct sockaddr_in target;
    int rc;
    ++c->callbacks;
    c->requestedPort=requestedPort;
    if (requestedPort!=30821) return -1;
    if (c->connected) return 1;
    if (c->fd<0) {
        c->fd=socket(AF_INET,SOCK_STREAM,0);
        if (c->fd<0) return -1;
        int flags=fcntl(c->fd,F_GETFL,0);
        if (flags<0 || fcntl(c->fd,F_SETFL,flags|O_NONBLOCK)<0) return -1;
        memset(&target,0,sizeof(target));
        target.sin_family=AF_INET;
        target.sin_port=htons((unsigned short)c->port);
        target.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        rc=connect(c->fd,(struct sockaddr *)&target,sizeof(target));
        if (rc==0) {c->connected=1; return 1;}
        if (errno!=EINPROGRESS && errno!=EWOULDBLOCK) return -1;
        return 0;
    }
    struct pollfd pfd={c->fd,POLLOUT,0};
    rc=poll(&pfd,1,0);
    if (rc<0) return errno==EINTR ? 0 : -1;
    if (!rc) return 0;
    int err=0;
    socklen_t len=sizeof(err);
    if (getsockopt(c->fd,SOL_SOCKET,SO_ERROR,&err,&len)<0 || err) return -1;
    if (!(pfd.revents&POLLOUT)) return -1;
    c->connected=1;
    return 1;
}
static int send_some(void *arg, const unsigned char *bytes, unsigned count) {
    Loopback *c=(Loopback *)arg;
    ++c->callbacks;
    // Cap sends at 13 bytes, independently of TCP's own fragmentation.
    if (count>13u) count=13u;
    ssize_t n=send(c->fd,bytes,count,MSG_DONTWAIT|MSG_NOSIGNAL);
    if (n>0) return (int)n;
    if (n<0 && (errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR)) return 0;
    return -1;
}
static int recv_some(void *arg, unsigned char *bytes, unsigned count) {
    Loopback *c=(Loopback *)arg;
    ++c->callbacks;
    ssize_t n=recv(c->fd,bytes,count,MSG_DONTWAIT);
    if (n>0) return (int)n;
    if (n<0 && (errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR)) return 0;
    return -1; // EOF or fatal socket error
}
static void close_connection(void *arg) {
    Loopback *c=(Loopback *)arg;
    ++c->callbacks;
    ++c->closes;
    if (c->fd>=0) close(c->fd);
    c->fd=-1;
}
static const WalkerPingIo IO={
    connect_gateway,send_some,recv_some,close_connection
};

int main(int argc,char **argv) {
    if (argc!=2) return 2;
    char *end=NULL;
    long parsed=strtol(argv[1],&end,10);
    if (!end || *end || parsed<1 || parsed>65535) return 3;
    for (int phase=0;phase<2;phase++) {
        Loopback net={.fd=-1,.port=(unsigned)parsed};
        WalkerPingFlow flow;
        walkerPingStart(&flow,1400u);
        int finished=0;
        for (unsigned step=0;step<1400u;step++) {
            unsigned before=net.callbacks;
            unsigned result=walkerPingStep(&flow,&IO,&net);
            if (net.callbacks-before>1u) {
                fprintf(stderr,"FAIL: performed multiple syscalls per tick\n");
                return 4;
            }
            if (result==WALKER_PING_OK ||
                result==WALKER_PING_FAILED || result==WALKER_PING_TIMEOUT) {
                unsigned expected=phase==0?WALKER_PING_OK:WALKER_PING_FAILED;
                if (result!=expected || net.closes!=1 ||
                    net.requestedPort!=30821u || flow.sent!=88u ||
                    flow.received!=88u) {
                    fprintf(stderr,"FAIL: phase=%d state=%u closes=%u sent=%u received=%u\n",
                            phase,result,net.closes,flow.sent,flow.received);
                    return 5;
                }
                finished=1;
                break;
            }
            struct timespec delay={0,2000000L};
            nanosleep(&delay,NULL);
        }
        if (!finished) {
            fprintf(stderr,"FAIL: TCP phase %d did not terminate\n",phase);
            return 6;
        }
    }
    puts("PASS: real localhost TCP, Java Android protocol, partial PING and malicious-op rejection.");
    return 0;
}
