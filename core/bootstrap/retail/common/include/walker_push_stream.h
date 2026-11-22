/* Direct DSi -> Android Pokéwalker, complete 64 KiB checkout stream.
 * Pure C; intentionally independent of radio/socket initialization and
 * of the game's critical IR hook. GPL-3.0-or-later.
 *
 * This is the REAL PUSH_TO_PHONE wire format, not a diagnostic PING.
 * The nonblocking socket implementation and a safe ARM9 scheduling point
 * are still required before this can run inside HGSS.
 */
#ifndef WALKER_PUSH_STREAM_H
#define WALKER_PUSH_STREAM_H
#include <stdint.h>
#include "walker_directsync.h"

#define WALKER_PUSH_CHUNK 512u
enum {
    WALKER_PUSH_IDLE=0, WALKER_PUSH_HEADER=1, WALKER_PUSH_DATA=2,
    WALKER_PUSH_ACK=3, WALKER_PUSH_DONE=4, WALKER_PUSH_FAILED=5
};

typedef struct WalkerPushStream {
    unsigned char header[WALKER_DIRECT_HEADER_SIZE];
    unsigned char ack[WALKER_DIRECT_HEADER_SIZE];
    const unsigned char *eeprom; /* Must remain immutable until ACK. */
    uint32_t durableSeq;
    uint32_t sentHeader;
    uint32_t sentData;
    uint32_t receivedAck;
    unsigned phase;
} WalkerPushStream;

/* Write/read attempt a nonblocking operation, returning:
 *    >0  number of bytes transferred (may be partial)
 *     0  would block; invoke step later from non-IRQ ARM9 code
 *    <0  socket closed or failed (caller retains the SD .walker copy)
 */
typedef struct WalkerPushIo {
    int (*write)(void *, const unsigned char *, unsigned);
    int (*read)(void *, unsigned char *, unsigned);
} WalkerPushIo;

/* 0 on initialized, -1 for invalid values. Session is exactly 32 hex ASCII
 * and trainer either empty or exactly 36 hex ASCII (Android verifies it). */
int walkerPushBegin(WalkerPushStream *s, const unsigned char *image,
                    uint32_t durableSeq, uint32_t crc,
                    const char *session, const char *trainer);

/* 0=pending; 1=validated Android OP_OK; -1=invalidated/error.
 * One bounded socket operation per call. Caller guarantees a TCP connection,
 * checks timeout/retry and that EEPROM sequence remains unchanged. */
int walkerPushStep(WalkerPushStream *s, const WalkerPushIo *io, void *ctx,
                   uint32_t currentWriteSeq);

#endif
