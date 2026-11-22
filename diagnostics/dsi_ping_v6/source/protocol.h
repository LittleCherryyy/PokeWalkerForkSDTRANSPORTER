#ifndef PW_PROTOCOL_H
#define PW_PROTOCOL_H
#include <stddef.h>
#include <stdint.h>
#define PW_HEADER_SIZE 16u
#define PW_MAX_PAYLOAD 1024u
#define PW_VERSION 1u
#define PW_ACT_PING 4u
#define PW_ACT_PONG 0x84u
#define PW_ACT_ERROR 0x7fu
#define PW_ERR_MAGIC 1
#define PW_ERR_VERSION 2
#define PW_ERR_SIZE 3
#define PW_ERR_CRC 4
#define PW_ERR_ACTION 5
uint32_t pw_crc32(const uint8_t *p, size_t n);
uint16_t pw_read_be16(const uint8_t *p);
uint32_t pw_read_be32(const uint8_t *p);
void pw_write_be16(uint8_t *p, uint16_t v);
void pw_write_be32(uint8_t *p, uint32_t v);
int pw_parse_header(const uint8_t h[PW_HEADER_SIZE], unsigned *action, unsigned *payload_len, unsigned *crc);
void pw_write_header(uint8_t h[PW_HEADER_SIZE], unsigned action, const uint8_t *payload, unsigned length);
int pw_validate_integrity(const uint8_t h[PW_HEADER_SIZE], const uint8_t *payload, unsigned *action, unsigned *length);
int pw_validate_packet(const uint8_t h[PW_HEADER_SIZE], const uint8_t *payload, unsigned *action, unsigned *length);
#endif
