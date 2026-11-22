#ifndef PW_UPLINK_H
#define PW_UPLINK_H
#include <stdint.h>
/* Returns 0 on successful authenticated server ACK, negative for transport/protocol error. */
int pw_uplink_ping(uint32_t server_be);
int pw_uplink_transfer(uint32_t server_be, unsigned total);
#endif
