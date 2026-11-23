package io.github.sdtransporter.pokewalker;

import java.io.*;
import java.util.Arrays;

/**
 * JDK-only wire-level regression test for the actual Android PWDSI001
 * encoder/decoder. It deliberately does not need Android SDK, a ROM, or a save.
 * The fixture is synthetic; this does NOT claim physical DSi connectivity.
 *
 * Run, from repository root:
 *   javac -d /tmp/pw-wire-test
 *     core/android/app/src/main/java/io/github/sdtransporter/pokewalker/DirectSyncProtocol.java
 *     core/tools/DirectSyncWireContractTest.java
 *   java -cp /tmp/pw-wire-test io.github.sdtransporter.pokewalker.DirectSyncWireContractTest
 */
public final class DirectSyncWireContractTest {
    private DirectSyncWireContractTest() {}

    private interface ThrowingTest { void run() throws Exception; }

    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }

    private static void expectIOException(ThrowingTest body, String name) throws Exception {
        try {
            body.run();
        } catch (IOException expected) {
            return;
        }
        throw new AssertionError("Expected IOException: " + name);
    }

    private static byte[] image() {
        byte[] bytes = new byte[DirectSyncProtocol.WALKER_SIZE];
        for (int i = 0; i < bytes.length; i++)
            bytes[i] = (byte) ((i * 73 + 19) & 0xff);
        return bytes;
    }

    private static String repeated(char value, int count) {
        char[] result = new char[count];
        Arrays.fill(result, value);
        return new String(result);
    }

    private static byte[] pushFrame(byte[] payload, String session, String trainer) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        DirectSyncProtocol.write(out, DirectSyncProtocol.OP_PUSH_TO_PHONE,
                session, trainer, payload, -1, null);
        return out.toByteArray();
    }

    public static void main(String[] args) throws Exception {
        final byte[] walker = image();
        final String session = repeated('a', 32);
        final String trainer = repeated('b', 36);
        byte[] frame = pushFrame(walker, session, trainer);
        check(frame.length == DirectSyncProtocol.HEADER + DirectSyncProtocol.WALKER_SIZE,
                "64 KiB walker must follow the 88-byte frame header");
        DirectSyncProtocol.Frame decoded = DirectSyncProtocol.read(new ByteArrayInputStream(frame));
        check(decoded.op == DirectSyncProtocol.OP_PUSH_TO_PHONE, "Wrong operation");
        check(decoded.length == 65536, "Wrong payload length");
        check(decoded.crc == DirectSyncProtocol.crc(walker), "Wrong CRC32");
        check(session.equals(decoded.session) && trainer.equals(decoded.trainer),
                "Session or trainer binding was lost");
        check(Arrays.equals(walker, decoded.payload), "Payload did not survive round trip");

        // TCP has no record boundaries: require readFully to handle tiny fragments.
        InputStream fragmented = new FilterInputStream(new ByteArrayInputStream(frame)) {
            @Override public int read(byte[] b, int off, int len) throws IOException {
                return super.read(b, off, Math.min(len, 7));
            }
        };
        check(Arrays.equals(walker, DirectSyncProtocol.read(fragmented).payload),
                "Fragmented TCP stream corrupted walker payload");

        byte[] damaged = frame.clone();
        damaged[DirectSyncProtocol.HEADER + 173] ^= 0x40;
        expectIOException(() -> DirectSyncProtocol.read(new ByteArrayInputStream(damaged)),
                "altered data must fail CRC");

        byte[] truncated = Arrays.copyOf(frame, frame.length - 1);
        expectIOException(() -> DirectSyncProtocol.read(new ByteArrayInputStream(truncated)),
                "truncated walker must fail");

        byte[] oversized = frame.clone();
        oversized[12] = 0;
        oversized[13] = 1;
        oversized[14] = 0;
        oversized[15] = 1; // 65537, greater than an EEPROM
        expectIOException(() -> DirectSyncProtocol.read(new ByteArrayInputStream(oversized)),
                "oversized walker must fail");

        ByteArrayOutputStream ackBytes = new ByteArrayOutputStream();
        DirectSyncProtocol.write(ackBytes, DirectSyncProtocol.OP_OK, session, trainer,
                null, -1, null);
        DirectSyncProtocol.Frame ack =
                DirectSyncProtocol.read(new ByteArrayInputStream(ackBytes.toByteArray()));
        check(ack.op == DirectSyncProtocol.OP_OK && ack.length == 0 &&
                ack.crc == 0 && session.equals(ack.session),
                "ACK frame does not match DSi session");

        if (args.length == 1 || args.length == 2) {
            /* Verify the actual bytes produced by walker_push_stream.c,
             * with its real 512-byte sender chunks and partial writes. */
            try (InputStream raw = new FileInputStream(args[0])) {
                DirectSyncProtocol.Frame fromC = DirectSyncProtocol.read(raw);
                check(fromC.op == DirectSyncProtocol.OP_PUSH_TO_PHONE,
                        "C sender used the wrong operation");
                check(fromC.length == DirectSyncProtocol.WALKER_SIZE,
                        "C sender payload length mismatch");
                check("0123456789abcdef0123456789abcdef".equals(fromC.session),
                        "C sender session was corrupted");
                check("0123456789abcdef0123456789abcdef0123".equals(fromC.trainer),
                        "C sender trainer was corrupted");
                check(fromC.crc == DirectSyncProtocol.crc(walker) &&
                      Arrays.equals(walker, fromC.payload),
                        "C sender bytes differ from Java protocol interpretation");
                check(raw.read() == -1, "C sender appended unexpected bytes");
            }
            System.out.println("PASS: real C sender wire frame decoded byte-for-byte by Android Java");
            if(args.length == 2) {
                /* Return the REAL Android-generated OP_OK bytes to the
                 * native C receiver for cross-language ACK validation. */
                try(OutputStream response=new FileOutputStream(args[1])) {
                    DirectSyncProtocol.write(response,DirectSyncProtocol.OP_OK,
                            "0123456789abcdef0123456789abcdef",
                            "0123456789abcdef0123456789abcdef0123",
                            null,-1,null);
                }
            }
        } else {
            check(args.length == 0,
                    "Usage: DirectSyncWireContractTest [c-frame.bin [android-ack.bin]]");
        }

        System.out.println("PASS: 64 KiB PUSH + CRC, fragmented TCP, corruption, length and ACK");
        System.out.println("LIMIT: protocol test only; no Wi-Fi/console or real Pokémon transfer tested");
    }
}
