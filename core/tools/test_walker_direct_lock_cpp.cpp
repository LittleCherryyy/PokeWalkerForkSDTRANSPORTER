/* The real launcher uses walker_direct_lock.h as C++ code.
 * This host-only check catches language/ABI mistakes without devkitARM.
 */
#include <string>
#include <cstdio>
#include "walker_direct_lock.h"
int main() {
    unsigned char record[WALKER_LOCK_SIZE];
    walkerLockPrepared(record);
    if(walkerLockDecode(record)!=WALKER_LOCK_PREPARED)return 1;
    const std::string session="0123456789abcdef0123456789abcdef";
    if(!walkerLockPending(record,8,0xabcdef01u,session.c_str(),""))return 2;
    if(walkerLockDecode(record)!=WALKER_LOCK_PENDING)return 3;
    std::puts("PASS: launcher C++ decodes the same 512-byte durable ownership marker");
    return 0;
}
