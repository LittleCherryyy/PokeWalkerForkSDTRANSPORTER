#include "../source/protocol.h"
#include "../source/transfer.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct pw_transfer st;
int main(void) {
    unsigned n; uint8_t out[16], a[12], chunk[13], id[4];
    uint8_t payload[]={10,20,30,40,50};
    assert(pw_crc32((const uint8_t*)"123456789",9)==0xcbf43926u);
    pw_write_be32(a,0x12345678); pw_write_be32(a+4,5);
    pw_write_be32(a+8,pw_crc32(payload,5));
    assert(pw_transfer_command(&st,PW_ACT_BEGIN,a,12,out,&n)==0x90 && n==12);
    assert(pw_transfer_command(&st,PW_ACT_BEGIN,a,12,out,&n)==0x7f); /* busy */
    memcpy(chunk,a,4);pw_write_be32(chunk+4,0);memcpy(chunk+8,payload,5);
    assert(pw_transfer_command(&st,PW_ACT_CHUNK,chunk,13,out,&n)==0x91);
    assert(pw_read_be32(out+4)==5);
    assert(pw_transfer_command(&st,PW_ACT_CHUNK,chunk,13,out,&n)==0x7f); /* replay */
    memcpy(id,a,4);
    assert(pw_transfer_command(&st,PW_ACT_COMMIT,id,4,out,&n)==0x92);
    assert(pw_read_be32(out+8)==pw_crc32(payload,5));
    assert(st.active==0);
    /* bad declared CRC: reject commit, do not write file */
    pw_write_be32(a+8,0);
    assert(pw_transfer_command(&st,PW_ACT_BEGIN,a,12,out,&n)==0x90);
    assert(pw_transfer_command(&st,PW_ACT_CHUNK,chunk,13,out,&n)==0x91);
    assert(pw_transfer_command(&st,PW_ACT_COMMIT,id,4,out,&n)==0x7f);
    assert(pw_read_be16(out)==PW_TERR_CRC && st.active==0);
    puts("OK: transfer unit tests (CRC, state, replay, commit)");
    return 0;
}
