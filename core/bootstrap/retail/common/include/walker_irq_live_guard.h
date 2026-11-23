/* V7.2.6 bounded ARM7 IRQ word peek for the HeartGold boot table.
 * This pure header does not dereference memory, install handlers or enable Wi-Fi.
 * A successful guard is only a READ permission for exactly words 0,16,24;
 * it NEVER proves IRQ-table ownership, format or writable slots.
 */
#ifndef WALKER_IRQ_LIVE_GUARD_H
#define WALKER_IRQ_LIVE_GUARD_H
#include <stdint.h>

#define WALKER_IRQ_NTR_RAM_START 0x02000000u
#define WALKER_IRQ_NTR_RAM_END   0x02400000u
#define WALKER_IRQ_25_WORD_BYTES (25u * sizeof(uint32_t))

static inline int walkerIrqReadOnlyRangeOk(uint32_t tableAddr,
                                          uint32_t imageStart,
                                          uint32_t imageBytes,
                                          uint32_t method) {
    /* Table location must come from one of the four real bootloaderi paths.
     * In particular, a CACHED address has not been independently revalidated.
     * This function permits a bounded read, not any modification. */
    if (method < 1u || method > 4u) return 0;
    if ((tableAddr & 3u) || (imageStart & 3u)) return 0;
    if (imageStart < WALKER_IRQ_NTR_RAM_START ||
        imageStart >= WALKER_IRQ_NTR_RAM_END) return 0;
    if (imageBytes < WALKER_IRQ_25_WORD_BYTES ||
        imageBytes > WALKER_IRQ_NTR_RAM_END - imageStart) return 0;
    if (tableAddr < imageStart ||
        tableAddr > WALKER_IRQ_NTR_RAM_END-WALKER_IRQ_25_WORD_BYTES) return 0;
    if (tableAddr-imageStart > imageBytes-WALKER_IRQ_25_WORD_BYTES) return 0;
    return 1;
}
#endif
