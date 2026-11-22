package io.github.sdtransporter.pokewalker;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;

/** Uses the *actual* Android DirectSyncProtocol class on a desktop JVM.
 * No Android runtime, network, user profiles, or save data needed.
 */
public final class DirectSyncInteropTest {
    public static void main(String[] args) throws Exception {
        if(args.length != 2) throw new IllegalArgumentException("request and response file paths required");
        byte[] request=Files.readAllBytes(Path.of(args[0]));
        if(request.length != DirectSyncProtocol.HEADER)
            throw new AssertionError("C PING must be exactly 88 bytes");
        DirectSyncProtocol.Frame frame=DirectSyncProtocol.read(new ByteArrayInputStream(request));
        if(frame.op != DirectSyncProtocol.OP_PING ||
           frame.length != 0 || frame.crc != 0 || frame.flags != 0 ||
           !frame.session.isEmpty() || !frame.trainer.isEmpty()) {
            throw new AssertionError("Android decoder did not accept the C PING request");
        }
        ByteArrayOutputStream encoded=new ByteArrayOutputStream();
        DirectSyncProtocol.write(encoded, DirectSyncProtocol.OP_OK,
                                 frame.session,frame.trainer,null,-1,null);
        byte[] reply=encoded.toByteArray();
        if(reply.length!=88)throw new AssertionError("Expected an 88-byte OP_OK response");
        Files.write(Path.of(args[1]),reply);
        System.out.println("PASS V7.2 interoperability: C request decoded by real Android Java parser");
    }
}
