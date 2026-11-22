/* Compile-only ABI checks for the appended, disabled V7.1 network state.
 * GPL-3.0-or-later. No ROM or game runtime dependency. */
#include "walker_emu.h"
typedef char walker_u32_size[(sizeof(unsigned int) == 4) ? 1 : -1];
typedef char walker_control_page[(sizeof(WalkerControl) <= 4096) ? 1 : -1];
typedef char walker_old_dirty_offset[
    (__builtin_offsetof(WalkerControl, dirty) == 0x20) ? 1 : -1
];
typedef char walker_new_fields_append[
    (__builtin_offsetof(WalkerControl, direct)
     > __builtin_offsetof(WalkerControl, linkMode)) ? 1 : -1
];
typedef char walker_net_api_fields[
    (sizeof(WalkerHgssNetApi) == 80) ? 1 : -1
];
int walkerV71LayoutBytes(void) { return sizeof(WalkerControl); }
