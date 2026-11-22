package io.github.sdtransporter.pokewalker;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Local loopback only. Runs the actual framework-free Android wire protocol
 * for two PING exchanges: valid OP_OK and malicious transfer-opcode reply.
 * Does not link Android services, modify saves or send data to a phone.
 */
public final class LocalPingServerTest {
    private static void check(boolean value, String message) throws IOException {
        if (!value) throw new IOException(message);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("port file required");
        try (ServerSocket listener =
                new ServerSocket(0, 2, InetAddress.getLoopbackAddress())) {
            listener.setSoTimeout(7000);
            Files.writeString(Path.of(args[0]), Integer.toString(listener.getLocalPort()),
                    StandardCharsets.US_ASCII);
            for (int caseIndex = 0; caseIndex < 2; ++caseIndex) {
                try (Socket peer = listener.accept()) {
                    peer.setSoTimeout(5000);
                    DirectSyncProtocol.Frame request =
                            DirectSyncProtocol.read(peer.getInputStream());
                    check(request.op == DirectSyncProtocol.OP_PING, "PING opcode only");
                    check(request.length == 0 && request.flags == 0 && request.crc == 0,
                            "PING must carry no payload, flags or CRC");
                    check(request.session.isEmpty() && request.trainer.isEmpty(),
                            "PING must contain no save or trainer identity");
                    ByteArrayOutputStream encoded = new ByteArrayOutputStream();
                    // Case 2 deliberately sends a forbidden save-transfer opcode:
                    // the C firmware-side decoder must refuse it.
                    int replyOp = caseIndex == 0
                            ? DirectSyncProtocol.OP_OK
                            : DirectSyncProtocol.OP_PUSH_TO_PHONE;
                    DirectSyncProtocol.write(encoded, replyOp, "", "", null, -1, null);
                    byte[] response = encoded.toByteArray();
                    check(response.length == 88, "Only 88-byte reply headers allowed");
                    // Force TCP response fragmentation; one recv cannot be assumed
                    // to return a whole PWDSI001 header.
                    for (int offset = 0; offset < response.length; offset += 7) {
                        int length = Math.min(7, response.length - offset);
                        peer.getOutputStream().write(response, offset, length);
                        peer.getOutputStream().flush();
                        Thread.sleep(2);
                    }
                }
            }
            System.out.println("PASS: local Java protocol server checked two read-only PINGs");
        }
    }
}
