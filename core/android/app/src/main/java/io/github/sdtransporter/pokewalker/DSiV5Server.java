package io.github.sdtransporter.pokewalker;

import java.io.*;
import java.net.*;
import java.nio.*;
import java.util.Arrays;
import java.util.zip.CRC32;

/** V5: LAN-only, RAM-only test server. One TCP connection per PWDSI001 frame. */
public final class DSiV5Server implements Closeable {
    public static final int PORT=30822;
    public interface Listener { void event(String text); }
    private final Listener listener;
    private volatile boolean running;
    private ServerSocket server;
    private Thread worker;
    private final byte[] buffer=new byte[8192];
    private int session, total, expected, received;
    private boolean active;
    public DSiV5Server(Listener cb){listener=cb;}
    private void emit(String s){listener.event(s);}
    public synchronized void start() throws IOException {
        if(running)return;
        server=new ServerSocket();server.setReuseAddress(true);
        server.bind(new InetSocketAddress("0.0.0.0",PORT),2);
        server.setSoTimeout(800);
        running=true;
        worker=new Thread(this::loop,"PW-V5-Server");worker.start();
        emit("Escutando na porta "+PORT+". Mantenha esta tela aberta.");
    }
    public synchronized void close(){running=false;if(server!=null)try{server.close();}catch(IOException ignored){}server=null;active=false;}
    private void loop(){
        while(running){
            try(Socket c=server.accept()){
                c.setSoTimeout(4000);
                InetAddress a=c.getInetAddress();
                if(!isLocal(a)){emit("Conexao nao local recusada");continue;}
                process(c);
            }catch(SocketTimeoutException ignored){}
             catch(IOException e){if(running)emit("Rede: "+e.getMessage());}
             catch(RuntimeException e){emit("Pacote invalido: "+e.getMessage());}
        }
    }
    private static boolean isLocal(InetAddress a){
        if(!(a instanceof Inet4Address))return false;
        if(a.isLoopbackAddress())return true;
        byte[] b=a.getAddress();int x=b[0]&255,y=b[1]&255;
        return x==10 || (x==172&&y>=16&&y<=31) || (x==192&&y==168) || (x==169&&y==254);
    }
    private static int val(byte[] b,int pos){return ByteBuffer.wrap(b,pos,4).order(ByteOrder.BIG_ENDIAN).getInt();}
    private static byte[] nums(int... xs){ByteBuffer b=ByteBuffer.allocate(xs.length*4).order(ByteOrder.BIG_ENDIAN);for(int x:xs)b.putInt(x);return b.array();}
    private static int crc(byte[] b){CRC32 c=new CRC32();c.update(b);return (int)c.getValue();}
    private static void read(InputStream in,byte[] buf)throws IOException{new DataInputStream(in).readFully(buf);}
    private static void reply(OutputStream out,int action,byte[] payload)throws IOException{
        ByteBuffer b=ByteBuffer.allocate(16+payload.length).order(ByteOrder.BIG_ENDIAN);
        b.put(new byte[]{'P','W','D','S','I','0','0','1'}).put((byte)1).put((byte)action).putShort((short)payload.length).putInt(crc(payload)).put(payload);
        out.write(b.array());out.flush();
    }
    private static void failure(OutputStream out,int code)throws IOException{reply(out,0x7f,new byte[]{0,(byte)code});}
    private void process(Socket c)throws IOException{
        InputStream in=c.getInputStream();OutputStream out=c.getOutputStream();
        byte[] h=new byte[16];read(in,h);
        if(!Arrays.equals(Arrays.copyOf(h,8),new byte[]{'P','W','D','S','I','0','0','1'}) || h[8]!=1)throw new IOException("Magic/versao invalidos");
        int action=h[9]&255,len=((h[10]&255)<<8)|(h[11]&255);
        if(len>1024)throw new IOException("Quadro grande demais");
        byte[] p=new byte[len];read(in,p);
        if(crc(p)!=val(h,12)){emit("CRC32 de quadro invalido");return;}
        if(action==4){reply(out,0x84,p);emit("DSi -> Android: PING recebido ("+len+" bytes)");return;}
        if(action==0x10){
            if(len!=12){failure(out,1);return;}
            int id=val(p,0),size=val(p,4),check=val(p,8);
            if(id==0||size<1||size>8192){failure(out,6);return;}
            if(active){failure(out,2);return;}
            session=id;total=size;expected=check;received=0;active=true;
            reply(out,0x90,nums(session,total,512));emit("Sessao iniciada: "+total+" bytes");return;
        }
        if(action==0x11){
            if(len<9||len>520){failure(out,1);return;}
            if(!active){failure(out,2);return;}
            int id=val(p,0),offset=val(p,4);
            if(id!=session){failure(out,3);return;}
            if(offset!=received){failure(out,4);return;}
            int n=len-8;if(n>total-received){failure(out,6);return;}
            System.arraycopy(p,8,buffer,received,n);received+=n;
            reply(out,0x91,nums(session,received));
            emit("Blocos DSi -> Android: "+received+"/"+total);return;
        }
        if(action==0x12){
            if(len!=4){failure(out,1);return;}
            if(!active){failure(out,2);return;}
            if(val(p,0)!=session){failure(out,3);return;}
            if(received!=total){failure(out,1);return;}
            CRC32 checksum=new CRC32();checksum.update(buffer,0,total);int actual=(int)checksum.getValue();
            active=false;
            if(actual!=expected){failure(out,5);emit("TRANSFERENCIA REJEITADA: CRC total invalido");return;}
            reply(out,0x92,nums(session,total,actual));
            emit("SUCESSO: "+total+" bytes recebidos do DSi, CRC32 "+String.format(java.util.Locale.US,"%08x",actual));return;
        }
        if(action==0x13){
            if(len!=4||!active||val(p,0)!=session){failure(out,3);return;}
            active=false;reply(out,0x93,nums(session));emit("Sessao cancelada");return;
        }
        failure(out,7);
    }
}
