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
    const uint32_t candidate = 0x021E1688u; /* fixed after literal guard */
    if ((candidate & 3u) || candidate < 0x02000000u ||
        candidate > 0x02400000u - 4u)
        return 0;
    *out = *(const volatile uint32_t *)(uintptr_t)candidate;
    return 1;
#endif
}

/* V8.6 — opt-in, read-only fixed RAM word probe.
 * Both words are in the NTR main RAM region and correspond to original
 * static HGSS US Rev0 one-step references, identical in HG/SS:
 *
 * 021E16A4 = 021E16A0 + 4  (20 static read xrefs)
 * 021E16A8 = 021E16A0 + 8  (4 static read xrefs)
 *          = 021E167C +44  (1 static read + 3 writes)
 *
 * Their actual types and runtime owners are UNKNOWN.  Never follow the
 * sampled values as pointers or infer active threads from their values.
 * The exact V8.3 OS_IsThreadAvailable original code gate is mandatory.
 */
int walkerArm9ThreadAliasWords(uint32_t out[2]) {
    if (!out) return 0;
    out[0]=0u;
    out[1]=0u;
#if defined(B4DS) || defined(TWLSDK)
    return 0;
#else
    uint32_t enabled=0u;
    if (!walkerArm9ThreadAvailabilityRaw(&enabled) || enabled!=1u)
        return 0;
    out[0]=*(const volatile uint32_t *)(uintptr_t)0x021E16A4u;
    out[1]=*(const volatile uint32_t *)(uintptr_t)0x021E16A8u;
    return 1;
#endif
}

/* V8.7 original HGSS USA Rev0 fixed RAM header comparison.
 * Reuses the previously validated V8.6 2-word snapshot and V8.3
 * exact 4-word instruction guard. Additional reads are ONLY A0+0
 * and A0+C, two aligned known NTR main-RAM addresses. The words
 * at +4 and +8 are reused from the V8.6 snapshot: no duplicate
 * volatile reads of those potentially scheduler-owned words.
 * Do not interpret contents as pointers or follow them here.
 */
int walkerArm9ThreadHeaderWords(uint32_t out[4]) {
    if (!out) return 0;
    out[0]=0u;
    out[1]=0u;
    out[2]=0u;
    out[3]=0u;
#if defined(B4DS) || defined(TWLSDK)
    return 0;
#else
    uint32_t pair[2]={0u,0u};
    if (!walkerArm9ThreadAliasWords(pair))
        return 0;
    out[0]=*(const volatile uint32_t *)(uintptr_t)0x021E16A0u;
    out[1]=pair[0];
    out[2]=pair[1];
    out[3]=*(const volatile uint32_t *)(uintptr_t)0x021E16ACu;
    return 1;
#endif
}

/* V8.8: test the SDK 2.x *legacy* layout hypothesis, not Infinity.
 * The original HGSS build targets NitroSDK 2.0; the public thread.h
 * only enables SDK_THREAD_INFINITY for SDK_VERSION_MAJOR >= 3.
 * An original legacy OSThreadInfo at 0x021E169C would place:
 *   +0 header flags/max_entry  = 0x021E169C (NEW)
 *   +4 irqDepth/padding        = 0x021E16A0 (reused)
 *   +8 current                 = 0x021E16A4 (reused)
 *  +12 list                    = 0x021E16A8 (reused)
 *  +16 switchCallback          = 0x021E16AC (reused)
 *  +20 entry[0]                = 0x021E16B0 (NEW)
 * All values are RAW and never interpreted as pointers by this code.
 * Reject changed previously observed original HGSS pointer pair:
 * this is a narrowly scoped diagnostic, not a general-purpose RAM
 * scanner. Two new fixed aligned NTR memory word reads only.
 */
int walkerArm9LegacyThreadInfoWords(uint32_t out[6]) {
    if (!out) return 0;
    for (unsigned i=0;i<6;i++) out[i]=0u;
#if defined(B4DS) || defined(TWLSDK)
    return 0;
#else
    uint32_t middle[4]={0u,0u,0u,0u};
    if (!walkerArm9ThreadHeaderWords(middle))
        return 0;
    if (middle[1]!=0x021E1770u || middle[2]!=0x021E3864u)
        return 0;
    out[0]=*(const volatile uint32_t *)(uintptr_t)0x021E169Cu;
    out[1]=middle[0];
    out[2]=middle[1];
    out[3]=middle[2];
    out[4]=middle[3];
    out[5]=*(const volatile uint32_t *)(uintptr_t)0x021E16B0u;
    return 1;
#endif
}
