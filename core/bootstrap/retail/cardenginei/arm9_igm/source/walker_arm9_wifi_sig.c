/* Pokewalker V7.7: read-only ARM9 Wi-Fi code residency check.
 * 32-byte SHA256 fingerprints were verified on authentic HGSS USA Rev0
 * in the user's V7.6 report. This code never calls network functions,
 * changes IRQ state or writes any part of the game/save/Pokewalker.
 * GPL-3.0-or-later.
 */
#include "walker_arm9_wifi_sig.h"

/* SHA-256 specialized for exactly one 32-byte message. A single padded
 * 64-byte block is processed; there are no heap allocations or OS calls.
 * source is volatile because it is live ARM9 RAM, not a ROM buffer. */
static uint32_t ror32(uint32_t a, unsigned n) {
    return (a >> n) | (a << (32u - n));
}

void walkerSha256Fixed32(const volatile uint8_t *source, uint8_t digest[32]) {
    static const uint32_t k[64] = {
        0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,
        0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
        0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,
        0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
        0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,
        0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
        0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,
        0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
        0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,
        0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
        0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,
        0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
        0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,
        0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
        0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,
        0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
    };
    uint32_t w[64];
    for (unsigned i=0;i<8;i++) {
        unsigned j=i*4u;
        w[i]=((uint32_t)source[j]<<24)|((uint32_t)source[j+1]<<16)
            |((uint32_t)source[j+2]<<8)|source[j+3];
    }
    w[8]=0x80000000u;
    for (unsigned i=9;i<15;i++) w[i]=0u;
    w[15]=256u; /* 32 input bytes * 8 bits */
    for (unsigned i=16;i<64;i++) {
        uint32_t x=w[i-15], y=w[i-2];
        uint32_t s0=ror32(x,7)^ror32(x,18)^(x>>3);
        uint32_t s1=ror32(y,17)^ror32(y,19)^(y>>10);
        w[i]=w[i-16]+s0+w[i-7]+s1;
    }
    uint32_t a=0x6a09e667u,b=0xbb67ae85u,c=0x3c6ef372u,d=0xa54ff53au;
    uint32_t e=0x510e527fu,f=0x9b05688cu,g=0x1f83d9abu,h=0x5be0cd19u;
    for (unsigned i=0;i<64;i++) {
        uint32_t S1=ror32(e,6)^ror32(e,11)^ror32(e,25);
        uint32_t ch=(e&f)^(~e&g);
        uint32_t t1=h+S1+ch+k[i]+w[i];
        uint32_t S0=ror32(a,2)^ror32(a,13)^ror32(a,22);
        uint32_t maj=(a&b)^(a&c)^(b&c);
        uint32_t t2=S0+maj;
        h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
    }
    uint32_t result[8] = {
        0x6a09e667u+a,0xbb67ae85u+b,0x3c6ef372u+c,0xa54ff53au+d,
        0x510e527fu+e,0x9b05688cu+f,0x1f83d9abu+g,0x5be0cd19u+h
    };
    for (unsigned i=0;i<8;i++) {
        uint32_t v=result[i];
        digest[i*4]=(uint8_t)(v>>24);
        digest[i*4+1]=(uint8_t)(v>>16);
        digest[i*4+2]=(uint8_t)(v>>8);
        digest[i*4+3]=(uint8_t)v;
    }
}

uint32_t walkerWifiCheckStaticCode(void) {
#ifdef B4DS
    /* B4DS does not have this DSi NTR resident mapping. */
    return 0;
#else
    /* Index order:
     * 0 = WCM_Init, 1 = WCM_StartupAsync, 2 = WCM_GetPhase,
     * 3 = SOC_Socket, 4 = SOC_Connect.
     * Exact verified V7.6 32-byte SHA256 fingerprints, HGSS USA revision 0.
     */
    static const uint32_t location[WALKER_WIFI_SIG_COUNT] = {
        0x020AD850u,0x020AD9C0u,0x020AE420u,0x020A2EACu,0x020A2F04u
    };
    static const uint8_t expected[WALKER_WIFI_SIG_COUNT][32] = {
        {0x63,0x69,0xf7,0x49,0x47,0xb5,0x17,0x49,0xf4,0x1b,0x1d,0xc4,0x2d,0xb9,0xf0,0xd1,0x0e,0x98,0x9d,0x24,0x51,0x81,0x27,0x30,0x0e,0xa5,0x58,0x79,0x17,0x6a,0x89,0xfa},
        {0x20,0xaf,0x5f,0x8f,0x43,0xb8,0xfa,0x2f,0x1b,0x77,0x47,0xe1,0x15,0xb4,0x1b,0xda,0x5a,0x87,0x6f,0x34,0x06,0x34,0x1d,0xc5,0xcc,0xb7,0x8c,0x7f,0x7a,0xc8,0xda,0xc8},
        {0x50,0xa4,0x8e,0x8d,0x3c,0x36,0x05,0xad,0xc7,0xf1,0xe4,0x63,0x86,0x65,0x4e,0xc0,0x5e,0x1a,0x4f,0xa6,0xaf,0x16,0x3b,0xd4,0x0d,0x66,0x51,0x26,0xc2,0x2f,0x0a,0xff},
        {0x85,0x6f,0xb4,0x18,0x64,0x0b,0x96,0xd1,0x91,0xc3,0x4c,0x16,0xda,0x20,0x11,0xda,0x5f,0x10,0xda,0x49,0x9f,0xa4,0x2e,0xb1,0x78,0x52,0x41,0x36,0x4b,0x0e,0x3d,0xc0},
        {0xc0,0xc3,0x98,0x8e,0xa2,0xf7,0xf0,0xf1,0x99,0xd8,0xa5,0xc3,0x93,0x68,0x2f,0x17,0x49,0xd1,0x29,0x81,0x25,0x99,0xaa,0x66,0x61,0x1e,0x7a,0xa2,0x8f,0x36,0x42,0xff}
    };
    uint32_t matches=0;
    uint8_t digest[32];
    for (unsigned item=0; item<WALKER_WIFI_SIG_COUNT; item++) {
        uint32_t addr=location[item];
        /* Fixed, aligned and in ordinary 4-MiB NTR RAM. No table probing. */
        if ((addr & 3u) || addr < 0x02000000u ||
            addr > 0x02400000u-32u) continue;
        walkerSha256Fixed32((const volatile uint8_t *)(uintptr_t)addr,digest);
        unsigned difference=0;
        for (unsigned i=0;i<32;i++) difference|=(digest[i]^expected[item][i]);
        if (difference==0) matches|=(1u<<item);
    }
    return matches;
#endif
}
