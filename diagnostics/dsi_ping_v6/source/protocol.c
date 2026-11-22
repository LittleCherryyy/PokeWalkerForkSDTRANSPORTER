#include "protocol.h"
#include <string.h>
uint32_t pw_crc32(const uint8_t *p, size_t n) {
    uint32_t crc=0xffffffffu;
    for (size_t i=0;i<n;i++) {
        crc ^= p[i];
        for (unsigned j=0;j<8;j++) crc=(crc>>1) ^ (0xedb88320u & (uint32_t)-(int)(crc&1u));
    }
    return ~crc;
}
uint16_t pw_read_be16(const uint8_t *p) {return (uint16_t)((unsigned)p[0]<<8 | p[1]);}
uint32_t pw_read_be32(const uint8_t *p) {return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
void pw_write_be16(uint8_t *p, uint16_t v) {p[0]=(uint8_t)(v>>8);p[1]=(uint8_t)v;}
void pw_write_be32(uint8_t *p, uint32_t v) {p[0]=(uint8_t)(v>>24);p[1]=(uint8_t)(v>>16);p[2]=(uint8_t)(v>>8);p[3]=(uint8_t)v;}
int pw_parse_header(const uint8_t h[PW_HEADER_SIZE], unsigned *action, unsigned *payload_len, unsigned *crc) {
    if (memcmp(h,"PWDSI001",8)!=0) return -PW_ERR_MAGIC;
    if (h[8]!=PW_VERSION) return -PW_ERR_VERSION;
    unsigned len=pw_read_be16(h+10);
    if (len>PW_MAX_PAYLOAD) return -PW_ERR_SIZE;
    *action=h[9]; *payload_len=len; *crc=pw_read_be32(h+12);
    return 0;
}
void pw_write_header(uint8_t h[PW_HEADER_SIZE], unsigned action, const uint8_t *payload, unsigned length) {
    memcpy(h,"PWDSI001",8);h[8]=PW_VERSION;h[9]=(uint8_t)action;
    pw_write_be16(h+10,(uint16_t)length);
    pw_write_be32(h+12,pw_crc32(payload,length));
}
int pw_validate_integrity(const uint8_t h[PW_HEADER_SIZE], const uint8_t *payload, unsigned *action, unsigned *length) {
    unsigned crc=0;
    int e=pw_parse_header(h,action,length,&crc);
    if (e) return e;
    if (pw_crc32(payload,*length)!=crc) return -PW_ERR_CRC;
    return 0;
}
int pw_validate_packet(const uint8_t h[PW_HEADER_SIZE], const uint8_t *payload, unsigned *action, unsigned *length) {
    int e=pw_validate_integrity(h,payload,action,length);
    if (e) return e;
    return *action==PW_ACT_PING ? 0 : -PW_ERR_ACTION;
}
