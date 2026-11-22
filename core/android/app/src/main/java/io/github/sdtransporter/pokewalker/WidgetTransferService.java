package io.github.sdtransporter.pokewalker;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.appwidget.AppWidgetManager;
import android.content.Intent;
import android.os.IBinder;
import java.io.IOException;
import java.security.SecureRandom;

public final class WidgetTransferService extends Service {
    static final String ACTION_RECEIVE="io.github.sdtransporter.pokewalker.SERVICE_RECEIVE";
    static final String ACTION_RETURN="io.github.sdtransporter.pokewalker.SERVICE_RETURN";
    static final String EXTRA_PROFILE_ID="profile_id";
    static final String EXTRA_HOST="host";
    private static final String CHANNEL="widget_sync";

    @Override public void onCreate(){super.onCreate();
        NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL,"Pokéwalker sync",NotificationManager.IMPORTANCE_LOW));
    }

    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent==null){stopSelf(startId);return START_NOT_STICKY;}
        boolean returning=ACTION_RETURN.equals(intent.getAction());
        int widgetId=intent.getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,AppWidgetManager.INVALID_APPWIDGET_ID);
        String profileId=intent.getStringExtra(EXTRA_PROFILE_ID),host=intent.getStringExtra(EXTRA_HOST);
        if(widgetId==AppWidgetManager.INVALID_APPWIDGET_ID||profileId==null||host==null||!host.matches("[A-Za-z0-9.:-]+")){
            stopSelf(startId);return START_NOT_STICKY;
        }
        Notification n=new Notification.Builder(this,CHANNEL).setSmallIcon(R.drawable.ic_stat_walker)
            .setContentTitle(returning?"Devolvendo Pokémon":"Recebendo Pokémon")
            .setContentText("Mantenha o console na tela de sincronização.").setOngoing(true).setOnlyAlertOnce(true).build();
        startForeground(22,n);
        new Thread(()->{runTransfer(widgetId,profileId,host,returning);stopForeground(STOP_FOREGROUND_REMOVE);stopSelf(startId);},"widget-walker-sync").start();
        return START_NOT_STICKY;
    }

    private void runTransfer(int widgetId,String profileId,String host,boolean returning){
        WalkerStore s=null; long operation=0; String session=""; byte[] payload=null; int previousMode=0;
        try{
            synchronized(WalkerStore.LOCK){
                for(WalkerStore item:WalkerStore.all(this))if(item.profileId.equals(profileId)){s=item;break;}
                if(s==null)throw new IOException("Perfil não encontrado");
                if(s.syncing)throw new IOException("Uma sincronização já está em andamento");
                if(returning&&s.battleRewardChoice>=0)throw new IOException("Resolva a recompensa de batalha antes de devolver");
                if(returning&&s.active()&&s.mode==1)Native.timer(s.data,Native.now(),s.rate);
                if(returning&&!s.active())throw new IOException("Nenhum Pokémon está disponível para devolver");
                if(returning&&s.completedSession(s.token))throw new IOException("Esta sessão já foi devolvida ou excluída");
                if(!returning&&s.active())throw new IOException("Devolva o Pokémon atual antes de receber outro");
                if(!returning&&!s.pendingToken.isEmpty()&&s.completedSession(s.pendingToken))s.pendingToken="";
                s.archiveCurrent(returning?"returning":"replaced");
                if(s.trainerKey.isEmpty()&&s.data!=null)s.trainerKey=Native.text(s.data,4);
                s.host=host;
                if(returning){previousMode=s.mode;s.mode=0;s.returnPending=true;payload=s.data.clone();session=s.token;}
                else if(s.pendingToken.isEmpty()){
                    byte[] random=new byte[16];new SecureRandom().nextBytes(random);StringBuilder b=new StringBuilder();
                    for(byte value:random)b.append(String.format(java.util.Locale.ROOT,"%02x",value&255));s.pendingToken=b.toString();
                }
                if(!returning)session=s.pendingToken;
                s.save();operation=s.beginSync();
            }
            final WalkerStore state=s; final long op=operation; final String sess=session; final byte[] sent=payload;
            WidgetConfigActivity.setStatus(this,widgetId,returning?"Devolvendo…":"Recebendo…");refresh(widgetId);
            byte[] incoming;
            try{
                incoming=WalkerSync.exchange(returning,host,sess,sent,state.trainerKey,message->{WidgetConfigActivity.setStatus(this,widgetId,message);refresh(widgetId);});
            }catch(WalkerSync.Rejected ex){
                synchronized(WalkerStore.LOCK){
                    if(!state.currentSync(op))throw new IOException("Esta sincronização foi substituída");
                    if(!returning&&ex.status==410)state.pendingToken="";
                    if(returning&&ex.status==410){state.revoked=true;state.mode=0;state.returnPending=false;}
                    state.save();
                }
                throw ex;
            }
            synchronized(WalkerStore.LOCK){
                if(!state.currentSync(op))throw new IOException("Esta sincronização foi substituída");
                if(returning){
                    state.completeReturn(sess,sent);state.data=null;state.token="";state.pendingToken="";state.revoked=false;state.returnPending=false;state.sensorLast=-1;
                }else{
                    if(incoming.length!=65536||!Native.walkable(incoming))throw new IOException("Walker recebido é inválido");
                    String receivedKey=Native.text(incoming,4);
                    if(!receivedKey.matches("[a-f0-9]{36}"))throw new IOException("Dados do treinador indisponíveis");
                    if(!state.trainerKey.isEmpty()&&!state.trainerKey.equals(receivedKey))throw new IOException("O treinador não corresponde a este perfil");
                    state.trainerKey=receivedKey;
                    if(state.completedSession(sess))throw new IOException("Esta transferência já foi devolvida; inicie uma nova");
                    state.returnCompleted=false;state.battlePaid=state.battleDone=state.battleRewarded=false;state.battleSession=state.battlePeer="";state.battleWinner=0;state.battleRewardChoice=-1;
                    state.data=incoming;state.token=sess;state.pendingToken="";state.revoked=false;state.returnPending=false;state.sensorLast=-1;state.boot=-1;state.mode=2;
                    Native.resume(state.data,Native.now(),state.rate);state.archiveCurrent("received");
                }
                state.save();state.finishSync(op);
            }
            WidgetConfigActivity.clearStatus(this,widgetId);
            PokewalkerWidgetProvider.resetClassic(this,widgetId);
            refresh(widgetId);
            if(!returning){
                try{startForegroundService(new Intent(this,WalkingService.class));}catch(Exception ignored){}
            }else{
                try{startForegroundService(new Intent(this,WalkingService.class));}catch(Exception ignored){}
            }
        }catch(Exception ex){
            /*
             * A widget sync failure must be non-destructive.  The return flow
             * temporarily locks the local walker (returnPending=true, mode=0)
             * before networking starts.  If the transfer does not finish, put
             * that exact local walker back into its previous walking mode and
             * return the Classic UI to HOME instead of leaving the widget stuck
             * on SYNC ERROR / return pending.  The recovery snapshot created
             * above remains on disk.
             */
            if(s!=null){
                synchronized(WalkerStore.LOCK){
                    if(returning&&s.active()&&!s.revoked&&!s.returnCompleted){
                        // Always unlock a failed local return.  currentSync() can be
                        // false after lifecycle/process edge cases, but an exception
                        // here means this service did not complete the handoff.
                        s.returnPending=false;
                        s.mode=previousMode;
                        if(s.mode==0)s.mode=2;
                    }
                    if(operation!=0&&s.currentSync(operation))s.finishSync(operation);
                    try{s.save();}catch(Exception ignored){}
                }
            }
            WidgetConfigActivity.clearStatus(this,widgetId);
            PokewalkerWidgetProvider.resetClassic(this,widgetId);
            refresh(widgetId);
            if(returning&&s!=null&&s.active()){
                try{startForegroundService(new Intent(this,WalkingService.class));}catch(Exception ignored){}
            }
        }
    }

    private void refresh(int widgetId){PokewalkerWidgetProvider.updateWidget(this,AppWidgetManager.getInstance(this),widgetId);}
    @Override public IBinder onBind(Intent intent){return null;}
}
