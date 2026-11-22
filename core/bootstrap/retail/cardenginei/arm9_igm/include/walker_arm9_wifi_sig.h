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
/* V8.3: read one HGSS USA Rev0 NitroSDK OS_IsThreadAvailable
 * global word, but ONLY after exact ARM instruction and literal
 * validation. Return 1 when sampled and 0 on failed guard.
 * Even when valid, does NOT establish an available OS thread slot. */
int walkerArm9ThreadAvailabilityRaw(uint32_t *out);
/* V8.6: two fixed, one-word read-only scheduler-related addresses,
 * only after V8.3's exact original code guard AND raw availability=1.
 * These are metadata words, NOT authenticated OSThread pointers.
 * Alias: 0x021E16A0+8 == 0x021E167C+44 == 0x021E16A8.
 * Return 0 if unsupported, 1 if both bounded words sampled. */
int walkerArm9ThreadAliasWords(uint32_t out[2]);
/* V8.7: four raw words at the fixed, suspected original HGSS
 * OSThreadInfo header (0x021E16A0..0x021E16AC). Requires V8.6 gate;
 * no indirection, no scheduler calls, no proven field names. */
int walkerArm9ThreadHeaderWords(uint32_t out[4]);
#endif
