#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "walker_directsync.h"
int main(void) {
    WalkerDirectHeader h;
    memset(&h,0,sizeof(h));
    memcpy(h.magic,WALKER_DIRECT_MAGIC,WALKER_DIRECT_MAGIC_SIZE);
    h.version=WALKER_DIRECT_VERSION;
    h.op=WALKER_DIRECT_PING;
    walkerDirectPut16(h.flagsBE,0x1234);
    walkerDirectPut32(h.payloadLengthBE,0x01020304);
    walkerDirectPut32(h.crc32BE,0xedb88320);
    assert(sizeof(h)==88);
    assert(memcmp(h.magic,"PWDSI001",8)==0);
    assert(h.version==1 && h.op==4);
    assert(walkerDirectBe16(h.flagsBE)==0x1234);
    assert(walkerDirectBe32(h.payloadLengthBE)==0x01020304);
    assert(walkerDirectBe32(h.crc32BE)==0xedb88320);
    return 0;
}
