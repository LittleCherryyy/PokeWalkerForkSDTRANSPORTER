#include "transfer.h"
#include "protocol.h"
#include <string.h>

static unsigned failure(uint8_t out[16], unsigned *out_len, unsigned code) {
    pw_write_be16(out, (uint16_t)code);
    *out_len = 2;
    return PW_ACT_ERROR;
}
unsigned pw_transfer_command(struct pw_transfer *s, unsigned action,
                             const uint8_t *data, unsigned len,
                             uint8_t out[16], unsigned *out_len) {
    *out_len = 0;
    if (action == PW_ACT_BEGIN) {
        if (len != 12) return failure(out,out_len,PW_TERR_LENGTH);
        uint32_t id=pw_read_be32(data), total=pw_read_be32(data+4);
        uint32_t expected=pw_read_be32(data+8);
        if (id==0 || total==0 || total>PW_TRANSFER_MAX) return failure(out,out_len,PW_TERR_RANGE);
        /* Never overwrite an in-progress transfer. */
        if (s->active) return failure(out,out_len,PW_TERR_STATE);
        s->session_id=id; s->total=total; s->expected_crc=expected;
        s->received=0; s->active=1;
        pw_write_be32(out,id);pw_write_be32(out+4,total);pw_write_be32(out+8,PW_CHUNK_MAX);
        *out_len=12; return PW_ACT_BEGIN|0x80u;
    }
    if (action == PW_ACT_ABORT) {
        if(len!=4) return failure(out,out_len,PW_TERR_LENGTH);
        if(!s->active) return failure(out,out_len,PW_TERR_STATE);
        uint32_t id=pw_read_be32(data);
        if(id!=s->session_id) return failure(out,out_len,PW_TERR_SESSION);
        s->active=0;s->received=0;s->total=0;s->expected_crc=0;s->session_id=0;
        pw_write_be32(out,id); *out_len=4;return PW_ACT_ABORT|0x80u;
    }
    if (action == PW_ACT_CHUNK) {
        if(len<9 || len>8+PW_CHUNK_MAX) return failure(out,out_len,PW_TERR_LENGTH);
        if(!s->active) return failure(out,out_len,PW_TERR_STATE);
        uint32_t id=pw_read_be32(data),offset=pw_read_be32(data+4);
        if(id!=s->session_id) return failure(out,out_len,PW_TERR_SESSION);
        if(offset!=s->received) return failure(out,out_len,PW_TERR_OFFSET);
        unsigned bytes=len-8;
        if(bytes>s->total-s->received) return failure(out,out_len,PW_TERR_RANGE);
        memcpy(s->bytes+s->received,data+8,bytes);
        s->received+=bytes;
        pw_write_be32(out,id);pw_write_be32(out+4,s->received);
        *out_len=8;return PW_ACT_CHUNK|0x80u;
    }
    if (action == PW_ACT_COMMIT) {
        if(len!=4) return failure(out,out_len,PW_TERR_LENGTH);
        if(!s->active) return failure(out,out_len,PW_TERR_STATE);
        uint32_t id=pw_read_be32(data);
        if(id!=s->session_id) return failure(out,out_len,PW_TERR_SESSION);
        if(s->received!=s->total) return failure(out,out_len,PW_TERR_LENGTH);
        uint32_t actual=pw_crc32(s->bytes,s->total);
        if(actual!=s->expected_crc) {
            /* Abort mismatch to avoid an unusable active session. */
            s->active=0;return failure(out,out_len,PW_TERR_CRC);
        }
        pw_write_be32(out,id);pw_write_be32(out+4,s->total);pw_write_be32(out+8,actual);
        *out_len=12;
        s->active=0; /* No file/save modifications. Memory is reused next session. */
        return PW_ACT_COMMIT|0x80u;
    }
    return failure(out,out_len,PW_TERR_ACTION);
}
