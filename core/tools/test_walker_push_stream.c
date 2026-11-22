/* Host-only test of the real 65536-byte DSi TCP checkout sender.
 * Synthetic bytes exercise framing; no copyrighted ROM or save required.
 * This does NOT prove Wi-Fi is usable while HeartGold runs.
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "walker_push_stream.h"

#define SIZE (WALKER_DIRECT_HEADER_SIZE+WALKER_DIRECT_WALKER_SIZE)
#define CHECK(x) do { if(!(x)) {fprintf(stderr,"FAIL: %s (%d)\n",#x,__LINE__);return 1;} }while(0)

typedef struct Mock {
    unsigned char sent[SIZE], ack[WALKER_DIRECT_HEADER_SIZE];
    unsigned sentLen, ackOffset, calls;
} Mock;

static int fakeWrite(void *ctx,const unsigned char *p,unsigned n) {
    Mock *m=(Mock *)ctx;
    if((m->calls++%13)==0) return 0; /* would block */
    if(n>17)n=17; /* TCP partial write */
    if(m->sentLen+n>SIZE)return -1;
    memcpy(m->sent+m->sentLen,p,n);m->sentLen+=n;
    return (int)n;
}
static int fakeRead(void *ctx,unsigned char *p,unsigned n) {
    Mock *m=(Mock *)ctx;
    if(m->sentLen!=SIZE)return -1; /* no ACK before full payload */
    if((m->calls++%11)==0)return 0;
    if(n>9)n=9; /* fragmented ACK */
    if(n>WALKER_DIRECT_HEADER_SIZE-m->ackOffset)
        n=WALKER_DIRECT_HEADER_SIZE-m->ackOffset;
    memcpy(p,m->ack+m->ackOffset,n);m->ackOffset+=n;
    return (int)n;
}

static uint32_t crc32(const unsigned char *p,unsigned n) {
    uint32_t crc=0xffffffffu;
    for(unsigned i=0;i<n;i++) {
        crc^=p[i];
        for(unsigned bit=0;bit<8;bit++)
            crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
    }
    return ~crc;
}
static void makeAck(Mock *m,const char *session) {
    memset(m,0,sizeof(*m));
    memcpy(m->ack,WALKER_DIRECT_MAGIC,8);
    m->ack[8]=WALKER_DIRECT_VERSION;
    m->ack[9]=WALKER_DIRECT_OK;
    memcpy(m->ack+20,session,32);
}
static int runUntilDone(WalkerPushStream *s,Mock *m,uint32_t seq) {
    const WalkerPushIo io={fakeWrite,fakeRead};
    for(unsigned tick=0;tick<20000;tick++) {
        int r=walkerPushStep(s,&io,m,seq);
        if(r!=0)return r;
    }
    return 0;
}
int main(int argc, char **argv) {
    unsigned char image[WALKER_DIRECT_WALKER_SIZE];
    const char *session="0123456789abcdef0123456789abcdef";
    const char *trainer="0123456789abcdef0123456789abcdef0123";
    for(unsigned i=0;i<sizeof(image);i++)image[i]=(unsigned char)(i*73u+19u);
    const uint32_t crc=crc32(image,sizeof(image));
    Mock m;
    WalkerPushStream s;

    if(argc==3 && strcmp(argv[1],"--android-ack")==0) {
        /* The reply came from Java DirectSyncProtocol.write(), not from
         * our native test's hand-built mock header. Re-send the same
         * synthetic 64KiB payload and verify the true Java OP_OK. */
        makeAck(&m,session);
        FILE *reply=fopen(argv[2],"rb");
        CHECK(reply!=NULL);
        CHECK(fread(m.ack,1,WALKER_DIRECT_HEADER_SIZE,reply)==WALKER_DIRECT_HEADER_SIZE);
        CHECK(fgetc(reply)==EOF && !ferror(reply));
        CHECK(fclose(reply)==0);
        CHECK(walkerPushBegin(&s,image,42,crc,session,trainer)==0);
        CHECK(runUntilDone(&s,&m,42)==1);
        CHECK(s.phase==WALKER_PUSH_DONE);
        puts("PASS: C sender verified exact Android Java OP_OK ACK");
        return 0;
    }

    makeAck(&m,session);
    CHECK(walkerPushBegin(&s,image,42,crc,session,trainer)==0);
    /* App returns the registered trainer binding, not the empty string. */
    memcpy(m.ack+52,trainer,36);
    CHECK(runUntilDone(&s,&m,42)==1);
    CHECK(s.phase==WALKER_PUSH_DONE);
    CHECK(m.sentLen==SIZE);
    CHECK(memcmp(m.sent,WALKER_DIRECT_MAGIC,8)==0);
    CHECK(m.sent[8]==WALKER_DIRECT_VERSION && m.sent[9]==WALKER_DIRECT_PUSH_TO_PHONE);
    CHECK(walkerDirectBe32(m.sent+12)==WALKER_DIRECT_WALKER_SIZE);
    CHECK(walkerDirectBe32(m.sent+16)==crc);
    CHECK(memcmp(m.sent+20,session,32)==0 && memcmp(m.sent+52,trainer,36)==0);
    CHECK(memcmp(m.sent+WALKER_DIRECT_HEADER_SIZE,image,sizeof(image))==0);

    /* Cross-language fixture: Java Android DirectSyncProtocol.read must
     * parse this EXACT C-produced frame, not a separately re-encoded mock.
     * A fixture is synthetic bytes only, never a real Pokémon/save. */
    if(argc==2) {
        FILE *file=fopen(argv[1],"wb");
        CHECK(file!=NULL);
        CHECK(fwrite(m.sent,1,SIZE,file)==SIZE);
        CHECK(fclose(file)==0);
    } else {
        CHECK(argc==1);
    }

    makeAck(&m,session);
    m.ack[20]='f'; /* incorrect ACK session */
    CHECK(walkerPushBegin(&s,image,42,crc,session,"")==0);
    CHECK(runUntilDone(&s,&m,42)==-1 && s.phase==WALKER_PUSH_FAILED);

    makeAck(&m,session);
    CHECK(walkerPushBegin(&s,image,42,crc,session,"")==0);
    const WalkerPushIo io={fakeWrite,fakeRead};
    CHECK(walkerPushStep(&s,&io,&m,42)==0);
    CHECK(walkerPushStep(&s,&io,&m,43)==-1); /* EEPROM changed */
    CHECK(s.phase==WALKER_PUSH_FAILED);

    CHECK(walkerPushBegin(&s,image,42,crc,"short","")==-1);
    printf("PASS: 64KiB PUSH bytes/CRC, partial TCP I/O, ACK binding, mutation guard\n");
    puts("LIMIT: socket backend and safe in-game ARM9 worker are not implemented");
    return 0;
}
