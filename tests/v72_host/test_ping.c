/* Host-only protocol tests — synthetic OP_OK, no game/save, no Wi-Fi. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "walker_ping_engine.h"

typedef struct {
    uint8_t tx[88], reply[88];
    unsigned txOffset, rxOffset;
    unsigned chunks;
    unsigned callbackCount;
    int blockSend, blockRecv, failSend, failRecv;
} Mock;
static int sendFake(void *p,uint8_t *b,unsigned n) {
    Mock *m=p;m->callbackCount++;
    if(m->failSend)return -1;
    if(m->blockSend>0){m->blockSend--;return 0;}
    unsigned take=n<m->chunks?n:m->chunks;
    if(take>sizeof(m->tx)-m->txOffset)return -1;
    memcpy(m->tx+m->txOffset,b,take);m->txOffset+=take;
    return (int)take;
}
static int recvFake(void *p,uint8_t *b,unsigned n) {
    Mock *m=p;m->callbackCount++;
    if(m->failRecv)return -1;
    if(m->blockRecv>0){m->blockRecv--;return 0;}
    unsigned take=n<m->chunks?n:m->chunks;
    if(take>sizeof(m->reply)-m->rxOffset)return -1;
    memcpy(b,m->reply+m->rxOffset,take);m->rxOffset+=take;
    return (int)take;
}
static void setup(Mock *m) {
    memset(m,0,sizeof(*m));m->chunks=7;
    memcpy(m->reply,WALKER_DIRECT_MAGIC,8);
    m->reply[8]=WALKER_DIRECT_VERSION;
    m->reply[9]=WALKER_DIRECT_OK;
}
static WalkerPingIo makeIo(Mock *m) {
    WalkerPingIo io={m,sendFake,recvFake};
    return io;
}
static void test_fragments(void) {
    Mock m;setup(&m);m.blockSend=2;m.blockRecv=3;
    WalkerPing p;WalkerPingIo io=makeIo(&m);
    walkerPingStart(&p,100,250);
    assert(p.state==WALKER_PING_SENDING);
    unsigned t=100;
    for(;p.state!=WALKER_PING_OK && p.state!=WALKER_PING_FAILED;t++){
        unsigned before=m.callbackCount;
        walkerPingStep(&p,&io,t);
        assert(m.callbackCount==before+1); /* At most one callback/tick. */
        assert(t<345u);
    }
    assert(p.state==WALKER_PING_OK && p.error==0);
    assert(m.txOffset==88u && m.rxOffset==88u);
    assert(!memcmp(m.tx,WALKER_DIRECT_MAGIC,8));
    assert(m.tx[8]==WALKER_DIRECT_VERSION && m.tx[9]==WALKER_DIRECT_PING);
    for(unsigned i=10;i<88;i++)assert(m.tx[i]==0);
    assert(walkerPingStep(&p,&io,t)==WALKER_PING_OK);
}
static void test_reply_rejected(int offset,uint8_t wrong) {
    Mock m;setup(&m);m.chunks=88;m.reply[offset]=wrong;
    WalkerPing p;WalkerPingIo io=makeIo(&m);
    walkerPingStart(&p,5,30);
    assert(walkerPingStep(&p,&io,5)==WALKER_PING_RECEIVING);
    assert(walkerPingStep(&p,&io,6)==WALKER_PING_FAILED);
    assert(p.error==WALKER_PING_ERROR_REPLY);
}
static void test_timeouts_and_bad_io(void) {
    Mock m;setup(&m);m.blockSend=999;
    WalkerPing p;WalkerPingIo io=makeIo(&m);
    walkerPingStart(&p,90,3);
    assert(walkerPingStep(&p,&io,90)==WALKER_PING_SENDING);
    assert(walkerPingStep(&p,&io,91)==WALKER_PING_SENDING);
    assert(walkerPingStep(&p,&io,93)==WALKER_PING_FAILED);
    assert(p.error==WALKER_PING_ERROR_TIMEOUT);
    walkerPingStart(&p,0,0);
    assert(p.error==WALKER_PING_ERROR_ARGUMENT);
    walkerPingStart(&p,10,20);
    assert(walkerPingStep(&p,NULL,10)==WALKER_PING_FAILED);
    assert(p.error==WALKER_PING_ERROR_ARGUMENT);
    walkerPingStart(&p,10,20);
    m.failSend=1;
    assert(walkerPingStep(&p,&io,11)==WALKER_PING_FAILED);
    assert(p.error==WALKER_PING_ERROR_SEND);
    m.failSend=0;m.blockSend=0;m.chunks=88;m.failRecv=1;
    walkerPingStart(&p,0,20);
    assert(walkerPingStep(&p,&io,0)==WALKER_PING_RECEIVING);
    assert(walkerPingStep(&p,&io,1)==WALKER_PING_FAILED);
    assert(p.error==WALKER_PING_ERROR_RECV);
}
static void test_cancel(void) {
    Mock m;setup(&m);
    WalkerPing p;WalkerPingIo io=makeIo(&m);
    walkerPingStart(&p,0,60);
    walkerPingStep(&p,&io,0);
    assert(m.txOffset>0 && p.state==WALKER_PING_SENDING);
    walkerPingCancel(&p);
    assert(p.state==WALKER_PING_IDLE && p.sent==0 && p.received==0);
    unsigned calls=m.callbackCount;
    assert(walkerPingStep(&p,&io,1)==WALKER_PING_IDLE);
    assert(m.callbackCount==calls);
}
static void test_frame_wrap(void) {
    Mock m;setup(&m);m.chunks=88;
    WalkerPing p;WalkerPingIo io=makeIo(&m);
    walkerPingStart(&p,UINT32_MAX-1u,10);
    assert(walkerPingStep(&p,&io,UINT32_MAX)==WALKER_PING_RECEIVING);
    assert(walkerPingStep(&p,&io,0)==WALKER_PING_OK);
}
int main(void) {
    test_fragments();
    test_reply_rejected(0,'X'); /* bad magic */
    test_reply_rejected(8,3);   /* bad version */
    test_reply_rejected(9,1);   /* bad operation */
    test_reply_rejected(10,1);  /* unsupported flags */
    test_reply_rejected(12,1);  /* unexpected payload */
    test_reply_rejected(16,1);  /* CRC mismatch */
    test_reply_rejected(20,1);  /* unexpected session */
    test_reply_rejected(52,1);  /* unexpected trainer */
    test_timeouts_and_bad_io();
    test_frame_wrap();
    test_cancel();
    puts("PASS V7.2 PING: fragmentation, would-block, reply checks, bounded timeouts, u32-wrap");
    return 0;
}
