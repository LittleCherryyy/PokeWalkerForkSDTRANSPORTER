/* Experimental concrete DSWifi TCP backend for direct HGSS checkout.
 * Copyright 2026 Pokéwalker Virtual contributors. GPL-3.0-or-later.
 *
 * This implementation sends REAL TCP bytes over an already initialized
 * DSWifi ARM9/ARM7 stack, to the Android phone's DHCP gateway.
 *
 * CRITICAL: DSWifi's ARM7 driver is NOT automatically available in retail
 * HGSS. Linking this file and setting an ARM9 compile flag alone WILL NOT
 * make Wi-Fi work. Do not enable this source in a DSi release until a
 * compatible resident ARM7 driver, FIFO/timer/IRQ ownership and safe
 * ARM9 scheduling have been implemented and hardware validated.
 *
 * The older standalone V6.4 hardware probe observed DSWifi close() hang.
 * This first-checkout backend deliberately never calls close(). It refuses
 * a second session until reset rather than risking a frozen game. It is
 * **not** yet a production radio lifecycle.
 *
 * To preserve the current fail-closed release, compile this file without
 * WALKER_RESIDENT_DSWIFI_ARM7_VERIFIED. Default builds contain no backend.
 */
#if defined(WALKER_RESIDENT_DSWIFI_ARM7_VERIFIED) && \
    !defined(TWLSDK) && !defined(B4DS) && !defined(DLDI) && !defined(GSDD)
#include <dswifi9.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include "walker_direct_radio.h"

static int fd=-1;
static int state; /* 0 idle; 1 connecting; 2 connected; 3 retired forever */
static unsigned long gateway;

static int available(void) {
    if(state==3) return 0;
    if(Wifi_AssocStatus()!=ASSOCSTATUS_ASSOCIATED) return 0;
    struct in_addr gw;
    (void)Wifi_GetIPInfo(&gw,0,0,0);
    gateway=gw.s_addr;
    return gateway!=0 && gateway!=0xffffffffUL;
}
static int beginConnection(unsigned port) {
    if(state==3 || port!=30821u) return -1;
    if(state==2) return 1;
    if(!available()) return -1;

    if(state==0) {
        fd=socket(AF_INET,SOCK_STREAM,0);
        if(fd<0) return -1;
        int flags=fcntl(fd,F_GETFL,0);
        if(flags<0 || fcntl(fd,F_SETFL,flags|O_NONBLOCK)<0) {
            state=3;return -1; /* Never call blocking close(). */
        }
        struct sockaddr_in dest;
        memset(&dest,0,sizeof(dest));
        dest.sin_family=AF_INET;
        dest.sin_port=htons((unsigned short)port);
        dest.sin_addr.s_addr=gateway;
        int rc=connect(fd,(struct sockaddr*)&dest,sizeof(dest));
        if(rc==0) {state=2;return 1;}
        if(errno!=EINPROGRESS && errno!=EALREADY &&
           errno!=EWOULDBLOCK) {state=3;return -1;}
        state=1;return 0;
    }
    if(state!=1)return -1;

    fd_set writable;
    FD_ZERO(&writable);FD_SET(fd,&writable);
    struct timeval tv={0,0};
    int rc=select(fd+1,0,&writable,0,&tv);
    if(rc<0){state=3;return -1;}
    if(rc==0)return 0;
    int socketError=0;
    socklen_t errorLength=sizeof(socketError);
    if(getsockopt(fd,SOL_SOCKET,SO_ERROR,&socketError,&errorLength)<0 ||
       socketError!=0){state=3;return -1;}
    state=2;return 1;
}
static int sendBytes(const unsigned char *data,unsigned size) {
    if(state!=2 || fd<0 || !data || !size)return -1;
    /* Never use blocking calls in an HGSS cardengine callback. */
    int n=send(fd,data,size,0);
    if(n>0)return n;
    if(n<0 && (errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR))return 0;
    return -1;
}
static int receiveBytes(unsigned char *data,unsigned size) {
    if(state!=2 || fd<0 || !data || !size)return -1;
    int n=recv(fd,data,size,0);
    if(n>0)return n;
    if(n<0 && (errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR))return 0;
    return -1; /* EOF or fatal error */
}
static void retire(void) {
    /* The original standalone DSi build could hang in close(). Prevent
     * both unsafe close and reuse until radio lifecycle is proven safe. */
    state=3;
}
static const WalkerDirectRadioOps ops={
    available,beginConnection,sendBytes,receiveBytes,retire
};
const WalkerDirectRadioOps *walkerDirectRadioBackend(void) {
    return &ops;
}
#endif
