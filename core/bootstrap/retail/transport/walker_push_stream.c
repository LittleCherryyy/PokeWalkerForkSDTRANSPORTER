/* Real 64 KiB virtual Pokéwalker transfer over an already connected,
 * nonblocking TCP stream. GPL-3.0-or-later.
 *
 * No network or file operations occur inside this module. It may be
 * called ONLY by a proven safe non-IRQ ARM9 resident worker.
 */
#include "walker_push_stream.h"
#include <string.h>

static int hexField(const char *p, unsigned count, int emptyAllowed) {
    if (!p) return 0;
    if (emptyAllowed && p[0] == '\0') return 1;
    for (unsigned i=0; i<count; ++i) {
        const char c=p[i];
        if (!((c>='0' && c<='9') || (c>='a' && c<='f'))) return 0;
    }
    return p[count] == '\0';
}

static unsigned minimum(unsigned a, unsigned b) {return a<b?a:b;}
static int failure(WalkerPushStream *s) {s->phase=WALKER_PUSH_FAILED;return -1;}

int walkerPushBegin(WalkerPushStream *s, const unsigned char *image,
                    uint32_t durableSeq, uint32_t crc,
                    const char *session, const char *trainer) {
    if (!s) return -1;
    memset(s,0,sizeof(*s));
    s->phase=WALKER_PUSH_FAILED;
    if (!image || !hexField(session,WALKER_DIRECT_SESSION_SIZE,0)
        || !hexField(trainer,WALKER_DIRECT_TRAINER_SIZE,1))
        return -1;
    unsigned char *h=s->header;
    memcpy(h,WALKER_DIRECT_MAGIC,WALKER_DIRECT_MAGIC_SIZE);
    h[8]=WALKER_DIRECT_VERSION;
    h[9]=WALKER_DIRECT_PUSH_TO_PHONE;
    walkerDirectPut32(h+12,WALKER_DIRECT_WALKER_SIZE);
    walkerDirectPut32(h+16,crc);
    memcpy(h+20,session,WALKER_DIRECT_SESSION_SIZE);
    if (trainer[0]) memcpy(h+52,trainer,WALKER_DIRECT_TRAINER_SIZE);
    s->eeprom=image;
    s->durableSeq=durableSeq;
    s->phase=WALKER_PUSH_HEADER;
    return 0;
}

static int validAck(const WalkerPushStream *s) {
    const unsigned char *a=s->ack;
    if(memcmp(a,WALKER_DIRECT_MAGIC,WALKER_DIRECT_MAGIC_SIZE)!=0 ||
       a[8]!=WALKER_DIRECT_VERSION || a[9]!=WALKER_DIRECT_OK ||
       a[10]!=0 || a[11]!=0 ||
       walkerDirectBe32(a+12)!=0 || walkerDirectBe32(a+16)!=0 ||
       memcmp(a+20,s->header+20,WALKER_DIRECT_SESSION_SIZE)!=0)
        return 0;
    /* Android fills the trainer binding in its ACK even when the DSi
     * did not have one in the outbound frame. Check it if supplied. */
    if(s->header[52] &&
       memcmp(a+52,s->header+52,WALKER_DIRECT_TRAINER_SIZE)!=0)
        return 0;
    return 1;
}

int walkerPushStep(WalkerPushStream *s, const WalkerPushIo *io, void *ctx,
                   uint32_t currentWriteSeq) {
    if(!s || !io || !io->write || !io->read) return -1;
    if(s->phase==WALKER_PUSH_DONE) return 1;
    if(s->phase==WALKER_PUSH_FAILED || s->phase==WALKER_PUSH_IDLE)
        return -1;
    /* If HGSS touches the virtual EEPROM while we are streaming,
     * abort. Sending a mixed old/new image would violate the CRC. */
    if(currentWriteSeq!=s->durableSeq) return failure(s);
    const unsigned char *data=0;
    unsigned remaining=0;
    unsigned *offset=0;
    if(s->phase==WALKER_PUSH_HEADER) {
        data=s->header;
        remaining=WALKER_DIRECT_HEADER_SIZE-s->sentHeader;
        offset=&s->sentHeader;
    } else if(s->phase==WALKER_PUSH_DATA) {
        data=s->eeprom;
        remaining=WALKER_DIRECT_WALKER_SIZE-s->sentData;
        offset=&s->sentData;
    }
    if(offset) {
        const unsigned count=minimum(remaining,WALKER_PUSH_CHUNK);
        const int n=io->write(ctx,data+*offset,count);
        if(n<0 || (unsigned)n>count) return failure(s);
        *offset+=(unsigned)n;
        if(s->phase==WALKER_PUSH_HEADER &&
           s->sentHeader==WALKER_DIRECT_HEADER_SIZE)
            s->phase=WALKER_PUSH_DATA;
        else if(s->phase==WALKER_PUSH_DATA &&
                s->sentData==WALKER_DIRECT_WALKER_SIZE)
            s->phase=WALKER_PUSH_ACK;
        return 0;
    }
    if(s->phase==WALKER_PUSH_ACK) {
        const unsigned count=WALKER_DIRECT_HEADER_SIZE-s->receivedAck;
        const int n=io->read(ctx,s->ack+s->receivedAck,count);
        if(n<0 || (unsigned)n>count) return failure(s);
        s->receivedAck+=(unsigned)n;
        if(s->receivedAck<WALKER_DIRECT_HEADER_SIZE) return 0;
        if(!validAck(s)) return failure(s);
        s->phase=WALKER_PUSH_DONE;
        return 1;
    }
    return failure(s);
}
