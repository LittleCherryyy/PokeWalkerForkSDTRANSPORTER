/* V7.7 read-only ARM9 code residency fingerprint; does NOT call Wi-Fi. */
#ifndef WALKER_ARM9_WIFI_SIG_H
#define WALKER_ARM9_WIFI_SIG_H
#include <stdint.h>
#define WALKER_WIFI_SIG_COUNT 5u
#define WALKER_WIFI_SIG_ALL 0x1Fu
/* Digest of EXACTLY 32 memory bytes, the same window used by V7.6. */
void walkerSha256Fixed32(const volatile uint8_t *source, uint8_t digest[32]);
/* Bit i means a matching 32-byte code signature; no network readiness proof. */
uint32_t walkerWifiCheckStaticCode(void);
#endif
