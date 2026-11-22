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
    uint32_t schedulerRaw=0xffffffffu;
    if(walkerArm9ThreadAvailabilityRaw(&schedulerRaw)!=0 || schedulerRaw!=0u) {
        fprintf(stderr,"B4DS scheduler live probe must fail closed\\n");return 6;
    }
    if(walkerArm9ThreadAvailabilityRaw(NULL)!=0) {
        fprintf(stderr,"NULL scheduler probe output must fail closed\\n");return 7;
    }
    uint32_t aliasWords[2]={0xffffffffu,0xffffffffu};
    if(walkerArm9ThreadAliasWords(aliasWords)!=0 ||
        aliasWords[0]!=0u || aliasWords[1]!=0u) {
        fprintf(stderr,"B4DS must not sample HGSS ARM9 alias RAM\\n");return 8;
    }
    if(walkerArm9ThreadAliasWords(NULL)!=0) {
        fprintf(stderr,"NULL alias output must fail closed\\n");return 9;
    }
    uint32_t header[4]={1u,2u,3u,4u};
    if (walkerArm9ThreadHeaderWords(header)!=0 ||
        header[0]!=0u || header[1]!=0u ||
        header[2]!=0u || header[3]!=0u) {
        fprintf(stderr,"B4DS must refuse full HGSS OS thread header\\n");return 10;
    }
    if (walkerArm9ThreadHeaderWords(NULL)!=0) {
        fprintf(stderr,"NULL header pointer must fail closed\\n");return 11;
    }
    puts("PASS: V7.7 CRC32, V8.3 flag, V8.6 alias and V8.7 disabled B4DS header");
    return 0;
}
