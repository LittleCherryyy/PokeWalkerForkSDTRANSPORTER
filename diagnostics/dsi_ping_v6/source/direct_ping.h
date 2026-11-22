#ifndef PW_DIRECT_PING_H
#define PW_DIRECT_PING_H
#include <stdint.h>
typedef void (*pw_direct_progress_fn)(const char *phase, int code, int sock_errno);
/* Diagnostico RAM-only. Uma sessao TCP para multiplos PINGs;
   sem close() no cliente; reinicie o DSi apos o teste. */
int pw_direct_ping_persistent(uint32_t gateway, pw_direct_progress_fn cb);
int pw_direct_socket_errno(void);
int pw_direct_request_count(void);
unsigned pw_direct_echo_blocks(void);
unsigned pw_direct_echo_bytes(void);
int pw_direct_echo_persistent(uint32_t gateway, unsigned total, pw_direct_progress_fn cb);
int pw_direct_connection_alive(void);
#endif
