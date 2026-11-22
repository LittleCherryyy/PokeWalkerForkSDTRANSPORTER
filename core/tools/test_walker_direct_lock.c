/* Host-only regression of persistent direct-Pokewalker checkout fence.
 * It uses synthetic fields, not a real save or game image.
 * Compile:
 *   gcc -std=c99 -Wall -Wextra -Werror -I
 *     core/bootstrap/retail/common/include
 *     core/tools/test_walker_direct_lock.c -o /tmp/direct-lock-test
 */
#include <stdio.h>
#include <string.h>
#include "walker_direct_lock.h"

#define ASSERT(x) do { if(!(x)){fprintf(stderr,"FAIL %s line %d\n",#x,__LINE__);return 1;} } while(0)

int main(void){
    const char *session="0123456789abcdef0123456789abcdef";
    const char *trainer="0123456789abcdef0123456789abcdef0123";
    unsigned char sector[WALKER_LOCK_SIZE],saved[WALKER_LOCK_SIZE];

    walkerLockPrepared(sector);
    ASSERT(walkerLockDecode(sector)==WALKER_LOCK_PREPARED);
    ASSERT(sector[8]==0);
    ASSERT(walkerLockGet32(sector+508)==walkerLockCrc32(sector,508));

    ASSERT(walkerLockPending(sector,42,0x11223344u,session,trainer));
    ASSERT(walkerLockDecode(sector)==WALKER_LOCK_PENDING);
    ASSERT(sector[8]==1);
    ASSERT(walkerLockGet32(sector+12)==42u);
    ASSERT(walkerLockGet32(sector+16)==0x11223344u);
    ASSERT(memcmp(sector+20,session,32)==0);
    ASSERT(memcmp(sector+52,trainer,36)==0);

    FILE *file=tmpfile();
    ASSERT(file!=NULL);
    ASSERT(fwrite(sector,1,WALKER_LOCK_SIZE,file)==WALKER_LOCK_SIZE);
    ASSERT(fflush(file)==0 && fseek(file,0,SEEK_SET)==0);
    ASSERT(fread(saved,1,WALKER_LOCK_SIZE,file)==WALKER_LOCK_SIZE);
    ASSERT(fgetc(file)==EOF && !ferror(file));
    ASSERT(fclose(file)==0);
    ASSERT(!memcmp(sector,saved,WALKER_LOCK_SIZE));
    ASSERT(walkerLockDecode(saved)==WALKER_LOCK_PENDING);

    saved[65]^=0x20;
    ASSERT(walkerLockDecode(saved)<0);
    memcpy(saved,sector,WALKER_LOCK_SIZE);
    saved[8]=0; /* forged PREPARED status must not pass CRC */
    ASSERT(walkerLockDecode(saved)<0);
    memcpy(saved,sector,WALKER_LOCK_SIZE);
    saved[20]='z'; /* CRC rewrite still cannot bypass session validation */
    walkerLockPut32(saved+508,walkerLockCrc32(saved,508));
    ASSERT(walkerLockDecode(saved)<0);

    walkerLockPrepared(saved);
    ASSERT(walkerLockDecode(saved)==WALKER_LOCK_PREPARED);
    saved[100]=3;
    walkerLockPut32(saved+508,walkerLockCrc32(saved,508));
    ASSERT(walkerLockDecode(saved)<0); /* nonzero forged PREPARED payload */

    ASSERT(!walkerLockPending(saved,42,4u,"short",trainer));
    ASSERT(!walkerLockPending(saved,0,4u,session,trainer));
    ASSERT(walkerLockPending(saved,42,4u,session,""));
    ASSERT(walkerLockDecode(saved)==WALKER_LOCK_PENDING);

    puts("PASS: 512-byte prepared/pending lease, on-disk roundtrip, CRC, corrupt/replay fail-closed");
    puts("LIMIT: synthetic host test; no live SD hardware, Android Wi-Fi or console game");
    return 0;
}
