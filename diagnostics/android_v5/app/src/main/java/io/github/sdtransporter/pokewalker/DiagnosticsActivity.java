package io.github.sdtransporter.pokewalker;

import android.app.*;
import android.content.*;
import android.os.*;
import android.graphics.Color;
import android.view.*;
import android.widget.*;
import java.io.*;

/** User-controlled diagnostics view/export, no Internet or background sampler. */
public final class DiagnosticsActivity extends Activity {
    private static final int EXPORT=191;
    private TextView display;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final Runnable refresh=new Runnable(){public void run(){Diagnostics.sample(DiagnosticsActivity.this,false);if(display!=null)display.setText(Diagnostics.report(DiagnosticsActivity.this));handler.postDelayed(this,30000);}};
    private String pending;
    private int dp(int a){return (int)(getResources().getDisplayMetrics().density*a+.5f);}
    private Button button(LinearLayout p,String name,Runnable action){Button b=new Button(this);b.setText(name);b.setAllCaps(false);p.addView(b);b.setOnClickListener(v->action.run());return b;}
    @Override public void onCreate(Bundle saved){super.onCreate(saved);
        ScrollView scroll=new ScrollView(this);scroll.setBackgroundColor(0xff0b1a28);
        LinearLayout root=new LinearLayout(this);root.setPadding(dp(16),dp(20),dp(16),dp(20));root.setOrientation(LinearLayout.VERTICAL);scroll.addView(root);setContentView(scroll);
        TextView heading=new TextView(this);heading.setText("POKEWALKER | DIAGNOSTICS");heading.setTextSize(22);heading.setTextColor(0xff44ddb3);root.addView(heading);
        TextView disclaimer=new TextView(this);disclaimer.setText("Battery measurements reflect the WHOLE PHONE, not the energy consumed by this app. Crash and network event logs stay private unless you export them. Review before sharing.");disclaimer.setTextColor(Color.WHITE);disclaimer.setPadding(0,dp(12),0,dp(12));root.addView(disclaimer);
        button(root,"Record battery snapshot now",()->{Diagnostics.sample(this,true);display.setText(Diagnostics.report(this));});
        button(root,"Export log to a text file",()->{pending=Diagnostics.report(this);Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("text/plain");i.putExtra(Intent.EXTRA_TITLE,"pokewalker-diagnostic.txt");startActivityForResult(i,EXPORT);});
        button(root,"Clear stored logs",()->new AlertDialog.Builder(this).setTitle("Clear diagnostics?").setMessage("This deletes local crash, error and battery history only. Pokewalker saves are untouched.").setPositiveButton("Clear",(d,w)->{Diagnostics.clear(this);Diagnostics.event(this,"INFO","Diagnostic log cleared");display.setText(Diagnostics.report(this));}).setNegativeButton("Cancel",null).show());
        display=new TextView(this);display.setTextIsSelectable(true);display.setTextSize(12);display.setTextColor(Color.WHITE);display.setPadding(0,dp(15),0,0);root.addView(display);
    }
    @Override protected void onResume(){super.onResume();handler.removeCallbacks(refresh);handler.post(refresh);}
    @Override protected void onPause(){handler.removeCallbacks(refresh);super.onPause();}
    @Override protected void onActivityResult(int req,int result,Intent data){super.onActivityResult(req,result,data);
        if(req!=EXPORT||result!=RESULT_OK||data==null||data.getData()==null)return;
        try(OutputStream stream=getContentResolver().openOutputStream(data.getData())){
            if(stream==null)throw new IOException("Document cannot be opened");
            stream.write((pending==null?Diagnostics.report(this):pending).getBytes("UTF-8"));
            Toast.makeText(this,"Diagnostic exported",Toast.LENGTH_LONG).show();
        }catch(Exception e){Diagnostics.error(this,"EXPORT",e);Toast.makeText(this,"Export failed: "+e.getMessage(),Toast.LENGTH_LONG).show();}
        finally{pending=null;}
    }
}
