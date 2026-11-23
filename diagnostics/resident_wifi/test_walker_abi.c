#include <stddef.h>
#include <stdint.h>
#include <assert.h>
#include "walker_emu.h"
int main(void) {
    assert(offsetof(WalkerControl,dirty)==0x20u);
    assert(offsetof(WalkerControl,direct)>offsetof(WalkerControl,linkMode));
    assert(offsetof(WalkerControl,hgssNet)==offsetof(WalkerControl,direct)+sizeof(WalkerDirectBridge));
    assert(sizeof(WalkerControl)<=WALKER_BLOB_OFF-WALKER_CONTROL_OFF);
    assert(sizeof(WalkerDirectHeader)==88u);
    assert(sizeof(WalkerHgssNetApi)==20u*sizeof(uint32_t));
    return 0;
}
