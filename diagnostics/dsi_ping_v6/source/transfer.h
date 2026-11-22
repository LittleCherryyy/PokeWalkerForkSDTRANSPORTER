#ifndef PW_TRANSFER_H
#define PW_TRANSFER_H
#include <stddef.h>
#include <stdint.h>
#define PW_TRANSFER_MAX 8192u
#define PW_CHUNK_MAX 512u
#define PW_ACT_BEGIN 0x10u
#define PW_ACT_CHUNK 0x11u
#define PW_ACT_COMMIT 0x12u
#define PW_ACT_ABORT 0x13u
/* Response codes are request | 0x80. Errors: response 0x7F, 2-byte big-endian code. */
#define PW_TERR_LENGTH 1u
#define PW_TERR_STATE 2u
#define PW_TERR_SESSION 3u
#define PW_TERR_OFFSET 4u
#define PW_TERR_CRC 5u
#define PW_TERR_RANGE 6u
#define PW_TERR_ACTION 7u
struct pw_transfer {
    uint8_t bytes[PW_TRANSFER_MAX];
    uint32_t session_id;
    uint32_t expected_crc;
    uint32_t total;
    uint32_t received;
    uint8_t active;
};
/* In-RAM only. Return response action, write its body to out and its length to out_len. */
unsigned pw_transfer_command(struct pw_transfer *s, unsigned action,
                             const uint8_t *data, unsigned len,
                             uint8_t out[16], unsigned *out_len);
#endif
