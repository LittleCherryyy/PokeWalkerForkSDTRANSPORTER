/* Synthetic host regression of HGSS's NATIVE Nitro SOC ABI adapter.
 * Does not initialize Wi-Fi or use actual Pokémon/save data.
 *
 * gcc -std=c99 -O2 -Wall -Wextra -Werror \
 *   -DWALKER_HGSS_SOC_ADAPTER_TEST \
 *   -I core/bootstrap/retail/common/include \
 *   core/bootstrap/retail/transport/walker_hgss_soc_radio.c \
 *   core/bootstrap/retail/transport/walker_push_stream.c \
 *   core/tools/test_walker_hgss_soc_radio.c -o /tmp/test-hgss-soc
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "walker_hgss_soc_radio.h"
#include "walker_push_stream.h"

#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %s line %d\n",#x,__LINE__);return 1;}}while(0)
#define STREAM_SIZE (WALKER_DIRECT_HEADER_SIZE + WALKER_DIRECT_WALKER_SIZE)

static unsigned char sent[STREAM_SIZE];
static unsigned sentLen;
static unsigned char ack[WALKER_DIRECT_HEADER_SIZE];
static unsigned ackOff;
static WalkerHgssOverlaySlot overlays[WALKER_HGSS_OVERLAY_SLOTS];
static int valid=1;
static int connectCalls;
static int closeCalls;
static int shutdownCalls;
static int fcntlMode;
static int socketCalls;
static int gatewayChecked;
static int mockReady(void){return valid;}
static int mockSocket(int domain,int type,int proto){
    if(domain!=2||type!=1||proto!=0)return -1;
    socketCalls++;
    return 7;
}
static int mockFcntl(int fd,int command,int arg){
    if(fd!=7)return -1;
    if(command==3)return 0;
    if(command==4){fcntlMode=arg;return 0;}
    return -1;
}
static int mockConnect(int fd,const WalkerHgssSocAddress *addr){
    if(fd!=7 || addr->length!=8 || addr->family!=2 ||
       addr->portBE[0]!=(30821>>8) || addr->portBE[1]!=(30821&255) ||
       addr->ip[0]!=192 || addr->ip[1]!=168 ||
       addr->ip[2]!=0 || addr->ip[3]!=1)
        return -1;
    gatewayChecked++;
    return connectCalls++ ? 0 : -26; /* game's SOC_EINPROGRESS */
}
static int mockSend(int fd,const void *data,int length,int flags){
    if(fd!=7 || flags || length<=0 || sentLen+(unsigned)length>STREAM_SIZE) return -1;
    if(length>29) length=29; /* Native TCP can send fewer than requested. */
    memcpy(sent+sentLen,data,(unsigned)length);
    sentLen+=(unsigned)length;
    return length;
}
static int mockRecv(int fd,void *data,int length,int flags){
    if(fd!=7 || flags || sentLen!=STREAM_SIZE)return -1;
    if(ackOff>=WALKER_DIRECT_HEADER_SIZE)return 0; /* EOF */
    if(length>11)length=11;
    if((unsigned)length>WALKER_DIRECT_HEADER_SIZE-ackOff)
        length=(int)(WALKER_DIRECT_HEADER_SIZE-ackOff);
    memcpy(data,ack+ackOff,(unsigned)length);ackOff+=(unsigned)length;
    return length;
}
static int mockShutdown(int fd,int how){
    if(fd!=7 || how!=2)return -1;
    shutdownCalls++;
    return 0;
}
static int mockClose(int fd){
    if(fd!=7)return -1;
    closeCalls++;
    return 0;
}
static WalkerHgssSocBindings makeApi(void){
    WalkerHgssSocBindings a;
    memset(&a,0,sizeof(a));
    a.magic=WALKER_HGSS_SOC_BIND_MAGIC;
    a.version=WALKER_HGSS_SOC_BIND_VERSION;
    a.overlayStart=WALKER_HGSS_SOC_OV0_START;
    a.overlayEnd=WALKER_HGSS_SOC_OV0_END;
    a.pokewalkerUnloaded=1;
    a.networkingLoaded=1;
    a.socStarted=1;
    a.arm7WifiReady=1;
    a.gameOverlaySlots=overlays;
    overlays[0].id=0;overlays[0].active=1;
    a.gateway[0]=192;a.gateway[1]=168;a.gateway[2]=0;a.gateway[3]=1;
    a.socSocket=mockSocket;a.socFcntl=mockFcntl;
    a.socConnect=mockConnect;a.socSend=mockSend;a.socRecv=mockRecv;
    a.socShutdown=mockShutdown;a.socClose=mockClose;
    a.stillReady=mockReady;
    return a;
}
static uint32_t crc32(const unsigned char *data,unsigned length){
    uint32_t crc=0xffffffffu;
    for(unsigned i=0;i<length;i++){
        crc^=data[i];
        for(unsigned bit=0;bit<8;bit++)
            crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
    }
    return ~crc;
}
static int stepWrite(void *ctx,const unsigned char *buf,unsigned n){
    const WalkerDirectRadioOps *r=(const WalkerDirectRadioOps*)ctx;
    return r->write(buf,n);
}
static int stepRead(void *ctx,unsigned char *buf,unsigned n){
    const WalkerDirectRadioOps *r=(const WalkerDirectRadioOps*)ctx;
    return r->read(buf,n);
}
int main(void){
    WalkerHgssSocBindings api=makeApi();
    CHECK(walkerHgssSocRadioOps()==0);
    api.pokewalkerUnloaded=0;
    CHECK(!walkerHgssSocBind(&api));
    api.pokewalkerUnloaded=1;api.networkingLoaded=0;
    CHECK(!walkerHgssSocBind(&api));
    api.networkingLoaded=1;api.socStarted=0;
    CHECK(!walkerHgssSocBind(&api));
    api.socStarted=1;api.arm7WifiReady=0;
    CHECK(!walkerHgssSocBind(&api));
    api.arm7WifiReady=1;
    api.gateway[0]=0;
    CHECK(!walkerHgssSocBind(&api));
    api.gateway[0]=192;
    /* Real game overlay-manager table: never bind while Pokewalker
     * 112 is active or networking overlay 0 has been unloaded. */
    overlays[1].id=112;overlays[1].active=1;
    CHECK(!walkerHgssSocBind(&api));
    overlays[1].active=0;
    overlays[0].active=0;
    CHECK(!walkerHgssSocBind(&api));
    overlays[0].active=1;
    valid=0;
    CHECK(!walkerHgssSocBind(&api));
    valid=1;
    CHECK(walkerHgssSocBind(&api));
    CHECK(!walkerHgssSocBind(&api)); /* one immutable binding */
    const WalkerDirectRadioOps *ops=walkerHgssSocRadioOps();
    CHECK(ops && ops->available());
    CHECK(ops->connect(30821)==0);
    CHECK(ops->connect(30821)==1);
    CHECK(socketCalls==1 && gatewayChecked==2);
    CHECK(fcntlMode==4);
    overlays[1].active=1;
    CHECK(!ops->available());
    CHECK(ops->write(sent,1)<0);
    overlays[1].active=0;
    CHECK(ops->available());

    static unsigned char walker[WALKER_DIRECT_WALKER_SIZE];
    for(unsigned i=0;i<sizeof(walker);i++)walker[i]=(unsigned char)(i*73u+19u);
    const uint32_t crc=crc32(walker,sizeof(walker));
    const char *session="0123456789abcdef0123456789abcdef";
    memset(ack,0,sizeof(ack));
    memcpy(ack,WALKER_DIRECT_MAGIC,8);ack[8]=WALKER_DIRECT_VERSION;
    ack[9]=WALKER_DIRECT_OK;memcpy(ack+20,session,32);
    WalkerPushStream stream;
    CHECK(walkerPushBegin(&stream,walker,47,crc,session,"")==0);
    const WalkerPushIo io={stepWrite,stepRead};
    int done=0;
    for(unsigned tick=0;tick<9000;tick++){
        done=walkerPushStep(&stream,&io,(void*)ops,47);
        if(done!=0)break;
    }
    CHECK(done==1 && stream.phase==WALKER_PUSH_DONE);
    CHECK(sentLen==STREAM_SIZE);
    CHECK(!memcmp(sent,WALKER_DIRECT_MAGIC,8));
    CHECK(sent[9]==WALKER_DIRECT_PUSH_TO_PHONE);
    CHECK(walkerDirectBe32(sent+12)==WALKER_DIRECT_WALKER_SIZE);
    CHECK(walkerDirectBe32(sent+16)==crc);
    CHECK(!memcmp(sent+20,session,32));
    CHECK(!memcmp(sent+WALKER_DIRECT_HEADER_SIZE,walker,sizeof(walker)));

    valid=0;
    CHECK(!ops->available());
    CHECK(ops->write(walker,1)<0);
    valid=1;
    ops->close();
    CHECK(closeCalls==1 && shutdownCalls==1);
    CHECK(ops->available());
    walkerHgssSocInvalidate();
    CHECK(walkerHgssSocRadioOps()==0);
    CHECK(!walkerHgssSocBind(&api)); /* stale overlay cannot be reused */
    puts("PASS: HGSS native SOC ABI, overlay/WFC gates, nonblocking connect,");
    puts("      real 64KiB PUSH stream, Android OK parsing, safe invalidation");
    puts("LIMIT: native API used fake SOC functions; in-game overlay and radio still unverified");
    return 0;
}
