/* Direct DSi <-> Android Pokewalker transport. GPL-3.0-or-later.
 *
 * The phone is the TCP server (port 30821) and nds-bootstrap is the client.
 * All multibyte integers in WalkerDirectHeader are big-endian on the wire.
 * Header is followed by payloadLength bytes. Payload CRC is standard CRC32.
 */
#ifndef WALKER_DIRECTSYNC_H
#define WALKER_DIRECTSYNC_H

#define WALKER_DIRECT_MAGIC "PWDSI001"
#define WALKER_DIRECT_MAGIC_SIZE 8u
#define WALKER_DIRECT_VERSION 1u
#define WALKER_DIRECT_PORT 30821u
#define WALKER_DIRECT_HEADER_SIZE 88u
#define WALKER_DIRECT_SESSION_SIZE 32u
#define WALKER_DIRECT_TRAINER_SIZE 36u
#define WALKER_DIRECT_WALKER_SIZE 65536u

#define WALKER_DIRECT_PUSH_TO_PHONE 1u
#define WALKER_DIRECT_PULL_FROM_PHONE 2u
#define WALKER_DIRECT_CONFIRM_RETURN 3u
#define WALKER_DIRECT_PING 4u
#define WALKER_DIRECT_OK 0x80u
#define WALKER_DIRECT_ERROR 0x7fu

#ifndef __ASSEMBLER__
typedef struct WalkerDirectHeader {
    unsigned char magic[8];
    unsigned char version;
    unsigned char op;
    unsigned char flagsBE[2];
    unsigned char payloadLengthBE[4];
    unsigned char crc32BE[4];
    char session[32];
    char trainer[36];
} WalkerDirectHeader;

typedef char walker_direct_header_size[(sizeof(WalkerDirectHeader)==WALKER_DIRECT_HEADER_SIZE)?1:-1];

static unsigned walkerDirectBe16(const unsigned char p[2]) {
    return ((unsigned)p[0]<<8)|p[1];
}
static unsigned walkerDirectBe32(const unsigned char p[4]) {
    return ((unsigned)p[0]<<24)|((unsigned)p[1]<<16)|((unsigned)p[2]<<8)|p[3];
}
static void walkerDirectPut16(unsigned char p[2],unsigned value) {
    p[0]=(unsigned char)(value>>8);p[1]=(unsigned char)value;
}
static void walkerDirectPut32(unsigned char p[4],unsigned value) {
    p[0]=(unsigned char)(value>>24);p[1]=(unsigned char)(value>>16);p[2]=(unsigned char)(value>>8);p[3]=(unsigned char)value;
}
#endif
#endif
