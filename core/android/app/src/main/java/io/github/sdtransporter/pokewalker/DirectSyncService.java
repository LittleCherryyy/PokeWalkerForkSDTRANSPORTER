package io.github.sdtransporter.pokewalker;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.os.*;
import java.io.*;
import java.net.*;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** Phone-side listener for direct DSi/nds-bootstrap Pokéwalker handoff. */
public final class DirectSyncService extends Service {
    static final String PREFS="direct_dsi_sync";
    static final String ACTION_START="io.github.sdtransporter.pokewalker.DIRECT_START";
    static final String ACTION_STOP="io.github.sdtransporter.pokewalker.DIRECT_STOP";
    static final String EXTRA_PROFILE_ID="profile_id";
    static final String EXTRA_ARMED_OPERATION="armed_operation";
    static final String KEY_ENABLED="enabled";
    static final String KEY_STATUS="status";
    static final String KEY_LAST_EVENT="last_event";
    static final String KEY_CONNECTION_EVENTS="connection_events";
    static final String KEY_TARGET_PROFILE="target_profile";
    static final String KEY_ARMED_OPERATION="armed_operation";
    private static final Object EVENT_LOCK=new Object();
    private static final Object ARM_LOCK=new Object();
    private static final int MAX_CONNECTION_EVENTS=8;
    private static volatile DirectSyncService liveService;
    private volatile boolean running;
    private volatile boolean listeningReady;
    private volatile boolean preservingArmForRestart;
    private volatile String targetProfileId="";
    private volatile int armedOperation;
    private volatile long armGeneration;
    private ServerSocket server;
    private Thread thread;

    static boolean processRunning(){DirectSyncService service=liveService;return service!=null&&service.running;}
    static boolean enabled(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getBoolean(KEY_ENABLED,false);}
    static String status(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getString(KEY_STATUS,"Stopped");}
    static String targetProfileId(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getString(KEY_TARGET_PROFILE,WalkerStore.get(c).profileId);}
    static int armedOperation(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getInt(KEY_ARMED_OPERATION,0);}
    static int operationFor(WalkerStore store){return store!=null&&(store.active()||store.returnPending)?DirectSyncProtocol.OP_ARM_PULL:DirectSyncProtocol.OP_ARM_PUSH;}
    static String targetProfileName(Context c){
        String id=targetProfileId(c);
        for(WalkerProfiles.Entry entry:WalkerStore.profileEntries(c))if(id.equals(entry.id))return entry.name;
        return WalkerStore.profileName(c);
    }
    static WalkerStore targetStore(Context c){
        String id=targetProfileId(c);
        for(WalkerStore store:WalkerStore.all(c))if(id.equals(store.profileId))return store;
        return WalkerStore.get(c);
    }
    static String lastEvent(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getString(KEY_LAST_EVENT,"nenhuma transferência recebida ainda");}
    static String connectionEvents(Context c){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getString(KEY_CONNECTION_EVENTS,"nenhuma conexão TCP recebida ainda");}
    static void start(Context c){start(c,WalkerStore.get(c).profileId,operationFor(WalkerStore.get(c)));}
    static void start(Context c,String profileId){
        WalkerStore target=null;
        for(WalkerStore store:WalkerStore.all(c))if(profileId!=null&&profileId.equals(store.profileId)){target=store;break;}
        start(c,profileId,operationFor(target));
    }
    static void start(Context c,String profileId,int operation){
        Intent i=new Intent(c,DirectSyncService.class).setAction(ACTION_START).putExtra(EXTRA_PROFILE_ID,profileId).putExtra(EXTRA_ARMED_OPERATION,operation);
        if(Build.VERSION.SDK_INT>=26)c.startForegroundService(i);else c.startService(i);
    }
    static void stop(Context c){c.startService(new Intent(c,DirectSyncService.class).setAction(ACTION_STOP));}
    static void restoreAfterPackageUpdate(Context c){
        if(!enabled(c)||processRunning())return;
        int operation=armedOperation(c);
        if(operation==DirectSyncProtocol.OP_ARM_PUSH||operation==DirectSyncProtocol.OP_ARM_PULL)
            start(c,targetProfileId(c),operation);
    }

    private void state(boolean enabled,String text){getSharedPreferences(PREFS,MODE_PRIVATE).edit().putBoolean(KEY_ENABLED,enabled).putString(KEY_STATUS,text).apply();notifyNow(text);PokewalkerWidgetProvider.updateAll(this);}
    private void recordEvent(String text){getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString(KEY_LAST_EVENT,text).apply();}
    private void recordConnectionEvent(String text){
        String clean=text==null?"evento de rede":text.replace('\n',' ').replace('\r',' ');
        String stamp=new SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(new Date());
        synchronized(EVENT_LOCK){
            android.content.SharedPreferences prefs=getSharedPreferences(PREFS,MODE_PRIVATE);
            String previous=prefs.getString(KEY_CONNECTION_EVENTS,"");
            StringBuilder next=new StringBuilder(stamp).append(" · ").append(clean);
            int kept=1;
            if(previous!=null&&!previous.isEmpty())for(String line:previous.split("\\n")){
                if(kept>=MAX_CONNECTION_EVENTS||line.isEmpty())break;
                next.append('\n').append(line);kept++;
            }
            prefs.edit().putString(KEY_CONNECTION_EVENTS,next.toString()).apply();
        }
    }

    @Override public void onCreate(){super.onCreate();liveService=this;
        NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel("direct_dsi","Direct DSi sync",NotificationManager.IMPORTANCE_LOW));
    }
    @Override public int onStartCommand(Intent intent,int flags,int id){
        if(intent!=null&&ACTION_STOP.equals(intent.getAction())){shutdown();return START_NOT_STICKY;}
        String requested=intent==null?"":intent.getStringExtra(EXTRA_PROFILE_ID);
        if(requested==null||requested.isEmpty())
            requested=getSharedPreferences(PREFS,MODE_PRIVATE).getString(KEY_TARGET_PROFILE,WalkerStore.get(this).profileId);
        // START_STICKY restarts the service with a null Intent after Android
        // reclaims its process. Restore the explicit, user-armed direction so
        // the widget does not get stuck in an enabled-but-unarmed state.
        int requestedOperation=intent==null
                ?getSharedPreferences(PREFS,MODE_PRIVATE).getInt(KEY_ARMED_OPERATION,0)
                :intent.getIntExtra(EXTRA_ARMED_OPERATION,0);
        if(requestedOperation!=DirectSyncProtocol.OP_ARM_PUSH&&requestedOperation!=DirectSyncProtocol.OP_ARM_PULL)
            requestedOperation=0;
        if(!profileExists(requested)){
            recordConnectionEvent("Perfil de destino do widget não encontrado");
            if(!running)stopSelf(id);
            return START_NOT_STICKY;
        }
        synchronized(ARM_LOCK){targetProfileId=requested;armedOperation=requestedOperation;armGeneration++;}
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString(KEY_TARGET_PROFILE,requested)
                .putInt(KEY_ARMED_OPERATION,requestedOperation).apply();
        if(running){
            recordConnectionEvent("Connect to Console armado: "+armedOperationName(requestedOperation)+" · "+profileName(requested));
            state(true,listeningReady?listeningText():"Starting listener on port "+DirectSyncProtocol.PORT+" · "+armedOperationName(requestedOperation));
            return START_STICKY;
        }
        running=true;
        listeningReady=false;
        Notification n=notification("Starting listener on port "+DirectSyncProtocol.PORT);
        // This service maintains a user-requested local connection to the DSi.
        // Treat it as an external-device session so Android does not apply the
        // six-hour dataSync foreground-service budget to an idle listener.
        if(Build.VERSION.SDK_INT>=29)startForeground(14,n,ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);else startForeground(14,n);
        state(true,"Starting listener on port "+DirectSyncProtocol.PORT+" · "+armedOperationName(requestedOperation));
        recordConnectionEvent("Connect to Console armado: "+armedOperationName(requestedOperation)+" · receptor na porta TCP "+DirectSyncProtocol.PORT);
        thread=new Thread(this::serve,"direct-dsi-sync");thread.start();
        return START_STICKY;
    }
    private boolean profileExists(String id){
        if(id==null||id.isEmpty())return false;
        for(WalkerStore store:WalkerStore.all(this))if(id.equals(store.profileId))return true;
        return false;
    }
    private String profileName(String id){
        for(WalkerProfiles.Entry entry:WalkerStore.profileEntries(this))if(id.equals(entry.id))return entry.name;
        return "perfil selecionado";
    }
    private static String armedOperationName(int operation){
        if(operation==DirectSyncProtocol.OP_ARM_PUSH)return "Send to phone";
        if(operation==DirectSyncProtocol.OP_ARM_PULL)return "Return to HGSS";
        return "no transfer armed";
    }
    private String listeningText(){return "Listening for DSi on port "+DirectSyncProtocol.PORT+" · "+armedOperationName(armedOperation)+" · "+profileName(targetProfileId);}
    private Notification notification(String text){
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,DirectSyncService.class).setAction(ACTION_STOP),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,"direct_dsi").setSmallIcon(R.drawable.ic_stat_walker).setContentTitle("Pokéwalker · Direct DSi Sync")
            .setContentText(text).setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
            .addAction(new Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel,"Stop",stop).build()).build();
    }
    private void notifyNow(String text){if(running)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(14,notification(text));}
    private void serve(){
        try(ServerSocket s=new ServerSocket()){server=s;s.setReuseAddress(true);s.bind(new InetSocketAddress(DirectSyncProtocol.PORT));s.setSoTimeout(1500);listeningReady=true;
            state(true,listeningText());
            recordConnectionEvent("Escuta ativa na porta TCP "+DirectSyncProtocol.PORT);
            while(running){try{
                Socket peer=s.accept();
                String ip=peer.getInetAddress().getHostAddress();
                String profileAtAccept=targetProfileId;
                state(true,"DSi TCP connected from "+ip);
                recordConnectionEvent("TCP aceito de "+ip+" · perfil "+profileName(profileAtAccept));
                handle(peer,profileAtAccept);
            }catch(SocketTimeoutException ignored){}catch(IOException ex){if(running){state(true,"Direct sync error: "+ex.getMessage());recordConnectionEvent("Erro no listener: "+ex.getMessage());}}}
        }catch(IOException ex){if(running){
            String reason=ex.getMessage()==null?ex.getClass().getSimpleName():ex.getMessage();
            state(false,"Could not listen: "+reason);
            WidgetConfigActivity.setStatusForProfile(this,targetProfileId,"Erro: não foi possível abrir TCP "+DirectSyncProtocol.PORT+" — "+reason);
            recordConnectionEvent("Falha ao abrir o listener: "+reason);
        }}
        finally{
            running=false;listeningReady=false;server=null;
            if(!preservingArmForRestart)clearArming();
            stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();
        }
    }
    private static String operationName(int op){
        switch(op){
            case DirectSyncProtocol.OP_PUSH_TO_PHONE:return "PUSH Pokémon para o celular";
            case DirectSyncProtocol.OP_PULL_FROM_PHONE:return "PULL Pokémon para o HGSS";
            case DirectSyncProtocol.OP_CONFIRM_RETURN:return "confirmação do retorno";
            case DirectSyncProtocol.OP_PING:return "PING";
            case DirectSyncProtocol.OP_TEST_ECHO:return "quadro de teste sintético";
            case DirectSyncProtocol.OP_ARM_PUSH:return "intenção Send to phone";
            case DirectSyncProtocol.OP_ARM_PULL:return "intenção Return to HGSS";
            default:return "operação "+op;
        }
    }
    private static boolean token(String s){return s!=null&&s.matches("[a-f0-9]{32}");}
    private static boolean trainer(String s){return s!=null&&s.matches("[a-f0-9]{36}");}
    private static final class ReturnSyncGuard {
        final WalkerStore store;
        final long epoch;
        ReturnSyncGuard(WalkerStore store,long epoch){this.store=store;this.epoch=epoch;}
        void release(Context context){
            store.finishSync(epoch);
            PokewalkerWidgetProvider.updateAll(context);
        }
    }
    private static final class ArmedSelection {
        final String profileId;
        final int operation;
        final long generation;
        ArmedSelection(String profileId,int operation,long generation){
            this.profileId=profileId;this.operation=operation;this.generation=generation;
        }
    }
    private void handle(Socket socket,String profileAtAccept){
        ReturnSyncGuard returnGuard=null;
        try(Socket peer=socket){
            peer.setSoTimeout(60000);
            boolean closedBeforeFrame=false;
            boolean awaitingReturnConfirmation=false;
            boolean directionAuthorized=false;
            int authorizedArmOperation=0;
            int authorizedTransferOperation=0;
            String authorizedSession="",authorizedTrainer="";
            String transferProfileId=profileAtAccept;
            long authorizedArmGeneration=0;
            long authorizedPushCrc=0;
            java.io.InputStream input=peer.getInputStream();
            boolean announced=false;
            while(running){
                DirectSyncProtocol.Frame f=null;
                try {
                    f=DirectSyncProtocol.readHeader(input);
                    if(!announced||f.op!=DirectSyncProtocol.OP_PING){
                        state(true,"DSi protocol frame received · processing request");
                        if(f.op!=DirectSyncProtocol.OP_PING)recordConnectionEvent("Quadro recebido: "+operationName(f.op));
                        announced=true;
                    }
                    if(f.op==DirectSyncProtocol.OP_PING){
                        if(f.length!=0)throw new IOException("Invalid DSi ping frame");
                        DirectSyncProtocol.readPayload(input,f);
                        ok(peer,f.session,f.trainer,null,-1);
                        // Do not create a notification every 400 ms on repeated PINGs.
                        continue;
                    }
                    if(f.op==DirectSyncProtocol.OP_TEST_ECHO){
                        // V6.7: only accept a fixed synthetic pattern; do not
                        // touch profiles, saves, EEPROM, or WalkerStore.
                        if(f.length!=512)
                            throw new IOException("Invalid V6.7 test block size");
                        DirectSyncProtocol.readPayload(input,f);
                        int index=((f.payload[0]&255)<<24)|((f.payload[1]&255)<<16)|((f.payload[2]&255)<<8)|(f.payload[3]&255);
                        if(index<0 || index>=16)throw new IOException("Invalid V6.7 test block index");
                        for(int i=4;i<512;i++){
                            int expected=(int)(((long)(index*508+i-4)*73+19)&255);
                            if((f.payload[i]&255)!=expected)
                                throw new IOException("Invalid V6.7 synthetic payload");
                        }
                        ok(peer,"","",f.payload,-1);
                        continue;
                    }
                    if(f.op==DirectSyncProtocol.OP_ARM_PUSH||f.op==DirectSyncProtocol.OP_ARM_PULL){
                        if(f.length!=0)throw new IOException("Invalid legacy direction header");
                        DirectSyncProtocol.readPayload(input,f);
                        if(directionAuthorized)throw new IOException("A transfer direction is already active on this TCP session");
                        ArmedSelection armed=awaitDirectionArm(f);
                        transferProfileId=armed.profileId;
                        authorizedArmGeneration=armed.generation;
                        directionAuthorized=true;
                        // Keep the direction actually armed by the user. The
                        // incoming ARM may be an exact retry after a lost ACK.
                        authorizedArmOperation=armed.operation;
                        authorizedTransferOperation=f.op==DirectSyncProtocol.OP_ARM_PUSH
                                ?DirectSyncProtocol.OP_PUSH_TO_PHONE
                                :((f.flags&1)!=0?DirectSyncProtocol.OP_CONFIRM_RETURN:DirectSyncProtocol.OP_PULL_FROM_PHONE);
                        authorizedSession=f.session;
                        authorizedTrainer=f.trainer;
                        authorizedPushCrc=f.crc;
                        DirectSyncProtocol.write(peer.getOutputStream(),DirectSyncProtocol.OP_READY,
                                f.session,f.trainer,null,0,null);
                        state(true,"DSi direction approved · "+armedOperationName(f.op));
                        recordConnectionEvent("Direção autorizada por Connect to Console: "+armedOperationName(f.op));
                        continue;
                    }
                    if(f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE||f.op==DirectSyncProtocol.OP_PULL_FROM_PHONE||f.op==DirectSyncProtocol.OP_CONFIRM_RETURN){
                        if(awaitingReturnConfirmation&&f.op!=DirectSyncProtocol.OP_CONFIRM_RETURN)
                            throw new IOException("Expected return confirmation after the DSi PULL");

                        /* A lost final ACK can leave only the DSi's local receipt
                         * pending. A matching durable receipt is safe to replay
                         * without arming a new transfer direction. */
                        if(!directionAuthorized&&f.op==DirectSyncProtocol.OP_CONFIRM_RETURN&&
                           completedReceipt(profileAtAccept,f)){
                            if(f.length!=0||f.flags!=0)throw new IOException("Invalid return receipt replay");
                            DirectSyncProtocol.readPayload(input,f);
                            confirm(peer,f,profileAtAccept);
                            shutdown();
                            break;
                        }

                        if(!directionAuthorized){
                            ArmedSelection armed=awaitDirectionArm(f);
                            transferProfileId=armed.profileId;
                            authorizedArmGeneration=armed.generation;
                            authorizedArmOperation=armed.operation;
                            authorizedTransferOperation=f.op;
                            authorizedSession=f.session;
                            authorizedTrainer=f.trainer;
                            authorizedPushCrc=f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE?f.crc:0;
                            directionAuthorized=true;
                            if(f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE){
                                DirectSyncProtocol.write(peer.getOutputStream(),DirectSyncProtocol.OP_READY,
                                        f.session,f.trainer,null,0,null);
                                recordConnectionEvent("Connect to Console autorizou o recebimento; homebrew liberado para enviar os dados");
                            }else{
                                recordConnectionEvent("Direção autorizada por Connect to Console: "+operationName(f.op));
                            }
                        }
                        validateAuthorizedFrame(f,directionAuthorized,authorizedTransferOperation,
                                authorizedSession,authorizedTrainer,authorizedPushCrc);
                        if(f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE) {
                            DirectSyncProtocol.readPayload(input,f);
                            assertArmCurrent(transferProfileId,authorizedArmOperation,authorizedArmGeneration);
                        } else {
                            if(f.length!=0)throw new IOException("Unexpected payload for DSi control frame");
                            DirectSyncProtocol.readPayload(input,f);
                            if(authorizedArmOperation!=0)
                                assertArmCurrent(transferProfileId,authorizedArmOperation,authorizedArmGeneration);
                        }
                    }
                    switch(f.op){
                        case DirectSyncProtocol.OP_PUSH_TO_PHONE:
                            push(peer,f,transferProfileId);
                            if(authorizedArmOperation==DirectSyncProtocol.OP_ARM_PUSH)
                                clearArmIf(transferProfileId,authorizedArmOperation,authorizedArmGeneration);
                            directionAuthorized=false;
                            break;
                        case DirectSyncProtocol.OP_PULL_FROM_PHONE:
                            returnGuard=pull(peer,f,transferProfileId);
                            awaitingReturnConfirmation=true;
                            authorizedTransferOperation=DirectSyncProtocol.OP_CONFIRM_RETURN;
                            continue; // PULL and CONFIRM_RETURN share one TCP stream.
                        case DirectSyncProtocol.OP_CONFIRM_RETURN:
                            confirm(peer,f,transferProfileId);
                            clearArmIf(transferProfileId,authorizedArmOperation,authorizedArmGeneration);
                            directionAuthorized=false;
                            break;
                        default: throw new IOException("Unknown DSi sync operation");
                    }
                    break;
                }catch(java.io.EOFException eof){
                    if(!announced){state(true,"DSi TCP closed before complete frame");recordConnectionEvent("TCP fechado antes do quadro completo");closedBeforeFrame=true;}
                    else {state(true,"DSi TCP disconnected after protocol frame");recordConnectionEvent("Cliente encerrou a sessão TCP após enviar quadro");}
                    break; // DSi disconnected normally.
                }catch(SocketTimeoutException timeout){
                    state(true,"DSi TCP timeout waiting for frame");recordConnectionEvent("Tempo esgotado aguardando quadro do DSi");
                    return;
                }catch(Exception ex){
                    if(f!=null)try{fail(peer,f,ex.getMessage()==null?"Direct sync failed":ex.getMessage());}catch(IOException ignored){}
                    String message=ex.getMessage()==null?ex.getClass().getSimpleName():ex.getMessage();
                    state(true,"Last DSi request failed: "+message);
                    if(!transferProfileId.isEmpty())WidgetConfigActivity.setStatusForProfile(this,transferProfileId,"Erro: "+message);
                    recordConnectionEvent("Quadro rejeitado: "+message);
                    return;
                }
            }
            if(!closedBeforeFrame&&running){state(true,listeningText());}
        }catch(Exception ex){state(true,"Last DSi request failed: "+ex.getMessage());recordConnectionEvent("Falha na sessão DSi: "+ex.getMessage());}
        finally{if(returnGuard!=null)returnGuard.release(this);}
    }
    private ArmedSelection awaitDirectionArm(DirectSyncProtocol.Frame f)throws IOException{
        long until=SystemClock.elapsedRealtime()+55000;
        boolean waitingLogged=false;
        int required=requiredArmOperation(f.op);
        if(required==0)throw new IOException("Unsupported DSi transfer direction");
        while(running){
            String profileId;int operation;long generation;
            synchronized(ARM_LOCK){profileId=targetProfileId;operation=armedOperation;generation=armGeneration;}
            boolean receiptOnlyRetry=f.op==DirectSyncProtocol.OP_ARM_PULL&&(f.flags&1)!=0&&
                    operation==DirectSyncProtocol.OP_ARM_PUSH;
            boolean exactPushRetry=(f.op==DirectSyncProtocol.OP_ARM_PUSH||
                    f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE)&&
                    operation==DirectSyncProtocol.OP_ARM_PULL;
            if(operation==required||receiptOnlyRetry||exactPushRetry){
                try{authorizeDirection(f,profileId,operation);}
                catch(IOException ex){
                    synchronized(ARM_LOCK){if(armGeneration!=generation)continue;}
                    throw ex;
                }
                boolean stillArmed;
                synchronized(ARM_LOCK){
                    stillArmed=armGeneration==generation&&armedOperation==operation&&
                            profileId.equals(targetProfileId);
                }
                if(stillArmed)return new ArmedSelection(profileId,operation,generation);
                continue;
            }
            if(!waitingLogged){
                state(true,"DSi waiting for Connect to Console direction");
                recordConnectionEvent("DSi aguarda o jogador armar "+armedOperationName(f.op)+" no app");
                waitingLogged=true;
            }
            if(SystemClock.elapsedRealtime()>=until)
                throw new IOException("The homebrew waited for Connect to Console, but the matching direction was not armed");
            try{Thread.sleep(200);}catch(InterruptedException ex){
                Thread.currentThread().interrupt();
                throw new IOException("Waiting for Connect to Console was interrupted");
            }
        }
        throw new IOException("Connect to Console stopped while the DSi was waiting");
    }
    private void authorizeDirection(DirectSyncProtocol.Frame f,String profileId,int operationAtAuthorization)throws IOException{
        /* A return-confirmation replay carries no Pokémon bytes and only lets
         * the DSi finish its durable local receipt after the phone already
         * saved the exact completed session. Keep this recovery path available
         * when the profile is empty and Connect therefore arms Send to phone. */
        boolean receiptOnlyRetry=f.op==DirectSyncProtocol.OP_ARM_PULL&&(f.flags&1)!=0&&
                operationAtAuthorization==DirectSyncProtocol.OP_ARM_PUSH;
        boolean exactPushRetry=(f.op==DirectSyncProtocol.OP_ARM_PUSH||
                f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE)&&
                operationAtAuthorization==DirectSyncProtocol.OP_ARM_PULL;
        int required=requiredArmOperation(f.op);
        if(required==0||(operationAtAuthorization!=required&&!receiptOnlyRetry&&!exactPushRetry))
            throw new IOException("Open Connect to Console in the app or widget and arm the matching direction first");
        if(!token(f.session))throw new IOException("Invalid DSi session identifier");
        WalkerStore target=null;
        for(WalkerStore store:WalkerStore.all(this))if(profileId.equals(store.profileId)){target=store;break;}
        if(target==null)throw new IOException("The selected app profile is unavailable");
        if(target.syncing||target.visitBlocked||target.revoked||!target.error.isEmpty())
            throw new IOException("The selected profile needs to finish recovery before syncing");
        synchronized(WalkerStore.LOCK){
            if(f.op==DirectSyncProtocol.OP_ARM_PUSH||f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE){
                if(!trainer(f.trainer))throw new IOException("Invalid HGSS trainer binding");
                if(f.op==DirectSyncProtocol.OP_ARM_PUSH){
                    if(f.flags!=0||f.length!=0||f.payload.length!=0)
                        throw new IOException("Invalid legacy Send to phone authorization frame");
                }else if(f.flags!=0||f.length!=DirectSyncProtocol.WALKER_SIZE){
                    throw new IOException("Invalid Send to phone header");
                }
                if(target.active()){
                    String crc=String.format(Locale.ROOT,"%08x",f.crc);
                    if(!"direct-dsi".equals(target.host)||!target.token.equals(f.session)||target.returnPending||
                       target.visitBlocked||!target.error.isEmpty()||!target.directCheckoutCrc.equals(crc)||
                       !target.trainerKey.equals(f.trainer)||!exactPushRetry)
                        throw new IOException("Return this profile's current Pokémon before receiving another");
                }else{
                    if(target.data!=null)throw new IOException("The selected profile is not ready to receive a Pokémon");
                    if(!target.trainerKey.isEmpty()&&!target.trainerKey.equals(f.trainer))
                        throw new IOException("Select the app profile paired with this HGSS save");
                    requireUniqueTrainerProfile(target,f.trainer);
                    if(target.completedSession(f.session))throw new IOException("This DSi session was already completed");
                }
                for(WalkerStore store:WalkerStore.all(this))
                    if(store!=target&&store.active()&&f.session.equals(store.token))
                        throw new IOException("This DSi session belongs to a different app profile");
                return;
            }
            if(f.op==DirectSyncProtocol.OP_ARM_PULL){
                if(!trainer(f.trainer)||(f.flags&~1)!=0||f.crc!=0||f.length!=0||f.payload.length!=0)
                    throw new IOException("Invalid legacy Return to HGSS authorization frame");
            }else if(f.op==DirectSyncProtocol.OP_PULL_FROM_PHONE){
                if(!trainer(f.trainer)||f.flags!=0||f.length!=0||f.crc!=0)
                    throw new IOException("Invalid Return to HGSS request header");
            }else if(f.op==DirectSyncProtocol.OP_CONFIRM_RETURN){
                if(f.flags!=0||f.length!=0)
                    throw new IOException("Invalid Return to HGSS receipt header");
            }else{
                throw new IOException("Unsupported DSi transfer direction");
            }
            String profileTrainer=target.trainerKey;
            if(profileTrainer.isEmpty()&&target.data!=null)
                profileTrainer=Native.text(target.data,4).toLowerCase(Locale.ROOT);
            boolean sameActive=target.active()&&"direct-dsi".equals(target.host)&&
                    target.token.equals(f.session)&&
                    (f.trainer.isEmpty()||profileTrainer.equals(f.trainer));
            if(f.op==DirectSyncProtocol.OP_PULL_FROM_PHONE||
               (f.op==DirectSyncProtocol.OP_ARM_PULL&&(f.flags&1)==0)){
                if(!sameActive)throw new IOException("No matching phone Pokémon is ready to return to this HGSS session");
            }else if(f.op==DirectSyncProtocol.OP_ARM_PULL){
                boolean stagedRetry=sameActive&&target.returnPending;
                boolean completedRetry=target.completedReturnSession(f.session)&&
                        (profileTrainer.isEmpty()||profileTrainer.equals(f.trainer));
                if(!stagedRetry&&!completedRetry)
                    throw new IOException("No staged return confirmation matches this DSi session");
            }else if(f.op==DirectSyncProtocol.OP_CONFIRM_RETURN){
                boolean stagedReceipt=sameActive&&target.returnPending;
                boolean completedReceipt=target.completedReturnMatches(f.session,f.crc)&&
                        (f.trainer.isEmpty()||profileTrainer.equals(f.trainer));
                if(!stagedReceipt&&!completedReceipt)
                    throw new IOException("No staged return receipt matches this DSi session");
            }
        }
    }
    private static int requiredArmOperation(int frameOperation){
        if(frameOperation==DirectSyncProtocol.OP_ARM_PUSH||
           frameOperation==DirectSyncProtocol.OP_PUSH_TO_PHONE)
            return DirectSyncProtocol.OP_ARM_PUSH;
        if(frameOperation==DirectSyncProtocol.OP_ARM_PULL||
           frameOperation==DirectSyncProtocol.OP_PULL_FROM_PHONE||
           frameOperation==DirectSyncProtocol.OP_CONFIRM_RETURN)
            return DirectSyncProtocol.OP_ARM_PULL;
        return 0;
    }
    private static void validateAuthorizedFrame(DirectSyncProtocol.Frame f,boolean authorized,
            int transferOperation,String session,String trainer,long pushCrc)throws IOException{
        if(!authorized||f.op!=transferOperation)
            throw new IOException("Connect to Console must arm this direction before Pokémon transfer");
        if(!f.session.equals(session)||
           (!f.trainer.isEmpty()&&!f.trainer.equals(trainer))||
           (f.op!=DirectSyncProtocol.OP_CONFIRM_RETURN&&!f.trainer.equals(trainer)))
            throw new IOException("Transfer frame does not match its approved session and trainer");
        if(f.op==DirectSyncProtocol.OP_PUSH_TO_PHONE&&
           (f.crc!=pushCrc||f.flags!=0||f.length!=DirectSyncProtocol.WALKER_SIZE))
            throw new IOException("Invalid Send to phone frame after direction approval");
        if(f.op==DirectSyncProtocol.OP_PULL_FROM_PHONE&&
           (f.flags!=0||f.length!=0||f.crc!=0))
            throw new IOException("Invalid Return to HGSS request after direction approval");
        if(f.op==DirectSyncProtocol.OP_CONFIRM_RETURN&&
           (f.flags!=0||f.length!=0))
            throw new IOException("Invalid Return to HGSS confirmation frame");
    }
    private void assertArmCurrent(String profileId,int operation,long generation)throws IOException{
        if(operation==0)return;
        synchronized(ARM_LOCK){
            if(armGeneration!=generation||armedOperation!=operation||
               !profileId.equals(targetProfileId))
                throw new IOException("Connect to Console was stopped or changed during transfer");
        }
    }
    private boolean completedReceipt(String profileId,DirectSyncProtocol.Frame f)throws IOException{
        if(f==null||f.op!=DirectSyncProtocol.OP_CONFIRM_RETURN||
           f.length!=0||f.flags!=0||!token(f.session))return false;
        synchronized(WalkerStore.LOCK){
            for(WalkerStore store:WalkerStore.all(this))
                if(profileId.equals(store.profileId)&&store.completedReturnMatches(f.session,f.crc))
                    return f.trainer.isEmpty()||f.trainer.equals(store.trainerKey);
        }
        return false;
    }
    private void clearArmIf(String profileId,int operation,long generation){
        synchronized(ARM_LOCK){
            if(armGeneration!=generation||armedOperation!=operation||!profileId.equals(targetProfileId))return;
            armedOperation=0;
        }
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().putInt(KEY_ARMED_OPERATION,0).apply();
        recordConnectionEvent("Transferência concluída; Connect to Console desarmado");
        shutdown();
    }
    private void clearArming(){
        synchronized(ARM_LOCK){armedOperation=0;armGeneration++;}
        getSharedPreferences(PREFS,MODE_PRIVATE).edit().putInt(KEY_ARMED_OPERATION,0).apply();
    }
    private void push(Socket peer,DirectSyncProtocol.Frame f,String profileAtAccept)throws IOException{
        if(!token(f.session)||f.length!=DirectSyncProtocol.WALKER_SIZE)
            throw new IOException("Invalid DSi checkout frame");
        if(!Native.walkable(f.payload))
            throw new IOException("DSi sent an invalid walker");
        /* Direct Sync is a Pokémon checkout, not a generic EEPROM backup.
         * Do not claim success if the uploaded walker has no Pokémon. */
        long[] details=Native.info(f.payload);
        if(details==null||details.length<=Native.HAS_POKEMON||
           details[Native.HAS_POKEMON]==0)
            throw new IOException("DSi walker contains no Pokémon for a stroll");
        String key=Native.text(f.payload,4).toLowerCase(Locale.ROOT);
        if(!trainer(key))throw new IOException("Walker trainer binding is unavailable");
        if(!f.trainer.isEmpty()&&!f.trainer.equals(key))
            throw new IOException("DSi trainer binding does not match walker data");
        final String incomingCrc=String.format(Locale.ROOT,"%08x",f.crc);
        boolean replay=false;
        final WalkerStore s;
        synchronized(WalkerStore.LOCK){
            s=storeForPush(f.session,key,profileAtAccept);
            if(s==null)throw new IOException("The selected widget profile is unavailable");
            if(s.syncing)throw new IOException("Another sync is in progress");
            if(s.active()&&"direct-dsi".equals(s.host)&&s.token.equals(f.session)){
                /* Android may have saved the full Pokémon while the DSi lost
                 * the TCP OK response. ACK this SAME checkout idempotently,
                 * even if steps changed the EEPROM since it was received.
                 * Any different payload, profile or return-in-progress fails
                 * closed rather than overwriting a walking Pokémon. */
                if(s.returnPending||s.visitBlocked||!s.error.isEmpty()||
                   s.directCheckoutCrc.isEmpty()||
                   !s.directCheckoutCrc.equals(incomingCrc)||
                   !s.trainerKey.equals(key))
                    throw new IOException("Conflicting DSi checkout retry");
                replay=true;
            } else {
                if(s.active())throw new IOException("Return the current Pokémon before receiving another");
                if(!s.trainerKey.isEmpty()&&!s.trainerKey.equals(key))
                    throw new IOException("Select the Android profile paired to this HGSS save");
                if(s.data!=null)s.archiveCurrent("direct-replaced");
                if(s.completedSession(f.session))
                    throw new IOException("This DSi session was already returned");
                /* Mark the in-memory checkout as uncommitted BEFORE changing
                 * state. If Native.resume(), recovery archiving or the
                 * AtomicFile save fails, a repeated DSi PUSH must NOT be
                 * acknowledged merely because RAM still holds its token.
                 * WalkerStore.save() clears error only after verified disk
                 * persistence, making a lost-ACK retry safe. */
                s.error="Direct checkout is not durably saved";
                s.returnCompleted=false;
                s.battlePaid=s.battleDone=s.battleRewarded=false;
                s.battleSession=s.battlePeer="";s.battleWinner=0;s.battleRewardChoice=-1;
                s.data=f.payload.clone();s.token=f.session;s.pendingToken="";
                s.trainerKey=key;s.host="direct-dsi";s.directCheckoutCrc=incomingCrc;
                s.revoked=false;s.returnPending=false;s.sensorLast=-1;s.boot=-1;s.mode=2;
                Native.resume(s.data,Native.now(),s.rate);
                s.archiveCurrent("direct-received");
                /* AtomicFile save + verification MUST complete before TCP OK. */
                s.save();
            }
        }
        if(!replay){
            WalkingService.ensureRunning(this);
            PokewalkerWidgetProvider.updateAll(this);
        }
        WidgetConfigActivity.setStatusForProfile(this,s.profileId,"Pokémon recebido pelo DSi");
        recordEvent(replay?"reenvio confirmado; Pokémon já estava salvo":"Pokémon recebido e salvo no celular");
        ok(peer,f.session,key,null,-1);
        recordConnectionEvent(replay?"PUSH repetido: Pokémon já estava salvo; OP_OK enviado":"Pokémon salvo no celular; OP_OK enviado");
    }
    private ReturnSyncGuard pull(Socket peer,DirectSyncProtocol.Frame f,String profileAtAccept)throws IOException{
        final byte[] payload;
        final String key;
        final WalkerStore store;
        final long epoch;
        synchronized(WalkerStore.LOCK){
            WalkerStore s=storeForSession(f.session);
            if(s==null)throw new IOException("DSi session does not match an Android profile");
            if(!profileAtAccept.equals(s.profileId))throw new IOException("This return belongs to a different selected app profile");
            if(s.syncing)throw new IOException("Another sync is in progress");
            if(!s.active()||!"direct-dsi".equals(s.host))
                throw new IOException("No active direct Pokémon is available to return");
            if(!f.session.equals(s.token))throw new IOException("DSi session does not match this phone walker");
            key=s.trainerKey.isEmpty()?Native.text(s.data,4).toLowerCase(Locale.ROOT):s.trainerKey;
            if(!f.trainer.isEmpty()&&!f.trainer.equals(key))
                throw new IOException("DSi trainer binding does not match this profile");
            store=s;
            epoch=s.beginSync();
            try{
                if(s.mode==1)Native.timer(s.data,Native.now(),s.rate);
                s.archiveCurrent("direct-returning");
                s.mode=0;
                s.returnPending=true;
                s.save();
                payload=s.data.clone();
            }catch(IOException|RuntimeException ex){
                s.finishSync(epoch);
                throw ex;
            }
        }
        try{
            ok(peer,f.session,key,payload,-1);
        }catch(IOException ex){
            store.finishSync(epoch);
            throw ex;
        }
        WidgetConfigActivity.setStatusForProfile(this,store.profileId,
                "Devolução enviada; aguardando confirmação do DSi");
        recordConnectionEvent("Dados do Pokémon enviados ao DSi; aguardando confirmação do HGSS");
        return new ReturnSyncGuard(store,epoch);
    }
    private void confirm(Socket peer,DirectSyncProtocol.Frame f,String profileAtAccept)throws IOException{
        final String profileId;final WalkerStore store;
        synchronized(WalkerStore.LOCK){WalkerStore s=storeForConfirmation(f.session,f.crc);
            if(s==null)throw new IOException("Return confirmation does not match an Android profile");
            if(!profileAtAccept.equals(s.profileId))throw new IOException("This return confirmation belongs to a different selected app profile");
            store=s;profileId=s.profileId;
            if(!f.trainer.isEmpty()&&!f.trainer.equals(s.trainerKey))throw new IOException("Return confirmation trainer mismatch");
            /* The DSi may have committed its EEPROM before the phone's ACK was
             * lost. Accept only an exact replay backed by the durable,
             * session-bound receipt; this never reopens or mutates the walker. */
            if(s.completedReturnMatches(f.session,f.crc)) {
                /* A previous attempt may have written the receipt and then
                 * failed while saving the cleared active state. Finish that
                 * exact session again before acknowledging its replay. */
                if(s.data!=null && f.session.equals(s.token)) {
                    if(DirectSyncProtocol.crc(s.data)!=f.crc)
                        throw new IOException("Pending return no longer matches its durable receipt");
                    s.completeReturn(f.session,s.data.clone());
                    s.data=null;s.token="";s.pendingToken="";s.directCheckoutCrc="";
                    s.revoked=false;s.returnPending=false;s.sensorLast=-1;s.mode=0;
                    s.save();
                } else if(s.data==null && s.token.isEmpty() && !s.returnPending) {
                    /* Retry an AtomicFile save that may have failed after the
                     * durable receipt was created. */
                    s.save();
                }
            }
            else {
                if(s.data==null||s.token.isEmpty()||s.revoked||!"direct-dsi".equals(s.host))throw new IOException("No direct phone walker is available for return confirmation");
                if(!f.session.equals(s.token))throw new IOException("Return confirmation session mismatch");
                long expected=DirectSyncProtocol.crc(s.data);if(f.crc!=expected)throw new IOException("DSi stored checksum does not match phone walker");
                byte[] returned=s.data.clone();s.completeReturn(s.token,returned);s.data=null;s.token="";s.pendingToken="";s.directCheckoutCrc="";s.revoked=false;s.returnPending=false;s.sensorLast=-1;s.mode=0;s.save();
            }
        }
        WidgetConfigActivity.clearStatusForProfile(this,profileId);
        PokewalkerWidgetProvider.updateAll(this);recordEvent("retorno ao jogo confirmado pelo DSi");ok(peer,f.session,f.trainer,null,f.crc);recordConnectionEvent("Retorno confirmado pelo DSi; OP_OK enviado");
    }
    private WalkerStore storeForPush(String session,String trainer,String preferredProfileId)throws IOException{
        java.util.ArrayList<WalkerStore> stores=WalkerStore.all(this);
        for(WalkerStore store:stores)
            if(store.active()&&session.equals(store.token))return store;
        for(WalkerStore store:stores)
            if(store.completedSession(session))throw new IOException("This DSi session was already returned");
        for(WalkerStore store:stores)if(preferredProfileId.equals(store.profileId)){
            if(!store.trainerKey.isEmpty()&&!store.trainerKey.equals(trainer))
                throw new IOException("Select the widget profile paired with this HGSS save");
            requireUniqueTrainerProfile(store,trainer);
            return store;
        }
        return null;
    }
    private void requireUniqueTrainerProfile(WalkerStore target,String trainer)throws IOException{
        for(WalkerStore store:WalkerStore.all(this))
            if(!store.profileId.equals(target.profileId)&&!store.trainerKey.isEmpty()&&store.trainerKey.equals(trainer))
                throw new IOException("This HGSS trainer is already paired with profile "+profileName(store.profileId)+". Use that profile to avoid mixing saves.");
    }
    private WalkerStore storeForSession(String session){
        for(WalkerStore store:WalkerStore.all(this))if(session.equals(store.token))return store;
        return null;
    }
    private WalkerStore storeForConfirmation(String session,long crc)throws IOException{
        WalkerStore active=storeForSession(session);
        if(active!=null)return active;
        for(WalkerStore store:WalkerStore.all(this))if(store.completedReturnMatches(session,crc))return store;
        return null;
    }
    private void ok(Socket peer,String session,String trainer,byte[] payload,long crc)throws IOException{DirectSyncProtocol.write(peer.getOutputStream(),DirectSyncProtocol.OP_OK,session,trainer,payload,crc,null);}
    private void fail(Socket peer,DirectSyncProtocol.Frame f,String message)throws IOException{DirectSyncProtocol.write(peer.getOutputStream(),DirectSyncProtocol.OP_ERROR,f.session,f.trainer,null,-1,message);}
    private void shutdown(){running=false;listeningReady=false;clearArming();try{if(server!=null)server.close();}catch(IOException ignored){}state(false,"Stopped");recordConnectionEvent("Receptor parado e direção desarmada");stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
    @Override public void onDestroy(){
        // Do not clear the persisted arm here: Android may destroy this
        // foreground service during an app update or process reclaim and then
        // restart it with a null Intent. Explicit Stop and listener failure
        // already clear the direction before this callback.
        preservingArmForRestart=true;running=false;listeningReady=false;
        try{if(server!=null)server.close();}catch(IOException ignored){}
        if(liveService==this)liveService=null;
        super.onDestroy();
    }
    @Override public android.os.IBinder onBind(Intent intent){return null;}
}
