/* HGSS Nintendo Nitro SOC adapter for a REAL 65536-byte Pokewalker send.
 * GPL-3.0-or-later.
 *
 * The socket ABI is grounded in pret/pokeheartgold's overlay 39 assembly
 * (SOC_Socket, SOC_Fcntl, SOC_Connect, SOC_Send, SOC_Recv, SOC_Shutdown
 * and SOC_Close). Unlike POSIX connect, Nintendo SOC_Connect takes TWO
 * arguments and its sockaddr has an explicit eight-byte length.
 *
 * This file does NOT initialize Wi-Fi, force-load overlay 0 or hook the
 * game's scheduler. A verified game lifecycle service must first ensure
 * that overlay 112 was unloaded, overlay 0 was loaded by the game, SOC
 * started and the ARM7 Wi-Fi service associated with the phone hotspot.
 *
 * Default builds are EMPTY. Enable target code only after ALL four
 * independent runtime gates are actually proven; never merely set
 * them to silence a compilation error.
 */
#if defined(WALKER_HGSS_SOC_ADAPTER_TEST) || ( \
    defined(WALKER_HGSS_SOC_EXACT_ROM_VERIFIED) && \
    defined(WALKER_HGSS_POST_UNLOAD_HOOK_VERIFIED) && \
    defined(WALKER_HGSS_WFC_LIFECYCLE_VERIFIED) && \
    defined(WALKER_HGSS_RAM_MAPPED_VERIFIED))
#include "walker_hgss_soc_radio.h"
#include <stddef.h>
#include <string.h>
#include <stdint.h>

enum { NATIVE_DOWN=0, NATIVE_CONNECTING=1, NATIVE_CONNECTED=2,
       NATIVE_RETIRED=3 };
/* Nintendo SOC_Fcntl(fd, F_GETFL=3, 0) and F_SETFL=4, O_NONBLOCK=4,
 * verified from HGSS ov39_02229AD4. */
#define SOC_F_GETFL 3
#define SOC_F_SETFL 4
#define SOC_O_NONBLOCK 4
/* Original HGSS ov39_02229BE4 retries SOC_Connect on -26 and treats
 * -30 (already connected) as success. These are the game's own return
 * codes, not portable errno values. */
#define SOC_EINPROGRESS (-26)
#define SOC_EISCONN (-30)

static WalkerHgssSocBindings game;
static int sock=-1;
static unsigned state;
static unsigned installed;

static int validGateway(const uint8_t ip[4]) {
    if(ip[0]==0 || ip[0]>=224 || ip[0]==127 ||
       (ip[0]==255 && ip[1]==255 && ip[2]==255 && ip[3]==255))
        return 0;
    return 1;
}
static int inside(const void *p,uint32_t begin,uint32_t end) {
#if defined(WALKER_HGSS_SOC_ADAPTER_TEST)
    /* Host callbacks have ASLR addresses; exercise the actual socket
     * adapter behavior, not fake host ARM overlay addresses. */
    (void)begin;(void)end;
    return p!=0;
#else
    uintptr_t address=(uintptr_t)p;
    address &= ~(uintptr_t)1u; /* accept ARM and Thumb entrypoint tags */
    return address >= (uintptr_t)begin && address < (uintptr_t)end;
#endif
}
static int validBindings(const WalkerHgssSocBindings *b) {
    if(!b || b->magic!=WALKER_HGSS_SOC_BIND_MAGIC ||
       b->version!=WALKER_HGSS_SOC_BIND_VERSION ||
       !b->pokewalkerUnloaded || !b->networkingLoaded ||
       !b->socStarted || !b->arm7WifiReady ||
       b->overlayStart!=WALKER_HGSS_SOC_OV0_START ||
       b->overlayEnd!=WALKER_HGSS_SOC_OV0_END ||
       !validGateway(b->gateway) ||
       !inside((const void*)b->socSocket,b->overlayStart,b->overlayEnd) ||
       !inside((const void*)b->socFcntl,b->overlayStart,b->overlayEnd) ||
       !inside((const void*)b->socConnect,b->overlayStart,b->overlayEnd) ||
       !inside((const void*)b->socSend,b->overlayStart,b->overlayEnd) ||
       !inside((const void*)b->socRecv,b->overlayStart,b->overlayEnd) ||
       !inside((const void*)b->socShutdown,b->overlayStart,b->overlayEnd) ||
       !inside((const void*)b->socClose,b->overlayStart,b->overlayEnd) ||
       !b->stillReady || !b->stillReady())return 0;
    return 1;
}
int walkerHgssSocBind(const WalkerHgssSocBindings *b) {
    /* Never replace an in-flight native session with new code pointers.
     * A false response here MUST NOT unlock the SD ownership fence. */
    if(installed || state!=NATIVE_DOWN || !validBindings(b))return 0;
    game=*b;
    installed=1;
    return 1;
}
void walkerHgssSocInvalidate(void) {
    /* The overlay might already be gone: it is unsafe to call SOC_Close
     * through a stale pointer. Preserve durable SD pending ownership. */
    installed=0;
    sock=-1;
    state=NATIVE_RETIRED;
    memset(&game,0,sizeof(game));
}
static int live(void) {
    return installed && state!=NATIVE_RETIRED &&
           game.stillReady && game.stillReady();
}
static int available(void) {
    return live() && validGateway(game.gateway);
}
static int connectPhone(unsigned port) {
    if(port!=30821u || !available())return -1;
    if(state==NATIVE_CONNECTED)return 1;
    if(state==NATIVE_DOWN) {
        int fd=game.socSocket(2,1,0);
        if(fd<0)return -1;
        sock=fd;
        int flags=game.socFcntl(fd,SOC_F_GETFL,0);
        if(flags<0 ||
           game.socFcntl(fd,SOC_F_SETFL,flags|SOC_O_NONBLOCK)<0) {
            state=NATIVE_RETIRED;
            return -1;
        }
        state=NATIVE_CONNECTING;
    }
    WalkerHgssSocAddress dst;
    dst.length=8;
    dst.family=2;
    dst.portBE[0]=(uint8_t)(port>>8);
    dst.portBE[1]=(uint8_t)port;
    memcpy(dst.ip,game.gateway,4);
    const int result=game.socConnect(sock,&dst);
    if(result>=0 || result==SOC_EISCONN) {
        state=NATIVE_CONNECTED;
        return 1;
    }
    if(result==SOC_EINPROGRESS)return 0;
    state=NATIVE_RETIRED;
    return -1;
}
static int writePhone(const unsigned char *data,unsigned length) {
    if(!available() || state!=NATIVE_CONNECTED || !data || !length)
        return -1;
    const int n=game.socSend(sock,data,(int)length,0);
    if(n>0 && (unsigned)n<=length)return n;
    if(n==SOC_EINPROGRESS)return 0;
    return -1;
}
static int readPhone(unsigned char *data,unsigned length) {
    if(!available() || state!=NATIVE_CONNECTED || !data || !length)
        return -1;
    const int n=game.socRecv(sock,data,(int)length,0);
    if(n>0 && (unsigned)n<=length)return n;
    if(n==SOC_EINPROGRESS)return 0;
    return -1;
}
static void closePhone(void) {
    if(!installed)return;
    /* Unload could have already occurred; checking live() avoids calling
     * code now overwritten by HGSS's next overlay. */
    if(sock>=0 && live()) {
        game.socShutdown(sock,2);
        game.socClose(sock);
    }
    sock=-1;
    state=NATIVE_DOWN;
}
static const WalkerDirectRadioOps ops={
    available,connectPhone,writePhone,readPhone,closePhone
};
const WalkerDirectRadioOps *walkerHgssSocRadioOps(void) {
    return installed ? &ops : 0;
}
#if !defined(WALKER_HGSS_SOC_ADAPTER_TEST)
const WalkerDirectRadioOps *walkerDirectRadioBackend(void) {
    return walkerHgssSocRadioOps();
}
#endif
#endif
