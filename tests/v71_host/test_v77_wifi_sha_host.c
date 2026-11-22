/* Portable host vectors for V7.7 32-byte single-block SHA256.
 * No ROM images, wireless hardware, Nintendo SDK or network APIs involved.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "walker_arm9_wifi_sig.h"

static int check(const uint8_t input[32], const char *hex) {
    uint8_t out[32];
    walkerSha256Fixed32(input, out);
    const char map[]="0123456789abcdef";
    for(unsigned i=0; i<32; i++){
        if(map[out[i]>>4] != hex[i*2] || map[out[i]&0x0f] != hex[i*2+1])
            return 0;
    }
    return 1;
}

int main(void) {
    uint8_t buf[32]={0};
    if(!check(buf,"66687aadf862bd776c8fc18b8e9f8e20089714856ee233b3902a591d0d5f2925")) {
        fprintf(stderr,"SHA256(zero32) mismatch\n"); return 1;
    }
    for(unsigned i=0; i<32; i++) buf[i]=(uint8_t)i;
    if(!check(buf,"630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd")) {
        fprintf(stderr,"SHA256(range32) mismatch\n"); return 2;
    }
    memset(buf,'A',32);
    if(!check(buf,"22a48051594c1949deed7040850c1f0f8764537f5191be56732d16a54c1d8153")) {
        fprintf(stderr,"SHA256('A'*32) mismatch\n"); return 3;
    }
    /* B4DS builds always fail closed; host test never reads game RAM. */
    if(walkerWifiCheckStaticCode()!=0) {
        fprintf(stderr,"B4DS radio signature reader must be disabled\n"); return 4;
    }
    puts("PASS: V7.7 SHA256 fixed-32 vectors and no-radio build gate");
    return 0;
}
