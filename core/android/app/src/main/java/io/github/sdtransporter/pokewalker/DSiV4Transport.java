package io.github.sdtransporter.pokewalker;

import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.zip.CRC32;

/** Compatible with PokeWalker_DSi_V3_Transferencia/source/protocol.c and transfer.c.
 * Synthetic bytes only; never accesses actual Pokemon or saves. */
public final class DSiV4Transport {
    private static final byte[] MAGIC = {'P','W','D','S','I','0','0','1'};
    private static final int PORT=30821, MAX_PAYLOAD=1024;
    private final String host;
    public interface Progress { void update(String message, int completed, int total); }
    public DSiV4Transport(String host) { this.host=host; }
    public static int crc32(byte[] bytes) { CRC32 crc=new CRC32();crc.update(bytes);return (int)crc.getValue(); }
    private static byte[] ints(int... nums) { ByteBuffer b=ByteBuffer.allocate(nums.length*4).order(ByteOrder.BIG_ENDIAN);for(int n:nums)b.putInt(n);return b.array(); }
    private static int word(byte[] b,int offset) {return ByteBuffer.wrap(b,offset,4).order(ByteOrder.BIG_ENDIAN).getInt();}
    private static void readFully(InputStream in, byte[] dest) throws IOException {
        int offset=0;
        while(offset<dest.length){int count=in.read(dest,offset,dest.length-offset);if(count<0)throw new EOFException("Conexao fechada antes da resposta completa");offset+=count;}
    }
    private static String hex(int value) {return String.format(java.util.Locale.US,"%08x",value);}
    public byte[] request(int action,byte[] payload) throws IOException {return request(action,payload,false);}
    public byte[] request(int action,byte[] payload, boolean damageCrc) throws IOException {
        if(payload.length>MAX_PAYLOAD)throw new IOException("Pacote maior que 1024 bytes");
        ByteBuffer b=ByteBuffer.allocate(16+payload.length).order(ByteOrder.BIG_ENDIAN);
        b.put(MAGIC).put((byte)1).put((byte)action).putShort((short)payload.length).putInt(crc32(payload)).put(payload);
        byte[] outgoing=b.array();if(damageCrc)outgoing[12]^=1;
        try(Socket socket=new Socket()) {
            socket.connect(new InetSocketAddress(host,PORT),5000);
            socket.setSoTimeout(6000);
            OutputStream os=socket.getOutputStream();os.write(outgoing);os.flush();
            InputStream is=socket.getInputStream();
            byte[] header=new byte[16];readFully(is,header);
            for(int i=0;i<MAGIC.length;i++)if(header[i]!=MAGIC[i])throw new IOException("Magic da resposta invalido");
            if((header[8]&255)!=1)throw new IOException("Versao binaria inesperada");
            int responseAction=header[9]&255;
            int count=((header[10]&255)<<8)|(header[11]&255);
            if(count>MAX_PAYLOAD)throw new IOException("Resposta excedeu limite do protocolo");
            byte[] data=new byte[count];readFully(is,data);
            int crc=word(header,12);
            if(crc32(data)!=crc)throw new IOException("CRC32 de resposta invalido");
            if(damageCrc)throw new IOException("DSi respondeu a quadro propositalmente corrompido");
            if(responseAction==0x7f){
                int code=data.length==2?((data[0]&255)<<8)|(data[1]&255):-1;
                throw new IOException("DSi rejeitou comando 0x"+Integer.toHexString(action)+"; codigo V3 "+code);
            }
            if(responseAction!=(action|0x80))throw new IOException("Acao de resposta inesperada: 0x"+Integer.toHexString(responseAction));
            return data;
        }
    }
    public boolean testCorrupt() throws IOException {
        try {
            request(0x04,"teste-corrompido".getBytes(java.nio.charset.StandardCharsets.US_ASCII),true);
            return false;
        }catch(EOFException expected){return true;}
        catch(java.net.SocketTimeoutException expected){return true;}
        catch(java.net.SocketException expected){return true;}
    }
    public String ping() throws IOException {
        byte[] sent="V4-ANDROID-PING".getBytes(java.nio.charset.StandardCharsets.US_ASCII);
        byte[] response=request(0x04,sent);
        if(!Arrays.equals(sent,response))throw new IOException("PONG difere do PING");
        return "PONG valido ("+response.length+" bytes)";
    }
    public String transfer(int total,int chunk,Progress progress) throws IOException {
        if(total<1||total>8192||chunk<1||chunk>512)throw new IOException("Parametros fora do limite V3");
        byte[] data=new byte[total];for(int i=0;i<total;i++)data[i]=(byte)((i*73+19)&255);
        int crc=crc32(data),session=new SecureRandom().nextInt();if(session==0)session=1;
        byte[] result=request(0x10,ints(session,total,crc));
        if(result.length!=12||word(result,0)!=session||word(result,4)!=total||word(result,8)!=512)
            throw new IOException("Resposta BEGIN invalida");
        boolean committed=false;
        try {
            for(int offset=0;offset<total;){
                int len=Math.min(Math.min(chunk,512),total-offset);
                byte[] payload=ByteBuffer.allocate(8+len).order(ByteOrder.BIG_ENDIAN)
                    .putInt(session).putInt(offset).put(data,offset,len).array();
                result=request(0x11,payload);
                if(result.length!=8||word(result,0)!=session||word(result,4)!=offset+len)
                    throw new IOException("ACK inesperado no bloco "+offset);
                offset+=len;
                if(progress!=null)progress.update("Confirmado "+offset+"/"+total+" bytes",offset,total);
            }
            result=request(0x12,ints(session));
            if(result.length!=12||word(result,0)!=session||word(result,4)!=total||word(result,8)!=crc)
                throw new IOException("COMMIT/CRC32 da transferencia divergiu");
            committed=true;
            return "Transferencia concluida: "+total+" bytes, CRC32 "+hex(crc)+" validado pelo DSi";
        } finally {
            if(!committed)try {request(0x13,ints(session));}catch(IOException ignored){}
        }
    }
}
