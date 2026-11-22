package io.github.sdtransporter.pokewalker;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.Context;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Test-only screen for the independent Nintendo DSi V3 homebrew server. */
public final class DSiV4Activity extends Activity {
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final Handler ui=new Handler(Looper.getMainLooper());
    private EditText ip;
    private TextView status, log;
    private ProgressBar progress;
    private Button ping,send2k,send8k,corrupt;
    private boolean busy=false;
    private int dp(float n){return (int)(n*getResources().getDisplayMetrics().density+.5f);}
    private TextView label(String text,int size,int color){TextView t=new TextView(this);t.setText(text);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(8),0,dp(8));return t;}
    private Button button(LinearLayout root,String text,Runnable onClick){Button b=new Button(this);b.setText(text);b.setAllCaps(false);root.addView(b,new LinearLayout.LayoutParams(-1,dp(54)));b.setOnClickListener(v->onClick.run());return b;}
    private void append(String message){ui.post(()->{if(isFinishing()||isDestroyed())return;log.append("\n"+message);});}
    private void lock(boolean state){ui.post(()->{busy=state;for(Button b:new Button[]{ping,send2k,send8k,corrupt})b.setEnabled(!state);});}
    private String validIP(){String v=ip.getText().toString().trim();
        // Validate numeric IPv4 only: no hostname, DNS lookup or external connections.
        if(!v.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}"))return null;
        String[] fields=v.split("\\.");for(String f:fields)if(Integer.parseInt(f)>255)return null;
        return v;
    }
    private interface Work {String run(DSiV4Transport connection) throws Exception;}
    private void execute(String title,Work task){
        if(busy)return;String host=validIP();if(host==null){status.setText("Informe um endereco IPv4 valido do DSi.");return;}
        lock(true);status.setText(title+"...");log.setText("DSi: "+host+":30821\n"+title);progress.setProgress(0);
        worker.execute(()->{
            try{String outcome=task.run(new DSiV4Transport(host));Diagnostics.event(this,"DSI_V4","Success: "+title+" "+outcome);ui.post(()->{if(isDestroyed())return;status.setText("SUCESSO");log.append("\n"+outcome);});}
            catch(Exception e){Diagnostics.error(this,"DSI_V4 "+title,e);ui.post(()->{if(isDestroyed())return;status.setText("FALHA");log.append("\nErro: "+e.getClass().getSimpleName()+": "+e.getMessage());});}
            finally {lock(false);}
        });
    }
    @Override public void onCreate(Bundle b){super.onCreate(b);
        getWindow().setStatusBarColor(0xff0b1a28);getWindow().setNavigationBarColor(0xff0b1a28);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(0xff0b1a28);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(20),dp(20),dp(20),dp(20));scroll.addView(root);setContentView(scroll);
        root.addView(label("POKEWALKER DSi | V4",24,0xff44ddb3));
        root.addView(label("Teste de rede com DSi V3. Dados ficticios na RAM, sem alterar Pokemon ou saves.",15,0xffe9f6f0));
        root.addView(label("IP mostrado no Nintendo DSi",15,0xff9ebeb7));
        ip=new EditText(this);ip.setSingleLine(true);ip.setInputType(android.text.InputType.TYPE_CLASS_PHONE);ip.setText(getPreferences(Context.MODE_PRIVATE).getString("dsi_ip","192.168.0.7"));ip.setTextColor(Color.WHITE);ip.setHint("192.168.0.7");root.addView(ip);
        status=label("Pronto para testar",17,0xff44ddb3);root.addView(status);
        progress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(8192);root.addView(progress);
        ping=button(root,"1. Testar PING binario",()->execute("PING",DSiV4Transport::ping));
        send2k=button(root,"2. Enviar 2.048 bytes",()->startTransfer(2048,256));
        send8k=button(root,"3. Enviar 8.192 bytes",()->startTransfer(8192,512));
        corrupt=button(root,"4. Testar CRC corrompido",()->execute("CRC incorreto",conn->{if(!conn.testCorrupt())throw new Exception("Quadro corrompido foi aceito");return "Quadro rejeitado pelo DSi";}));
        log=label("Aguardando",15,0xffe9f6f0);root.addView(log);
        root.addView(label("A rede deve permitir conexoes entre Android e DSi. O programa .nds V3 precisa estar aberto no console.",13,0xff9ebeb7));
        ip.setOnFocusChangeListener((v,has)->{if(!has)getPreferences(Context.MODE_PRIVATE).edit().putString("dsi_ip",ip.getText().toString().trim()).apply();});
    }
    private void startTransfer(int total,int chunk){execute("Transferencia "+total+" bytes",conn->conn.transfer(total,chunk,(message,done,all)->ui.post(()->{if(!isDestroyed()){progress.setMax(all);progress.setProgress(done);log.append("\n"+message);}})));}
    @Override protected void onDestroy(){worker.shutdownNow();super.onDestroy();}
}
