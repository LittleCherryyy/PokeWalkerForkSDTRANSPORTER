package io.github.sdtransporter.pokewalker;

import android.content.*;
import android.os.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

/** Private, local-only diagnostics. No uploads, no Pokemon payloads or save bytes. */
public final class Diagnostics {
    private static final Object LOCK=new Object();
    private static final long MAX_BYTES=512*1024;
    private static volatile boolean installed;
    private static volatile long lastSample=0;
    private static final long SAMPLE_MS=15*60*1000L;
    private Diagnostics(){}
    private static File current(Context ctx){return new File(ctx.getFilesDir(),"diagnostics.log");}
    private static File previous(Context ctx){return new File(ctx.getFilesDir(),"diagnostics.previous.log");}
    private static String stamp(){return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS Z",Locale.US).format(new Date());}
    public static void event(Context c,String kind,String message){
        if(c==null)return;
        synchronized(LOCK){
            try {
                File file=current(c);
                if(file.exists() && file.length()>MAX_BYTES){File old=previous(c);if(old.exists())old.delete();file.renameTo(old);}
                String safe=(message==null?"":message).replace('\r',' ').replace('\n',' ');
                if(safe.length()>600)safe=safe.substring(0,600)+" [truncated]";
                try(FileOutputStream f=new FileOutputStream(file,true)){
                    f.write((stamp()+" ["+kind+"] "+safe+"\n").getBytes("UTF-8"));
                    f.flush();
                }
            }catch(Exception ignored){} // diagnostics must never break the main app
        }
    }
    public static void error(Context c,String component,Throwable t){
        if(t==null)return;
        event(c,"ERROR",component+" "+t.getClass().getName()+": "+t.getMessage());
        StackTraceElement[] trace=t.getStackTrace();
        for(int i=0;i<Math.min(trace.length,10);i++)event(c,"TRACE",trace[i].toString());
    }
    public static void install(Context context){
        if(installed)return;
        synchronized(LOCK){
            if(installed)return;
            final Context app=context.getApplicationContext();
            final Thread.UncaughtExceptionHandler original=Thread.getDefaultUncaughtExceptionHandler();
            Thread.setDefaultUncaughtExceptionHandler((thread,error)->{
                try{event(app,"CRASH","Uncaught exception in "+thread.getName());error(app,"UNCAUGHT",error);}catch(Throwable ignored){}
                if(original!=null)original.uncaughtException(thread,error);
                else {android.os.Process.killProcess(android.os.Process.myPid());System.exit(10);}
            });
            installed=true;
        }
    }
    public static String battery(Context c){
        Intent i=c.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(i==null)return "Battery status unavailable";
        int level=i.getIntExtra(BatteryManager.EXTRA_LEVEL,-1),scale=i.getIntExtra(BatteryManager.EXTRA_SCALE,-1);
        int plugged=i.getIntExtra(BatteryManager.EXTRA_PLUGGED,0);
        String pct=(level>=0&&scale>0)?String.format(Locale.US,"%.1f%%",100.0*level/scale):"unknown";
        StringBuilder s=new StringBuilder("Level="+pct+"; charging="+(plugged!=0));
        BatteryManager bm=(BatteryManager)c.getSystemService(Context.BATTERY_SERVICE);
        if(bm!=null){
            long microAh=bm.getLongProperty(BatteryManager.BATTERY_PROPERTY_CHARGE_COUNTER);
            if(microAh!=Long.MIN_VALUE && microAh>0)s.append("; device_charge_uAh=").append(microAh);
            long current=bm.getLongProperty(BatteryManager.BATTERY_PROPERTY_CURRENT_NOW);
            if(current!=Long.MIN_VALUE && current!=0)s.append("; device_current_uA=").append(current);
        }
        s.append("; NOTE: phone-wide data, not app-only consumption");
        return s.toString();
    }
    public static void sample(Context c,boolean force){
        long now=SystemClock.elapsedRealtime();
        synchronized(LOCK){if(!force && now-lastSample<SAMPLE_MS)return;lastSample=now;}
        event(c,"BATTERY",battery(c));
    }
    public static String report(Context c){
        StringBuilder b=new StringBuilder();
        b.append("Pokewalker diagnostic report\nGenerated: ").append(stamp()).append("\n");
        b.append("Device: ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL);
        b.append("; Android SDK ").append(Build.VERSION.SDK_INT).append("\n");
        b.append("App version: 1.7.2-v5-diagnostics\n");
        b.append("Battery snapshot: ").append(battery(c)).append("\n");
        b.append("IMPORTANT: battery snapshots are PHONE-WIDE and cannot quantify app-specific energy.\n");
        b.append("Logs are stored only on your device until you explicitly export/share them.\n\n");
        appendFile(b,"Older log",previous(c));appendFile(b,"Current log",current(c));
        return b.toString();
    }
    private static void appendFile(StringBuilder b,String title,File file){
        b.append("\n=== ").append(title).append(" ===\n");
        if(!file.exists()){b.append("(empty)\n");return;}
        synchronized(LOCK){
            try(BufferedReader r=new BufferedReader(new InputStreamReader(new FileInputStream(file),"UTF-8"))){
                String line;while((line=r.readLine())!=null)b.append(line).append('\n');
            }catch(IOException e){b.append("[read failure]\n");}
        }
    }
    public static void clear(Context c){synchronized(LOCK){current(c).delete();previous(c).delete();}}
}
