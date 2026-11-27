package io.github.sdtransporter.pokewalker;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.hardware.*;
import android.os.*;
import android.provider.Settings;
import java.util.*;
public final class WalkingService extends Service implements SensorEventListener {
    private static final long TIMER_INTERVAL_MS=60_000L;
    private SensorManager sensors;private int boot;private long lastWidgetUpdate,lastCounterUpdate,lastBatterySample;
    private boolean physical,timers;
    private final HashMap<String,String> running=new HashMap<>();
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable tick=new Runnable(){public void run(){
        long elapsed=SystemClock.elapsedRealtime();
        boolean anyTracking=false;
        synchronized(WalkerStore.LOCK){
            if(lastCounterUpdate==0||elapsed-lastCounterUpdate>=TIMER_INTERVAL_MS){
                for(WalkerStore s:WalkerStore.all(WalkingService.this))if(s.tracking()){anyTracking=true;s.creditTimer(Native.now());}
                lastCounterUpdate=elapsed;
            } else {for(WalkerStore s:WalkerStore.all(WalkingService.this))if(s.tracking()){anyTracking=true;break;}}
        }
        boolean widgets=PokewalkerWidgetProvider.hasWidgets(WalkingService.this);
        if(!anyTracking&&!widgets){stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();return;}
        // This is the persistent animation clock. Unlike a Handler owned by an
        // AppWidgetProvider, a foreground service survives launcher inactivity.
        if(widgets)PokewalkerWidgetProvider.updateAnimatedFrames(WalkingService.this);
        if(elapsed-lastBatterySample>=900_000L){Diagnostics.sample(WalkingService.this,false);lastBatterySample=elapsed;}
        handler.postDelayed(this,widgets?400L:TIMER_INTERVAL_MS);
    }};

    static void ensureRunning(Context c){
        Intent i=new Intent(c,WalkingService.class);
        try{if(Build.VERSION.SDK_INT>=26)c.startForegroundService(i);else c.startService(i);}catch(Exception ignored){}
    }
    @Override public void onCreate(){super.onCreate();sensors=(SensorManager)getSystemService(SENSOR_SERVICE);boot=Settings.Global.getInt(getContentResolver(),Settings.Global.BOOT_COUNT,-1);
        Diagnostics.event(this,"TRACKING","Tracking service started");
        Diagnostics.sample(this,false);
        ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).createNotificationChannel(new NotificationChannel("walking","Walking",NotificationManager.IMPORTANCE_LOW));}
    @Override public int onStartCommand(Intent intent,int flags,int id){
        synchronized(WalkerStore.LOCK){
            handler.removeCallbacks(tick);sensors.unregisterListener(this);physical=timers=false;
            ArrayList<WalkerStore> all=WalkerStore.all(this);
            // A service start is a fresh tracking attempt. Sensor and Android
            // permission failures are transient and must never poison save state.
            for(WalkerStore s:all)s.trackingIssue="";
            if(intent!=null&&"pause".equals(intent.getAction())){
                for(WalkerStore s:all){if(s.tracking()&&s.mode==1)Native.timer(s.data,Native.now(),s.rate);s.mode=0;s.changed();}
                if(PokewalkerWidgetProvider.hasWidgets(this)){physical=false;timers=false;try{notice(true);}catch(Exception ignored){}handler.post(tick);return START_STICKY;}
                stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();return START_NOT_STICKY;
            }
            boolean sensorOK=Build.VERSION.SDK_INT<29||checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION)==PackageManager.PERMISSION_GRANTED;
            Sensor sensor=sensors.getDefaultSensor(Sensor.TYPE_STEP_COUNTER);sensorOK&=sensor!=null;
            for(WalkerStore s:all){
                if(s.tracking()&&s.mode==2&&!sensorOK){s.trackingIssue="Physical step counting is unavailable. Allow activity access or select a time-based mode.";running.remove(s.profileId);continue;}
                if(!s.tracking()){running.remove(s.profileId);continue;}
                if(!s.token.equals(running.get(s.profileId))){Native.resume(s.data,Native.now(),s.rate);s.changed();running.put(s.profileId,s.token);}
                if(s.mode==2){if(s.boot!=boot||SystemClock.elapsedRealtime()<s.sensorElapsed)s.sensorLast=-1;s.boot=boot;physical=true;}else timers=true;
            }
            if(physical&&!sensors.registerListener(this,sensor,SensorManager.SENSOR_DELAY_NORMAL)){
                for(WalkerStore s:all)if(s.tracking()&&s.mode==2){s.trackingIssue="The phone step counter could not be enabled.";running.remove(s.profileId);}physical=false;
            }
            boolean widgetOnly=!physical&&!timers&&PokewalkerWidgetProvider.hasWidgets(this);
            if(!physical&&!timers&&!widgetOnly){stopSelf();return START_NOT_STICKY;}
            try{notice(true);}catch(SecurityException ex){Diagnostics.error(this,"TRACKING_PERMISSION",ex);for(WalkerStore s:all)if(s.active()&&s.mode!=0)s.trackingIssue="Tracking notification unavailable: "+ex.getMessage();stopSelf();return START_NOT_STICKY;}
            handler.post(tick);
        }
        Diagnostics.event(this,"TRACKING","Service mode: timer="+timers+" physical="+physical+" widget="+PokewalkerWidgetProvider.hasWidgets(this));
        return START_STICKY;
    }
    private void notice(boolean start){
        int count=0;for(WalkerStore s:WalkerStore.all(this))if(s.tracking())count++;
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent pause=PendingIntent.getService(this,1,new Intent(this,WalkingService.class).setAction("pause"),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        boolean widgetOnly=count==0&&PokewalkerWidgetProvider.hasWidgets(this);
        String title=widgetOnly?"Pokewalker widget active":"Pokewalker · "+count+" active profile"+(count==1?"":"s");
        String detail=widgetOnly?"Keeping the Pokéwalker LCD animation alive.":"All active profiles earn steps. Tap to view your walkers.";
        Notification n=new Notification.Builder(this,"walking").setSmallIcon(R.drawable.ic_stat_walker).setContentTitle(title)
            .setContentText(detail).setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
            .addAction(new Notification.Action.Builder(android.R.drawable.ic_media_pause,"Pause all",pause).build()).build();
        if(start){if(Build.VERSION.SDK_INT>=34){int type=(physical?ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH:0)|((timers||widgetOnly)?ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE:0);startForeground(1,n,type);}else startForeground(1,n);}
        else ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(1,n);
    }
    @Override public void onSensorChanged(SensorEvent event){
        if(event.sensor.getType()!=Sensor.TYPE_STEP_COUNTER)return;
        synchronized(WalkerStore.LOCK){for(WalkerStore s:WalkerStore.all(this))if(s.tracking()&&s.mode==2){
            s.creditPhysical((long)event.values[0],SystemClock.elapsedRealtime(),boot);
        }}
        if(SystemClock.elapsedRealtime()-lastWidgetUpdate>=1500){PokewalkerWidgetProvider.updateAll(this);lastWidgetUpdate=SystemClock.elapsedRealtime();}
    }
    @Override public void onAccuracyChanged(Sensor sensor,int accuracy){}
    @Override public void onDestroy(){handler.removeCallbacks(tick);if(sensors!=null)sensors.unregisterListener(this);synchronized(WalkerStore.LOCK){for(WalkerStore s:WalkerStore.all(this))if(s.data!=null)s.changed();}Diagnostics.event(this,"TRACKING","Tracking service stopped");super.onDestroy();}
    @Override public IBinder onBind(Intent intent){return null;}
}
