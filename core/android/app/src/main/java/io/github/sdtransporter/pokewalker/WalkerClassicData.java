package io.github.sdtransporter.pokewalker;

import java.util.Calendar;
import java.util.Arrays;

/** Runtime-only support for rendering the empty Pokewalker menu. */
final class WalkerClassicData {
    private static final byte[] EMPTY = new byte[65536];
    static {
        Arrays.fill(EMPTY, (byte) 0xff);
    }

    private WalkerClassicData() {}

    static byte[] image(WalkerStore store) {
        // Empty profiles still need a valid native image, but never let a
        // menu/widget mutate the shared template used by other profiles.
        return store != null && store.data != null ? store.data : EMPTY.clone();
    }

    static int secondsOfDay() {
        Calendar now = Calendar.getInstance();
        return now.get(Calendar.HOUR_OF_DAY) * 3600
                + now.get(Calendar.MINUTE) * 60
                + now.get(Calendar.SECOND);
    }
}
