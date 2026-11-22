/* V7.2.6: native tests, no hardware reads. */
#include "walker_irq_live_guard.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    const uint32_t image=0x02380000u, length=0x000276D8u;
    const uint32_t table=0x0238ECF4u; /* user's photographed DSi value */
    assert(walkerIrqReadOnlyRangeOk(table,image,length,1));
    assert(table+24u*4u==0x0238ED54u);
    assert(!walkerIrqReadOnlyRangeOk(table,image,length,0));
    assert(!walkerIrqReadOnlyRangeOk(table,image,length,5));
    assert(!walkerIrqReadOnlyRangeOk(table+1u,image,length,1));
    assert(!walkerIrqReadOnlyRangeOk(image-4u,image,length,1));
    assert(!walkerIrqReadOnlyRangeOk(0x023FFFFCu,0x023FFF00u,0x100u,1));
    assert(!walkerIrqReadOnlyRangeOk(table,image,99u,1));
    assert(!walkerIrqReadOnlyRangeOk(table,image,table-image+99u,1));
    assert(!walkerIrqReadOnlyRangeOk(table,0x04000000u,length,1));
    assert(!walkerIrqReadOnlyRangeOk(table,0x01FFFFFFu,length,1));
    assert(!walkerIrqReadOnlyRangeOk(table,image,0xFFFFFFFFu,1));
    assert(!walkerIrqReadOnlyRangeOk(0xFFFFFFF0u,0xFFFFFF00u,0x500u,1));
    /* 100 bytes ending at exclusive RAM limit is valid, +4 is not. */
    assert(walkerIrqReadOnlyRangeOk(0x023FFF9Cu,image,0x80000u,4));
    assert(!walkerIrqReadOnlyRangeOk(0x023FFFA0u,image,0x80000u,4));
    puts("PASS V7.2.6: photo fits bounded RAM; invalid image/addresses fail closed");
    return 0;
}
