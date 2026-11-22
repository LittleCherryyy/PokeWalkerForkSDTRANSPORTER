/* V7.7 read-only live ARM9 code-window CRC32 verification.
 * The user separately verified exact 32-byte SHA256s on the USA Rev0
 * HGSS ROMs in V7.6. This small runtime CRC32 produces an independent
 * fingerprint of the same RAM window for comparison with an offline ROM
 * reference. Does not invoke WCM/SOC, use IRQ, or access save files.
 * GPL-3.0-or-later.
 */
#include "walker_arm9_wifi_sig.h"

uint32_t walkerCrc32Fixed32(const volatile uint8_t *source) {
    uint32_t crc=0xffffffffu;
    for(unsigned i=0;i<32;i++) {
        crc ^= source[i];
        for(unsigned bit=0;bit<8;bit++) {
            crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
        }
    }
    return ~crc;
}

uint32_t walkerWifiCheckStaticCode(uint32_t out[WALKER_WIFI_SIG_COUNT]) {
    if(!out) return 0u;
#ifdef B4DS
    for(unsigned i=0;i<WALKER_WIFI_SIG_COUNT;i++) out[i]=0u;
    return 0u;
#else
    /* Original US HGSS Rev0 V7.5/WCM-SOC callsite destinations.
     * 0 WCM_Init, 1 WCM_StartupAsync, 2 WCM_GetPhase,
     * 3 SOC_Socket, 4 SOC_Connect. Runtime signatures are not
     * automatically compared to a reference: user verifies offline CRCs.
     */
    static const uint32_t address[WALKER_WIFI_SIG_COUNT] = {
        0x020AD850u,0x020AD9C0u,0x020AE420u,0x020A2EACu,0x020A2F04u
    };
    uint32_t entryMask=0u;
    for(unsigned i=0;i<WALKER_WIFI_SIG_COUNT;i++) {
        const uint32_t a=address[i];
        if((a&3u)!=0 || a<0x02000000u || a>0x02400000u-32u) {
            out[i]=0u;
            continue;
        }
        const volatile uint8_t *p=(const volatile uint8_t *)(uintptr_t)a;
        const uint32_t first=*(const volatile uint32_t *)(uintptr_t)a;
        out[i]=walkerCrc32Fixed32(p);
        /* Plausible ARM 'STMDB sp!,{regs}' opening from V7.6, NOT ABI proof. */
        if((first & 0xffff0000u)==0xe92d0000u)
            entryMask |= 1u<<i;
    }
    return entryMask;
#endif
}

/* V8.3 HGSS USA Rev0 only; derived from the user's matching V8.2 report.
 *
 * 020D1AC4  LDR r0, [pc,#4]       literal at 020D1AD0
 * 020D1AC8  LDR r0, [r0]          single data read
 * 020D1ACC  BX  lr                return
 * 020D1AD0  .word 021E1688       original NTR RAM global
 *
 * Read the fixed original instruction sequence and literal first.  A
 * mismatch is a hard no-read condition. The global is read only once,
 * with no pointer chasing, loop, mutating operation, or OS API call.
 * This value is returned as RAW DATA; it is NOT evidence of a healthy
 * scheduler, available OSThread storage, or permission to create threads.
 */
int walkerArm9ThreadAvailabilityRaw(uint32_t *out) {
    if (!out) return 0;
    *out = 0u;
#if defined(B4DS) || defined(TWLSDK)
    return 0;
#else
    const volatile uint32_t * const code =
        (const volatile uint32_t *)(uintptr_t)0x020D1AC4u;
    if (code[0] != 0xE59F0004u ||
        code[1] != 0xE5900000u ||
        code[2] != 0xE12FFF1Eu ||
        code[3] != 0x021E1688u)
        return 0;
    const uint32_t candidate = code[3];
    if ((candidate & 3u) || candidate < 0x02000000u ||
        candidate > 0x02400000u - 4u)
        return 0;
    *out = *(const volatile uint32_t *)(uintptr_t)candidate;
    return 1;
#endif
}
