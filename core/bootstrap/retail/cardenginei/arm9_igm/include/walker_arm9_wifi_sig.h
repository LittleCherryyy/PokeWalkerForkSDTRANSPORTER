/* V7.7: fixed 32-byte ARM9 code CRC32 residency audit, no Wi-Fi calls. */
#ifndef WALKER_ARM9_WIFI_SIG_H
#define WALKER_ARM9_WIFI_SIG_H
#include <stdint.h>
#define WALKER_WIFI_SIG_COUNT 5u
#define WALKER_WIFI_SIG_ALL 0x1Fu
/* IEEE CRC32 of EXACTLY 32 bytes (same windows as V7.6 SHA256 report). */
uint32_t walkerCrc32Fixed32(const volatile uint8_t *source);
/* Writes CRC32 into out[5], returns bit mask for ARM entry prologues.
 * Does NOT establish a callable ABI or a working Wi-Fi interface. */
uint32_t walkerWifiCheckStaticCode(uint32_t out[WALKER_WIFI_SIG_COUNT]);
#endif
