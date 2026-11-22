/* V7.7 fixed-32 byte CRC32 host vectors; no ROM or Wi-Fi involved. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "walker_arm9_wifi_sig.h"

int main(void) {
    uint8_t input[32]={0};
    if(walkerCrc32Fixed32(input)!=0x190a55adu) {
        fprintf(stderr,"CRC32(zero32) mismatch\n");return 1;
    }
    for(unsigned i=0;i<32;i++)input[i]=(uint8_t)i;
    if(walkerCrc32Fixed32(input)!=0x91267e8au) {
        fprintf(stderr,"CRC32(range32) mismatch\n");return 2;
    }
    memset(input,'A',32);
    if(walkerCrc32Fixed32(input)!=0xad316f1eu) {
        fprintf(stderr,"CRC32('A'*32) mismatch\n");return 3;
    }
    uint32_t out[WALKER_WIFI_SIG_COUNT]={1,1,1,1,1};
    if(walkerWifiCheckStaticCode(out)!=0) {
        fprintf(stderr,"B4DS must not scan NTR ARM9 addresses\n");return 4;
    }
    for(unsigned i=0;i<WALKER_WIFI_SIG_COUNT;i++) {
        if(out[i]!=0) {
            fprintf(stderr,"B4DS returned nonzero code CRC32\n");return 5;
        }
    }
    puts("PASS: V7.7 CRC32 fixed-32 vectors and disabled B4DS radio probe");
    return 0;
}
