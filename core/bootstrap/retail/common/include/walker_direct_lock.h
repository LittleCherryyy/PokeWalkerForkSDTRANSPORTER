/* Persistent pre-send ownership fence for DIRECT DSi -> Android checkout.
 * GPL-3.0-or-later.
 *
 * File name: <save>.walker.directlock ; exact size 512 bytes.
 * A preallocated FAT cluster lets the ARM7 cardengine write/verify one
 * sector without creating files while HGSS is active.
 *
 * PREPARED is safe to launch; PENDING means a real Android checkout may
 * have succeeded, even if its ACK or the DSi power was lost. Launcher
 * MUST refuse HGSS while PENDING, regardless of Android availability.
 *
 * This is NOT a .walker.lease or .walker.phone record, so it does not
 * mislead the existing SD Transporter lease.c reader.
 */
#ifndef WALKER_DIRECT_LOCK_H
#define WALKER_DIRECT_LOCK_H
#include <stdint.h>
#include <string.h>

#define WALKER_LOCK_SIZE 512u
#define WALKER_LOCK_MAGIC "PWDLOCK1"
#define WALKER_LOCK_PREPARED 0u
#define WALKER_LOCK_PENDING 1u

/* Big-endian layout:
 * 0..7 magic, 8 status, 9..11 reserved, 12..15 walker seq,
 * 16..19 EEPROM CRC32, 20..51 32-byte hex session,
 * 52..87 36-byte optional hex trainer, 88..507 zero,
 * 508..511 CRC32 of the preceding 508 bytes.
 */
static inline uint32_t walkerLockGet32(const unsigned char *p) {
    return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|
           ((uint32_t)p[2]<<8)|(uint32_t)p[3];
}
static inline void walkerLockPut32(unsigned char *p,uint32_t value) {
    p[0]=(unsigned char)(value>>24);p[1]=(unsigned char)(value>>16);
    p[2]=(unsigned char)(value>>8);p[3]=(unsigned char)value;
}
static inline uint32_t walkerLockCrc32(const unsigned char *p,unsigned size) {
    uint32_t crc=0xffffffffu;
    for(unsigned i=0;i<size;i++){
        crc^=p[i];
        for(unsigned bit=0;bit<8;bit++)
            crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
    }
    return ~crc;
}
static inline int walkerLockHex(const char *p,unsigned length,int optional) {
    if(!p)return 0;
    if(optional && !p[0])return 1;
    for(unsigned i=0;i<length;i++)
        if(!((p[i]>='0'&&p[i]<='9')||(p[i]>='a'&&p[i]<='f')))
            return 0;
    return p[length]=='\0';
}
static inline void walkerLockPrepared(unsigned char out[WALKER_LOCK_SIZE]) {
    memset(out,0,WALKER_LOCK_SIZE);
    memcpy(out,WALKER_LOCK_MAGIC,8);
    walkerLockPut32(out+508,walkerLockCrc32(out,508));
}
/* -1 malformed/truncated/corrupt, 0 prepared, 1 phone-pending. */
static inline int walkerLockDecode(const unsigned char in[WALKER_LOCK_SIZE]) {
    if(memcmp(in,WALKER_LOCK_MAGIC,8)!=0 ||
       in[8]>WALKER_LOCK_PENDING ||
       in[9]||in[10]||in[11] ||
       walkerLockGet32(in+508)!=walkerLockCrc32(in,508))
        return -1;
    if(in[8]==WALKER_LOCK_PENDING){
        if(!walkerLockGet32(in+12))return -1;
        for(unsigned i=0;i<32;i++)
            if(!((in[20+i]>='0'&&in[20+i]<='9')||
                 (in[20+i]>='a'&&in[20+i]<='f')))return -1;
    } else {
        for(unsigned i=12;i<508;i++)if(in[i])return -1;
    }
    return (int)in[8];
}
/* Reserve phone ownership BEFORE emitting the first TCP byte.
 * On failure, remain PENDING (recovery explicitly required): the caller
 * cannot distinguish "the Android stored it but the TCP ACK was lost". */
static inline int walkerLockPending(unsigned char out[WALKER_LOCK_SIZE],
                  uint32_t seq,uint32_t imageCrc,
                  const char *session,const char *trainer) {
    if(!seq || !walkerLockHex(session,32,0) ||
       !walkerLockHex(trainer,36,1))return 0;
    walkerLockPrepared(out);
    out[8]=WALKER_LOCK_PENDING;
    walkerLockPut32(out+12,seq);
    walkerLockPut32(out+16,imageCrc);
    memcpy(out+20,session,32);
    if(trainer[0])memcpy(out+52,trainer,36);
    walkerLockPut32(out+508,walkerLockCrc32(out,508));
    return 1;
}
#endif
