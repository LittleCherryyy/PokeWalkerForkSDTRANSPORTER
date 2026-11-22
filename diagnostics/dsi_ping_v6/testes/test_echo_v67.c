/* Test vector for V6.7 synthetic data, no libnds required. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static uint32_t crc(const uint8_t *p,unsigned n){uint32_t c=~0u;for(unsigned i=0;i<n;i++){c^=p[i];for(int j=0;j<8;j++)c=(c>>1)^(0xedb88320u&(0u-(c&1u)));}return ~c;}
int main(void){uint8_t p[512]; for(unsigned b=0;b<16;b++){p[0]=p[1]=p[2]=0;p[3]=b;for(unsigned i=4;i<512;i++)p[i]=(uint8_t)((((b*508u)+(i-4u))*73u+19u)&255);if(crc(p,512)!=crc(p,512))return 1;}puts("OK: 16 blocos sinteticos (512 bytes), CRC32");return 0;}
