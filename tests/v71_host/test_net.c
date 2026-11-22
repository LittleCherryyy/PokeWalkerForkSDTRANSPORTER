/* V7.1 host checks for shared layout and fail-closed resolver.
 * Uses zero game code/data, never a commercial ROM or a save.
 */
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "walker_emu.h"
#include "walker_ds_context.h"
#include "walker_hgss_net.h"

#define ALL_MISSING ((1u << 13) - 1u)

static void test_layout(void) {
    assert(offsetof(WalkerControl, dirty) == 0x20u);
    assert(offsetof(WalkerControl, linkMode) < offsetof(WalkerControl, direct));
    assert(offsetof(WalkerControl, direct) < offsetof(WalkerControl, hgssNet));
    assert(sizeof(WalkerControl) <= 0x800u);
    assert(sizeof(WalkerDirectHeader) == 88u);
}

static void test_invalid_inputs(void) {
    u32 arm9[1024] = {0};
    WalkerHgssNetApi n;
    assert(!walkerResolveHgssNet(arm9, 0x02000000u, sizeof(arm9), 0, "IPKE"));
    memset(&n, 0xff, sizeof(n));
    assert(!walkerResolveHgssNet(0, 0x02000000u, sizeof(arm9), &n, "IPKE"));
    assert(n.magic == WALKER_HGSS_NET_MAGIC);
    assert(n.ready == 0u);
    assert(walkerHgssNetMissingMask(&n) == ALL_MISSING);
    memset(&n, 0xff, sizeof(n));
    assert(!walkerResolveHgssNet(arm9, 0x02000000u, 0x100u, &n, "IPKE"));
    assert(n.ready == 0u);
    memset(&n, 0xff, sizeof(n));
    assert(!walkerResolveHgssNet(arm9, 0x02000001u, sizeof(arm9), &n, "IPKE"));
    assert(n.ready == 0u);
    assert(walkerHgssNetMissingMask(0) == ALL_MISSING);
    memset(&n, 0, sizeof(n));
    assert(walkerHgssNetMissingMask(&n) == ALL_MISSING);
}

static void test_title_gates(void) {
    u32 arm9[1024] = {0};
    WalkerHgssNetApi n;
    assert(walkerResolveHgssNet(arm9, 0x02000000u, sizeof(arm9), &n, "IPKE"));
    assert(n.soclGatewayPtr == 0x021D464Cu);
    assert(n.ready == 0u);
    assert(walkerHgssNetMissingMask(&n) == (ALL_MISSING & ~WALKER_NET_MISS_GATEWAY));
    assert(walkerResolveHgssNet(arm9, 0x02000000u, sizeof(arm9), &n, "IPGE"));
    assert(n.soclGatewayPtr == 0x021D464Cu);
    assert(n.ready == 0u);
    assert(walkerResolveHgssNet(arm9, 0x02000000u, sizeof(arm9), &n, "IPJE"));
    assert(n.soclGatewayPtr == 0u);
    assert(n.ready == 0u);
    assert(walkerResolveHgssNet(arm9, 0x02000000u, sizeof(arm9), &n, "ABCE"));
    assert(n.soclGatewayPtr == 0u);
    assert(n.ready == 0u);
}

static void test_mask_individual_slots(void) {
    WalkerHgssNetApi n;
    memset(&n, 0, sizeof(n));
    n.magic = WALKER_HGSS_NET_MAGIC;
    n.wcmInit=1; n.wcmStartupAsync=1; n.wcmBeginSearchAsync=1;
    n.wcmConnectAsync=1; n.wcmGetPhase=1; n.wcmPointApList=1;
    n.soclStartup=1; n.socSocket=1; n.socConnect=1;
    n.socRecv=1; n.socSend=1; n.socClose=1; n.soclGatewayPtr=1;
    assert(walkerHgssNetMissingMask(&n) == 0u);
    /* Presence of addresses alone must not flip the resolver-ready flag. */
    assert(n.ready == 0u);
    n.socSend=0;
    assert(walkerHgssNetMissingMask(&n) == WALKER_NET_MISS_SOC_SEND);
    n.socSend=1; n.wcmInit=0;
    assert(walkerHgssNetMissingMask(&n) == WALKER_NET_MISS_WCM_INIT);
}

int main(void) {
    test_layout();
    test_invalid_inputs();
    test_title_gates();
    test_mask_individual_slots();
    printf("PASS V7.1 host: layout, invalid input, title gates, missing-mask. Control size=%u bytes\n",
           (unsigned)sizeof(WalkerControl));
    return 0;
}
