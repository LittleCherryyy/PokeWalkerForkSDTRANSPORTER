package io.github.sdtransporter.pokewalker;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.widget.RemoteViews;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import java.util.Base64;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Home-screen version of the app's Classic mode.
 *
 * The LCD is not re-created with Android text/views.  It is the exact 96x64
 * framebuffer returned by Native.classicFrame(), i.e. the same walkerclassic
 * core used by MainActivity.  The three transparent hit targets map to the
 * Pokéwalker's left/centre/right buttons.  Tapping the LCD sends the app's
 * "held centre" action because Android launchers reserve a real long-press for
 * moving/resizing widgets.
 */
public final class PokewalkerWidgetProvider extends AppWidgetProvider {
    static final String ACTION_LEFT   = "io.github.sdtransporter.pokewalker.WIDGET_CLASSIC_LEFT";
    static final String ACTION_CENTER = "io.github.sdtransporter.pokewalker.WIDGET_CLASSIC_CENTER";
    static final String ACTION_RIGHT  = "io.github.sdtransporter.pokewalker.WIDGET_CLASSIC_RIGHT";
    static final String ACTION_BACK   = "io.github.sdtransporter.pokewalker.WIDGET_CLASSIC_BACK";
    static final String ACTION_REFRESH= "io.github.sdtransporter.pokewalker.WIDGET_CLASSIC_REFRESH";

    private static final String TAG="PokewalkerWidget";
    private static final ExecutorService EXEC=Executors.newCachedThreadPool();
    private static final Handler ANIM=new Handler(Looper.getMainLooper());
    private static final long HOME_FRAME_MS=400L;
    private static boolean animationScheduled;
    private static Context animationContext;
    private static final Runnable animationTick=new Runnable(){@Override public void run(){
        animationScheduled=false;
        Context c=animationContext;
        if(c==null)return;
        AppWidgetManager m=AppWidgetManager.getInstance(c);
        int[] ids=m.getAppWidgetIds(new ComponentName(c,PokewalkerWidgetProvider.class));
        if(ids.length==0){animationContext=null;return;}
        boolean any=false;
        for(int id:ids)try{if(renderAnimatedFrame(c,m,id))any=true;}catch(Throwable e){Log.w(TAG,"Widget animation frame failed",e);}
        if(any)ensureAnimation(c);
    }};
    private static final String STATE_PREFS="pokewalker_widget_classic";
    private static final int VIEW=0, SEL=1, SUB=2, SOUND=10, VOLUME=19, CONTRAST=20;
    private static final int HOME=0, CONNECT=8, PEERS=10;

    @Override public void onUpdate(Context c,AppWidgetManager m,int[] ids){for(int id:ids)safeRender(c,m,id);ensureAnimation(c);WalkingService.ensureRunning(c);}
    @Override public void onAppWidgetOptionsChanged(Context c,AppWidgetManager m,int id,Bundle options){safeRender(c,m,id);ensureAnimation(c);}
    @Override public void onDeleted(Context c,int[] ids){for(int id:ids){WidgetConfigActivity.clearProfileFor(c,id);SkinManager.clearWidgetSkin(c,id);clearClassic(c,id);}if(AppWidgetManager.getInstance(c).getAppWidgetIds(new ComponentName(c,PokewalkerWidgetProvider.class)).length==0)stopAnimation();}

    @Override public void onReceive(Context context,Intent intent){
        super.onReceive(context,intent);
        String action=intent.getAction();
        if(action==null)return;
        int id=intent.getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,AppWidgetManager.INVALID_APPWIDGET_ID);
        if(id==AppWidgetManager.INVALID_APPWIDGET_ID)return;
        int button;
        if(ACTION_LEFT.equals(action))button=0;
        else if(ACTION_CENTER.equals(action))button=1;
        else if(ACTION_RIGHT.equals(action))button=2;
        else if(ACTION_BACK.equals(action))button=3;
        else if(ACTION_REFRESH.equals(action)){safeRender(context,AppWidgetManager.getInstance(context),id);return;}
        else return;

        final PendingResult pending=goAsync();
        final Context app=context.getApplicationContext();
        EXEC.execute(()->{
            try{handleClassicInput(app,id,button);}catch(Throwable e){Log.e(TAG,"Classic widget input failed",e);Diagnostics.error(app,"WIDGET_INPUT",e);WidgetConfigActivity.setStatus(app,id,"Erro: "+shortMessage(e));}
            finally{safeRender(app,AppWidgetManager.getInstance(app),id);ensureAnimation(app);pending.finish();}
        });
    }

    static void updateWidget(Context c,AppWidgetManager m,int id){safeRender(c,m,id);ensureAnimation(c);}
    static void updateAll(Context c){AppWidgetManager m=AppWidgetManager.getInstance(c);for(int id:m.getAppWidgetIds(new ComponentName(c,PokewalkerWidgetProvider.class)))safeRender(c,m,id);ensureAnimation(c);}
    /** Called by the foreground walking service every 400 ms so animation does
     * not depend on the AppWidgetProvider process staying resident. */
    static void updateAnimatedFrames(Context c){
        AppWidgetManager m=AppWidgetManager.getInstance(c);
        for(int id:m.getAppWidgetIds(new ComponentName(c,PokewalkerWidgetProvider.class)))
            try{renderAnimatedFrame(c,m,id);}catch(Throwable e){Log.w(TAG,"Service animation frame failed",e);}
    }
    static boolean hasWidgets(Context c){
        return AppWidgetManager.getInstance(c).getAppWidgetIds(new ComponentName(c,PokewalkerWidgetProvider.class)).length>0;
    }
    static void resetClassic(Context c,int id){clearClassic(c,id);safeRender(c,AppWidgetManager.getInstance(c),id);}

    private static synchronized void ensureAnimation(Context c){
        animationContext=c.getApplicationContext();
        if(animationScheduled)return;
        animationScheduled=true;
        ANIM.postDelayed(animationTick,HOME_FRAME_MS);
    }

    private static synchronized void stopAnimation(){
        animationScheduled=false;
        animationContext=null;
        ANIM.removeCallbacks(animationTick);
    }

    /**
     * Refresh only the 96x64 LCD bitmap.  walkerClassicFrame() changes the
     * HOME Pokemon frame every 400 ms (frame=(ms/400)&1), so this is the exact
     * animation cadence used by the firmware instead of an Android-side sprite.
     */
    private static boolean renderAnimatedFrame(Context c,AppWidgetManager m,int id){
        String profileId=WidgetConfigActivity.profileFor(c,id);
        WalkerStore store=findStore(c,profileId);
        recoverOrphanedTransfer(c,id,store);
        if(store==null||!store.active()||store.syncing||store.returnPending||!store.error.isEmpty())return false;
        int layout=layoutForSize(m,id);
        int[] screen=screenSize(layout);
        int[] classic=loadClassic(c,id,store);
        byte[] pixels;
        synchronized(WalkerStore.LOCK){
            // Keep the native Classic controller alive even when the user never
            // touches the widget. This advances timed firmware states and keeps
            // the same state clock used by the in-app Classic view.
            byte[] before=store.data.clone();
            Native.classicInput(store.data,classic,-1,Native.now(),SystemClock.elapsedRealtime(),store.expandedItems);
            if(!Arrays.equals(before,store.data))try{store.save();}catch(IOException ignored){}
            saveClassic(c,id,classic);
            pixels=Native.classicFrame(store.data,classic,SystemClock.elapsedRealtime());
        }
        Bitmap lcd=frameBitmap(pixels,store.classicContrast,screen[0],screen[1],c.getResources().getDisplayMetrics().density);
        RemoteViews frame=new RemoteViews(c.getPackageName(),layout);
        frame.setImageViewBitmap(R.id.widget_lcd,lcd);
        m.partiallyUpdateAppWidget(id,frame);
        return true;
    }

    private static void handleClassicInput(Context c,int id,int button) throws Exception {
        String profileId=WidgetConfigActivity.profileFor(c,id);
        WalkerStore store=findStore(c,profileId);
        if(store==null)throw new IOException("Perfil indisponível");
        recoverOrphanedTransfer(c,id,store);
        if(store.syncing)throw new IOException("Sincronização em andamento");
        if(store.returnPending)throw new IOException("Devolução aguardando confirmação");
        if(!store.error.isEmpty())throw new IOException(store.error);
        if(!store.active()){
            // An empty Pokéwalker cannot boot the classic firmware.  The centre
            // button starts the same console receive flow the CONNECT/CONSOLE
            // menu uses when a walker is already active.
            if(button==1){startConsoleTransfer(c,id,store,false);return;}
            throw new IOException("Sem Pokémon — pressione o botão central para receber");
        }

        int[] classic=loadClassic(c,id,store);
        byte[] before;
        int score=-1;
        synchronized(WalkerStore.LOCK){
            before=store.data.clone();
            Native.classicInput(store.data,classic,button,Native.now(),SystemClock.elapsedRealtime(),store.expandedItems);
            store.classicVolume=classic[VOLUME];
            store.classicContrast=classic[CONTRAST];
            if(classic[SOUND]>0){score=classic[SOUND]-1;classic[SOUND]=0;}
            if(!Arrays.equals(before,store.data)){
                boolean reward=false;
                for(int n=0xce8c;n<0xcef0;n++)if(before[n]!=store.data[n]){reward=true;break;}
                if(reward)store.archiveCurrent("reward");
                store.save();
            } else {
                // Volume/contrast live outside EEPROM and still need persisting.
                store.save();
            }
            saveClassic(c,id,classic);
        }
        if(score>=0)playScoreAsync(store,score,classic[VOLUME]);

        // Exactly the same hand-off MainActivity performs when Classic mode
        // confirms CONNECT -> CONSOLE.  The widget chooses receive/return from
        // the currently bound profile state.
        if(classic[VIEW]==CONNECT && classic[SUB]==1){
            boolean returning=store.active();
            classic[VIEW]=HOME;classic[SEL]=0;classic[SUB]=0;saveClassic(c,id,classic);
            startConsoleTransfer(c,id,store,returning);
            return;
        }

        // OTHER WALKER needs Bluetooth/profile-discovery UI, which a RemoteViews
        // widget cannot host. Keep the firmware screen intact and show a short
        // hint instead of silently opening the whole app.
        if(classic[VIEW]==PEERS){
            classic[VIEW]=CONNECT;classic[SEL]=1;classic[SUB]=0;saveClassic(c,id,classic);
            WidgetConfigActivity.clearStatus(c,id);
            try{c.startActivity(new Intent(c,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("widget_open_connect",true));}
            catch(Exception ex){WidgetConfigActivity.setStatus(c,id,"OTHER WALKER: abra o app");}
        } else WidgetConfigActivity.clearStatus(c,id);

        // The classic core has timed screens (radar, battle, dowsing).  Tick it
        // briefly after each interaction so animations/deadlines progress even
        // though an AppWidget has no continuous View.invalidate() loop.
        scheduleTicks(c,id,profileId);
    }

    private static void scheduleTicks(Context c,int id,String profileId){
        EXEC.execute(()->{
            for(int frame=0;frame<18;frame++){
                try{Thread.sleep(110);}catch(InterruptedException e){Thread.currentThread().interrupt();return;}
                WalkerStore s=findStore(c,profileId);if(s==null||!s.active()||s.syncing||s.returnPending)return;
                int[] classic=loadClassic(c,id,s);
                synchronized(WalkerStore.LOCK){
                    byte[] before=s.data.clone();
                    Native.classicInput(s.data,classic,-1,Native.now(),SystemClock.elapsedRealtime(),s.expandedItems);
                    if(!Arrays.equals(before,s.data))try{s.save();}catch(IOException ignored){}
                    saveClassic(c,id,classic);
                }
                safeRender(c,AppWidgetManager.getInstance(c),id);
            }
        });
    }

    private static void startConsoleTransfer(Context c,int id,WalkerStore store,boolean returning) throws IOException {
        String host=WidgetConfigActivity.hostFor(c,id);
        if(host.isEmpty())throw new IOException("Configure o IP do console no widget");
        WidgetConfigActivity.setStatus(c,id,returning?"Devolvendo…":"Recebendo…");
        Intent service=new Intent(c,WidgetTransferService.class)
            .setAction(returning?WidgetTransferService.ACTION_RETURN:WidgetTransferService.ACTION_RECEIVE)
            .putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,id)
            .putExtra(WidgetTransferService.EXTRA_PROFILE_ID,store.profileId)
            .putExtra(WidgetTransferService.EXTRA_HOST,host);
        try{c.startForegroundService(service);}catch(Exception ex){throw new IOException("Não foi possível iniciar a sincronização: "+shortMessage(ex));}
    }

    private static void safeRender(Context c,AppWidgetManager m,int id){try{render(c.getApplicationContext(),m,id);}catch(Throwable e){Log.e(TAG,"Widget render failed",e);showFallback(c,m,id,"Toque para configurar");}}

    private static void render(Context c,AppWidgetManager m,int id){
        int layout=layoutForSize(m,id);
        RemoteViews v=new RemoteViews(c.getPackageName(),layout);
        String profileIdForSkin=WidgetConfigActivity.profileFor(c,id);
        v.setImageViewResource(R.id.widget_shell,SkinManager.resource(SkinManager.widgetSkin(c,id,profileIdForSkin)));
        v.setOnClickPendingIntent(R.id.widget_left,broadcast(c,id,ACTION_LEFT,11));
        v.setOnClickPendingIntent(R.id.widget_center,broadcast(c,id,ACTION_CENTER,12));
        v.setOnClickPendingIntent(R.id.widget_right,broadcast(c,id,ACTION_RIGHT,13));
        // Android launchers consume long-press for widget move/resize. Tapping
        // the LCD is therefore the widget equivalent of holding centre/back.
        String profileId=WidgetConfigActivity.profileFor(c,id);
        WalkerStore store=findStore(c,profileId);
        recoverOrphanedTransfer(c,id,store);
        int[] screen=screenSize(layout);
        float density=c.getResources().getDisplayMetrics().density;
        Bitmap lcd;
        int view=HOME;
        if(store==null)lcd=statusBitmap("CONFIGURE", "THE WIDGET",screen[0],screen[1],density);
        else if(store.syncing)lcd=statusBitmap("CONNECT", trimStatus(WidgetConfigActivity.statusFor(c,id)),screen[0],screen[1],density);
        else if(!store.error.isEmpty())lcd=statusBitmap("ERROR", "OPEN APP",screen[0],screen[1],density);
        else if(!store.active())lcd=statusBitmap("NO POKEMON", "PRESS CENTER",screen[0],screen[1],density);
        else {
            int[] classic=loadClassic(c,id,store);view=classic[VIEW];
            synchronized(WalkerStore.LOCK){
                byte[] pixels=Native.classicFrame(store.data,classic,SystemClock.elapsedRealtime());
                lcd=frameBitmap(pixels,store.classicContrast,screen[0],screen[1],density);
            }
            String status=WidgetConfigActivity.statusFor(c,id);
            if(!status.isEmpty()&&status.startsWith("Erro:"))lcd=statusBitmap("SYNC ERROR",trimStatus(status.substring(5)),screen[0],screen[1],density);
        }
        if(store==null || !store.active() || view==HOME){
            Intent cfg=new Intent(c,WidgetConfigActivity.class).putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,id);
            v.setOnClickPendingIntent(R.id.widget_screen_touch,PendingIntent.getActivity(c,10000+id,cfg,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT));
        } else v.setOnClickPendingIntent(R.id.widget_screen_touch,broadcast(c,id,ACTION_BACK,14));
        v.setImageViewBitmap(R.id.widget_lcd,lcd);
        m.updateAppWidget(id,v);
    }

    private static Bitmap frameBitmap(byte[] pixels,int contrast,int widthDp,int heightDp,float density){
        int w=Math.max(96,Math.round(widthDp*density)),h=Math.max(64,Math.round(heightDp*density));
        Bitmap b=Bitmap.createBitmap(w,h,Bitmap.Config.RGB_565);
        int[][] shades={{0xffb4b7aa,0xff9a9f91,0xff787e6f,0xff535b4b},{0xffb4b7aa,0xff8d9383,0xff555e4c,0xff232b1d},{0xffb4b7aa,0xff7f8675,0xff3e4835,0xff10180d}};
        int[] colors=shades[Math.max(0,Math.min(2,contrast))];
        int[] out=new int[w*h];
        for(int y=0;y<h;y++){int sy=Math.min(63,y*64/h);for(int x=0;x<w;x++){int sx=Math.min(95,x*96/w);int at=sy*96+sx;out[y*w+x]=colors[(pixels!=null&&at<pixels.length)?pixels[at]&3:0];}}
        b.setPixels(out,0,w,0,0,w,h);return b;
    }

    // Small fallback/status framebuffer. Normal operation always uses
    // Native.classicFrame(); this is only for configuration/sync/error states.
    private static Bitmap statusBitmap(String top,String bottom,int widthDp,int heightDp,float density){
        int w=Math.max(96,Math.round(widthDp*density)),h=Math.max(64,Math.round(heightDp*density));
        Bitmap b=Bitmap.createBitmap(w,h,Bitmap.Config.RGB_565);b.eraseColor(0xffb4b7aa);
        android.graphics.Canvas c=new android.graphics.Canvas(b);android.graphics.Paint p=new android.graphics.Paint();p.setAntiAlias(false);p.setColor(0xff232b1d);p.setTypeface(android.graphics.Typeface.MONOSPACE);p.setTextAlign(android.graphics.Paint.Align.CENTER);p.setFakeBoldText(true);p.setTextSize(11f*h/64f);c.drawText(top,w/2f,24f*h/64f,p);p.setFakeBoldText(false);p.setTextSize(8f*h/64f);c.drawText(bottom,w/2f,44f*h/64f,p);return b;
    }

    private static int[] screenSize(int layout){
        if(layout==R.layout.widget_pokewalker_440)return new int[]{242,169};
        if(layout==R.layout.widget_pokewalker_400)return new int[]{220,154};
        if(layout==R.layout.widget_pokewalker_360)return new int[]{198,138};
        if(layout==R.layout.widget_pokewalker_xxlarge)return new int[]{176,123};
        if(layout==R.layout.widget_pokewalker_xlarge)return new int[]{154,108};
        if(layout==R.layout.widget_pokewalker_large)return new int[]{132,92};
        if(layout==R.layout.widget_pokewalker_medium)return new int[]{110,77};
        return new int[]{88,61};
    }

    private static String trimStatus(String s){if(s==null||s.isEmpty())return "PLEASE WAIT";s=s.replace('✓',' ');return s.length()>18?s.substring(0,18):s;}

    /**
     * returnPending is persisted for crash safety, while syncing is intentionally
     * process-local.  If Android kills/restarts the process during a failed return,
     * the old code could therefore reload an active walker with returnPending=true
     * and syncing=false forever.  That orphaned lock blocked every button and also
     * stopped the 400 ms HOME animation.
     *
     * An active transfer in this process always has syncing=true.  So an active
     * walker that is returnPending without syncing has no transfer left to finish
     * and can safely be restored to walking mode.
     */
    private static void recoverOrphanedTransfer(Context c,int id,WalkerStore store){
        if(store==null||store.syncing||!store.returnPending||!store.active())return;
        synchronized(WalkerStore.LOCK){
            if(store.syncing||!store.returnPending||!store.active())return;
            store.returnPending=false;
            if(store.mode==0)store.mode=2;
            try{store.save();}catch(IOException e){Log.w(TAG,"Could not persist orphaned transfer recovery",e);}
        }
        WidgetConfigActivity.clearStatus(c,id);
        clearClassic(c,id);
    }

    private static WalkerStore findStore(Context c,String profileId){for(WalkerStore s:WalkerStore.all(c))if(s.profileId.equals(profileId))return s;return null;}

    private static int[] loadClassic(Context c,int id,WalkerStore store){
        int[] out=new int[40];out[VOLUME]=store.classicVolume;out[CONTRAST]=store.classicContrast;
        String encoded=c.getSharedPreferences(STATE_PREFS,Context.MODE_PRIVATE).getString("state_"+id,"");
        if(!encoded.isEmpty())try{
            byte[] raw=Base64.getDecoder().decode(encoded);if(raw.length==160){ByteBuffer bb=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);for(int n=0;n<40;n++)out[n]=bb.getInt();}
        }catch(Exception ignored){}
        // Always follow profile-level settings, like MainActivity does.
        out[VOLUME]=store.classicVolume;out[CONTRAST]=store.classicContrast;return out;
    }
    private static void saveClassic(Context c,int id,int[] s){ByteBuffer bb=ByteBuffer.allocate(160).order(ByteOrder.LITTLE_ENDIAN);for(int n=0;n<40;n++)bb.putInt(s[n]);c.getSharedPreferences(STATE_PREFS,Context.MODE_PRIVATE).edit().putString("state_"+id,Base64.getEncoder().encodeToString(bb.array())).apply();}
    private static void clearClassic(Context c,int id){c.getSharedPreferences(STATE_PREFS,Context.MODE_PRIVATE).edit().remove("state_"+id).apply();}

    private static void playScoreAsync(WalkerStore store,int score,int volume){
        if(volume<=0||store.data==null)return;byte[] data=store.data.clone();
        EXEC.execute(()->{android.media.AudioTrack audio=null;try{short[] pcm=Native.classicSound(data,score);if(pcm==null||pcm.length==0)return;audio=new android.media.AudioTrack.Builder().setAudioAttributes(new android.media.AudioAttributes.Builder().setUsage(android.media.AudioAttributes.USAGE_GAME).setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION).build()).setAudioFormat(new android.media.AudioFormat.Builder().setSampleRate(22050).setChannelMask(android.media.AudioFormat.CHANNEL_OUT_MONO).setEncoding(android.media.AudioFormat.ENCODING_PCM_16BIT).build()).setTransferMode(android.media.AudioTrack.MODE_STATIC).setBufferSizeInBytes(pcm.length*2).build();audio.setVolume(volume==1?.25f:.5f);audio.write(pcm,0,pcm.length);audio.play();Thread.sleep(Math.min(12000,50+pcm.length*1000L/22050));}catch(Exception ignored){}finally{if(audio!=null)try{audio.release();}catch(Exception ignored){}}});
    }

    private static int layoutForSize(AppWidgetManager manager,int id){
        Bundle o=manager.getAppWidgetOptions(id);
        int w=o.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH,160);
        int h=o.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT,160);
        int side=Math.min(w,h);
        if(side>=420)return R.layout.widget_pokewalker_440;
        if(side>=380)return R.layout.widget_pokewalker_400;
        if(side>=340)return R.layout.widget_pokewalker_360;
        if(side>=300)return R.layout.widget_pokewalker_xxlarge;
        if(side>=260)return R.layout.widget_pokewalker_xlarge;
        if(side>=220)return R.layout.widget_pokewalker_large;
        if(side>=175)return R.layout.widget_pokewalker_medium;
        return R.layout.widget_pokewalker;
    }
    private static PendingIntent broadcast(Context c,int id,String action,int salt){Intent i=new Intent(c,PokewalkerWidgetProvider.class).setAction(action).putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,id);return PendingIntent.getBroadcast(c,id*100+salt,i,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);}
    private static void showFallback(Context c,AppWidgetManager m,int id,String msg){try{RemoteViews f=new RemoteViews(c.getPackageName(),R.layout.widget_pokewalker_fallback);f.setTextViewText(R.id.widget_fallback_text,msg);Intent cfg=new Intent(c,WidgetConfigActivity.class).putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,id);f.setOnClickPendingIntent(R.id.widget_fallback_root,PendingIntent.getActivity(c,20000+id,cfg,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT));m.updateAppWidget(id,f);}catch(Throwable e){Log.e(TAG,"Fallback failed",e);}}
    private static String shortMessage(Throwable e){String s=e.getMessage();return s==null||s.isEmpty()?e.getClass().getSimpleName():s;}
}
