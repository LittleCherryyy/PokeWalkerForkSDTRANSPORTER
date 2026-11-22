package io.github.sdtransporter.pokewalker;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.zip.CRC32;

/** Compact transport used by the DSi nds-bootstrap direct-sync bridge. */
final class DirectSyncProtocol {
    static final byte[] MAGIC="PWDSI001".getBytes(StandardCharsets.US_ASCII);
    static final int VERSION=1;
    static final int PORT=30821;
    static final int HEADER=88;
    static final int WALKER_SIZE=65536;

    static final int OP_PUSH_TO_PHONE=1;   // DSi -> Android (checkout)
    static final int OP_PULL_FROM_PHONE=2; // Android -> DSi (return payload)
    static final int OP_CONFIRM_RETURN=3;  // DSi confirms durable write
    static final int OP_PING=4;
    static final int OP_OK=0x80;
    static final int OP_ERROR=0x7f;

    static final class Frame {
        int op,flags,length;
        long crc;
        String session="",trainer="";
        byte[] payload=new byte[0];
    }

    private DirectSyncProtocol(){}

    static long crc(byte[] data){CRC32 c=new CRC32();c.update(data);return c.getValue();}
    static String crcHex(byte[] data){return String.format(Locale.ROOT,"%08x",crc(data));}

    private static void putAscii(byte[] dst,int at,int length,String value) throws IOException {
        byte[] src=value==null?new byte[0]:value.getBytes(StandardCharsets.US_ASCII);
        if(src.length>length)throw new IOException("Direct sync field too long");
        System.arraycopy(src,0,dst,at,src.length);
    }
    private static String ascii(byte[] src,int at,int length){
        int used=0;while(used<length&&src[at+used]!=0)used++;
        return new String(src,at,used,StandardCharsets.US_ASCII);
    }
    private static int u16(byte[] b,int o){return (b[o]&255)<<8|(b[o+1]&255);}
    private static long u32(byte[] b,int o){return ((long)(b[o]&255)<<24)|((long)(b[o+1]&255)<<16)|((long)(b[o+2]&255)<<8)|(b[o+3]&255L);}
    private static void p16(byte[] b,int o,int v){b[o]=(byte)(v>>>8);b[o+1]=(byte)v;}
    private static void p32(byte[] b,int o,long v){b[o]=(byte)(v>>>24);b[o+1]=(byte)(v>>>16);b[o+2]=(byte)(v>>>8);b[o+3]=(byte)v;}

    static Frame read(InputStream raw) throws IOException {
        DataInputStream in=new DataInputStream(raw);
        byte[] h=new byte[HEADER];in.readFully(h);
        for(int i=0;i<MAGIC.length;i++)if(h[i]!=MAGIC[i])throw new IOException("Not an SD Transporter DSi sync client");
        if((h[8]&255)!=VERSION)throw new IOException("Unsupported DSi sync version");
        Frame f=new Frame();
        f.op=h[9]&255;f.flags=u16(h,10);f.length=(int)u32(h,12);f.crc=u32(h,16);
        f.session=ascii(h,20,32).toLowerCase(Locale.ROOT);f.trainer=ascii(h,52,36).toLowerCase(Locale.ROOT);
        if(f.length<0||f.length>WALKER_SIZE)throw new IOException("Invalid DSi sync payload length");
        if(f.length>0){f.payload=new byte[f.length];in.readFully(f.payload);if(crc(f.payload)!=f.crc)throw new IOException("DSi sync payload checksum mismatch");}
        return f;
    }

    static void write(OutputStream raw,int op,String session,String trainer,byte[] payload,long crcOverride,String error) throws IOException {
        byte[] body=payload==null?new byte[0]:payload;
        if(error!=null)body=error.getBytes(StandardCharsets.UTF_8);
        if(body.length>WALKER_SIZE)throw new IOException("Direct sync response too large");
        byte[] h=new byte[HEADER];System.arraycopy(MAGIC,0,h,0,MAGIC.length);h[8]=(byte)VERSION;h[9]=(byte)op;
        p16(h,10,0);p32(h,12,body.length);p32(h,16,crcOverride>=0?crcOverride:crc(body));
        putAscii(h,20,32,session==null?"":session);putAscii(h,52,36,trainer==null?"":trainer);
        BufferedOutputStream out=new BufferedOutputStream(raw);out.write(h);if(body.length>0)out.write(body);out.flush();
    }
}
