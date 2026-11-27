package io.github.sdtransporter.pokewalker;

/** Ten-step LCD shade scale shared by the app and launcher widget. */
final class WalkerLcdPalette {
    private static final int[][] LIGHT = {
            {0xb4, 0xb7, 0xaa}, {0xa5, 0xa9, 0x9a},
            {0x8c, 0x91, 0x84}, {0x6a, 0x70, 0x64}};
    private static final int[][] DARK = {
            {0xb4, 0xb7, 0xaa}, {0x75, 0x7b, 0x6e},
            {0x35, 0x3e, 0x30}, {0x08, 0x0e, 0x06}};

    private WalkerLcdPalette() {}

    static int[] colors(int shade) {
        shade = Math.max(0, Math.min(9, shade));
        int[] colors = new int[4];
        for (int p = 0; p < 4; p++) {
            int r = blend(LIGHT[p][0], DARK[p][0], shade);
            int g = blend(LIGHT[p][1], DARK[p][1], shade);
            int b = blend(LIGHT[p][2], DARK[p][2], shade);
            colors[p] = 0xff000000 | r << 16 | g << 8 | b;
        }
        return colors;
    }

    private static int blend(int a, int b, int step) {
        return (a * (9 - step) + b * step + 4) / 9;
    }
}
