package io.github.sdtransporter.pokewalker;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.os.*;
import java.io.*;
import java.net.*;
import java.util.Locale;

/** Phone-side listener for direct DSi/nds-bootstrap Pokéwalker handoff. */
public final class DirectSyncService extends Service {
    static final String PREFS="direct_dsi_sync";
    static final String ACTION_START="io.github.sdtransporter.pokewalker.DIRECT_START";
    static final String ACTION_STOP="io.github.sdtransporter.pokewalker.DIRECT_STOP";
    static final String KEY_ENABLED="enabled";
    static final String KEY_STATUS="status";
    private volatile boolean running;
    private ServerSocket server;
    private Thread thread;

    static boolean enabled(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getBoolean(KEY_ENABLED,false);}
    static String status(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getString(KEY_STATUS,"Stopped");}
    static void start(Context c){Intent i=new Intent(c,DirectSyncService.class).setAction(ACTION_START);if(Build.VERSION.SDK_INT>=26)c.startForegroundService(i);else c.startService(i);}
    static void stop(Context c){c.startService(new Intent(c,DirectSyncService.class).setAction(ACTION_STOP));}

    private void state(boolean enabled,String text){getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean(KEY_ENABLED,enabled).putString(KEY_STATUS,text).apply();notifyNow(text);}

    @Override public void onCreate(){super.onCreate();
        NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel("direct_dsi","Direct DSi sync",NotificationManager.IMPORTANCE_LOW));
    }
    @Override public int onStartCommand(Intent intent,int flags,int id){
        if(intent!=null&&ACTION_STOP.equals(intent.getAction())){shutdown();return START_NOT_STICKY;}
        if(running)return START_STICKY;
        running=true;
        Notification n=notification("Waiting for DSi on port "+DirectSyncProtocol.PORT);
        if(Build.VERSION.SDK_INT>=34)startForeground(14,n,ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);else startForeground(14,n);
        state(true,"Waiting for DSi on port "+DirectSyncProtocol.PORT);
        thread=new Thread(this::serve,"direct-dsi-sync");thread.start();
        return START_STICKY;
    }
    private Notification notification(String text){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,DirectSyncService.class).setAction(ACTION_STOP),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,"direct_dsi").setSmallIcon(R.drawable.ic_stat_walker).setContentTitle("Pokéwalker · Direct DSi Sync")
            .setContentText(text).setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
            .addAction(new Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel,"Stop",stop).build()).build();
    }
    private void notifyNow(String text){if(running)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(14,notification(text));}
    private void serve(){
        try(ServerSocket s=new ServerSocket()){server=s;s.setReuseAddress(true);s.bind(new InetSocketAddress(DirectSyncProtocol.PORT));s.setSoTimeout(1500);
            while(running){try{Socket peer=s.accept();handle(peer);}catch(SocketTimeoutException ignored){}catch(IOException ex){if(running)state(true,"Direct sync error: "+ex.getMessage());}}
        }catch(IOException ex){if(running)state(false,"Could not listen: "+ex.getMessage());}
        finally{running=false;server=null;stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
    }
    private static boolean token(String s){return s!=null&&s.matches("[a-f0-9]{32}");}
    private static boolean trainer(String s){return s!=null&&s.matches("[a-f0-9]{36}");}
    private void handle(Socket socket){
        try(Socket peer=socket){
            peer.setSoTimeout(60000);
            // V6.6: accept repeated PING frames on the same TCP connection.
            // All real walker operations remain one-request-per-connection.
            java.io.InputStream input=peer.getInputStream();
            boolean announced=false;
            for(int pingCount=0;running;pingCount++){
                DirectSyncProtocol.Frame f=null;
                try {
                    f=DirectSyncProtocol.read(input);
                    if(!announced){state(true,"DSi connected · processing request");announced=true;}
                    if(f.op==DirectSyncProtocol.OP_PING){
                        ok(peer,f.session,f.trainer,null,-1);
                        // Do not create a notification every 400 ms on repeated PINGs.
                        continue;
                    }
                    switch(f.op){
                        case DirectSyncProtocol.OP_PUSH_TO_PHONE: push(peer,f);break;
                        case DirectSyncProtocol.OP_PULL_FROM_PHONE: pull(peer,f);break;
                        case DirectSyncProtocol.OP_CONFIRM_RETURN: confirm(peer,f);break;
                        default: throw new IOException("Unknown DSi sync operation");
                    }
                    break;
                }catch(java.io.EOFException eof){
                    break; // DSi disconnected normally.
                }catch(Exception ex){
                    if(f!=null)try{fail(peer,f,ex.getMessage()==null?"Direct sync failed":ex.getMessage());}catch(IOException ignored){}
                    state(true,"Last DSi request failed: "+(ex.getMessage()==null?ex.getClass().getSimpleName():ex.getMessage()));
                    return;
                }
            }
            state(true,"Waiting for DSi on port "+DirectSyncProtocol.PORT);
        }catch(Exception ex){state(true,"Last DSi request failed: "+ex.getMessage());}
    }
    private void push(Socket peer,DirectSyncProtocol.Frame f)throws IOException{
        if(!token(f.session)||f.length!=DirectSyncProtocol.WALKER_SIZE)throw new IOException("Invalid DSi checkout frame");
        if(!Native.walkable(f.payload))throw new IOException("DSi sent an invalid walker");
        String key=Native.text(f.payload,4).toLowerCase(Locale.ROOT);if(!trainer(key))throw new IOException("Walker trainer binding is unavailable");
        if(!f.trainer.isEmpty()&&!f.trainer.equals(key))throw new IOException("DSi trainer binding does not match walker data");
        synchronized(WalkerStore.LOCK){WalkerStore s=WalkerStore.get(this);
            if(s.syncing)throw new IOException("Another sync is in progress");
            if(s.active())throw new IOException("Return the current Pokémon before receiving another");
            if(!s.trainerKey.isEmpty()&&!s.trainerKey.equals(key))throw new IOException("Select the Android profile paired to this HGSS save");
            if(s.data!=null)s.archiveCurrent("direct-replaced");
            if(s.completedSession(f.session))throw new IOException("This DSi session was already returned");
            s.returnCompleted=false;s.battlePaid=s.battleDone=s.battleRewarded=false;s.battleSession=s.battlePeer="";s.battleWinner=0;s.battleRewardChoice=-1;
            s.data=f.payload.clone();s.token=f.session;s.pendingToken="";s.trainerKey=key;s.host="direct-dsi";s.revoked=false;s.returnPending=false;s.sensorLast=-1;s.boot=-1;s.mode=2;
            Native.resume(s.data,Native.now(),s.rate);s.archiveCurrent("direct-received");s.save();
        }
        WalkingService.ensureRunning(this);PokewalkerWidgetProvider.updateAll(this);ok(peer,f.session,key,null,-1);
    }
    private void pull(Socket peer,DirectSyncProtocol.Frame f)throws IOException{
        final byte[] payload;final String key;
        synchronized(WalkerStore.LOCK){WalkerStore s=WalkerStore.get(this);
            if(s.syncing)throw new IOException("Another sync is in progress");
            if(!s.active()&&!(s.returnPending&&s.data!=null&&!s.token.isEmpty()))throw new IOException("No active Pokémon is available to return");
            if(!f.session.equals(s.token))throw new IOException("DSi session does not match this phone walker");
            key=s.trainerKey.isEmpty()?Native.text(s.data,4).toLowerCase(Locale.ROOT):s.trainerKey;
            if(!f.trainer.isEmpty()&&!f.trainer.equals(key))throw new IOException("DSi trainer binding does not match this profile");
            if(s.mode==1)Native.timer(s.data,Native.now(),s.rate);
            s.archiveCurrent("direct-returning");s.mode=0;s.returnPending=true;s.save();payload=s.data.clone();
        }
        ok(peer,f.session,key,payload,-1);
    }
    private void confirm(Socket peer,DirectSyncProtocol.Frame f)throws IOException{
        synchronized(WalkerStore.LOCK){WalkerStore s=WalkerStore.get(this);
            if(s.data==null||s.token.isEmpty()||!s.returnPending)throw new IOException("No direct return is awaiting confirmation");
            if(!f.session.equals(s.token))throw new IOException("Return confirmation session mismatch");
            long expected=DirectSyncProtocol.crc(s.data);if(f.crc!=expected)throw new IOException("DSi stored checksum does not match phone walker");
            byte[] returned=s.data.clone();s.completeReturn(s.token,returned);s.data=null;s.token="";s.pendingToken="";s.revoked=false;s.returnPending=false;s.sensorLast=-1;s.mode=0;s.save();
        }
        PokewalkerWidgetProvider.updateAll(this);ok(peer,f.session,f.trainer,null,f.crc);
    }
    private void ok(Socket peer,String session,String trainer,byte[] payload,long crc)throws IOException{DirectSyncProtocol.write(peer.getOutputStream(),DirectSyncProtocol.OP_OK,session,trainer,payload,crc,null);}
    private void fail(Socket peer,DirectSyncProtocol.Frame f,String message)throws IOException{DirectSyncProtocol.write(peer.getOutputStream(),DirectSyncProtocol.OP_ERROR,f.session,f.trainer,null,-1,message);}
    private void shutdown(){running=false;try{if(server!=null)server.close();}catch(IOException ignored){}state(false,"Stopped");stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
    @Override public void onDestroy(){running=false;try{if(server!=null)server.close();}catch(IOException ignored){}super.onDestroy();}
    @Override public android.os.IBinder onBind(Intent intent){return null;}
}
