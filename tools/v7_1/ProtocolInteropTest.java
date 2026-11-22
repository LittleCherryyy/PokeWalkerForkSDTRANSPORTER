package io.github.sdtransporter.pokewalker;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/** Host-JVM validation of Android direct-sync framing; no ROM, network or save access. */
public final class ProtocolInteropTest {
    private static void check(boolean value, String detail) {
        if (!value) throw new AssertionError(detail);
    }

    private static byte[] encoded(int op, String session, String trainer, byte[] data) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        DirectSyncProtocol.write(out, op, session, trainer, data, -1, null);
        return out.toByteArray();
    }

    private static void rejects(byte[] data, String message) throws IOException {
        boolean rejected = false;
        try { DirectSyncProtocol.read(new ByteArrayInputStream(data)); }
        catch (IOException expected) { rejected = true; }
        check(rejected, message);
    }

    public static void main(String[] args) throws Exception {
        check(DirectSyncProtocol.HEADER == 88, "88-byte bridge header");
        check(DirectSyncProtocol.PORT == 30821, "bridge TCP port");
        check(DirectSyncProtocol.OP_PING == 4, "PING opcode");
        check(DirectSyncProtocol.OP_OK == 128, "OK opcode");

        byte[] ping = encoded(DirectSyncProtocol.OP_PING, "", "", null);
        check(ping.length == 88, "PING must not have a payload");
        check(new String(ping, 0, 8, StandardCharsets.US_ASCII).equals("PWDSI001"), "magic");
        check((ping[8] & 255) == 1 && (ping[9] & 255) == 4, "version/opcode");
        for (int i=10; i<88; i++) check(ping[i] == 0, "empty PING trailing fields");
        DirectSyncProtocol.Frame parsedPing = DirectSyncProtocol.read(new ByteArrayInputStream(ping));
        check(parsedPing.length == 0 && parsedPing.op == 4, "PING readback");

        byte[] block = new byte[512];
        for (int i=0; i<block.length; i++) block[i] = (byte)((i*73+19)&255);
        String session = "0123456789abcdef0123456789abcdef";
        String trainer = "0123456789abcdef0123456789abcdef1234";
        byte[] data = encoded(DirectSyncProtocol.OP_TEST_ECHO, session, trainer, block);
        check(data.length == 600, "88-byte header + 512 payload");
        check((data[12]&255)==0 && (data[13]&255)==0 && (data[14]&255)==2 && (data[15]&255)==0,
              "payload size big endian at 12");
        DirectSyncProtocol.Frame parsed = DirectSyncProtocol.read(new ByteArrayInputStream(data));
        check(parsed.op == 5 && parsed.length == 512 && parsed.crc == DirectSyncProtocol.crc(block),
              "payload CRC and metadata");
        check(parsed.session.equals(session) && parsed.trainer.equals(trainer), "session/trainer");
        check(Arrays.equals(parsed.payload, block), "binary round trip");

        byte[] badCrc = data.clone(); badCrc[88] ^= 1;
        rejects(badCrc, "corrupted payload must be rejected");
        byte[] badMagic = ping.clone(); badMagic[0] = 0;
        rejects(badMagic, "bad magic must be rejected");
        byte[] badVersion = ping.clone(); badVersion[8] = 2;
        rejects(badVersion, "bad version must be rejected");
        byte[] tooLong = ping.clone(); tooLong[12]=0; tooLong[13]=1; tooLong[14]=0; tooLong[15]=1;
        rejects(tooLong, "oversized payload must be rejected");
        rejects(Arrays.copyOf(ping, 87), "truncated frame must be rejected");

        System.out.println("ProtocolInteropTest: PASS (Android 88-byte framing, CRC and rejection checks)");
    }
}
