package io.github.sdtransporter.pokewalker;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.graphics.Color;
import android.widget.*;
import android.view.View;
import java.net.*;
import java.util.*;

/** Manual hotspot configuration; Android does not expose portable third-party control of open tethering. */
public final class DSiV5Activity extends Activity {
    private DSiV5Server server;
    private final Handler ui=new Handler(Looper.getMainLooper());
    private TextView log;
    private Button start,stop;
    private int dp(int a){return (int)(a*getResources().getDisplayMetrics().density+.5f);}
    private void note(String value){Diagnostics.event(this,"DSI_V5",value);ui.post(()->{if(log!=null && !isDestroyed())log.append("\n"+value);});}
    @Override public void onCreate(Bundle saved){super.onCreate(saved);
        ScrollView sc=new ScrollView(this);sc.setBackgroundColor(0xff0b1a28);
        LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(dp(20),dp(16),dp(20),dp(16));sc.addView(layout);setContentView(sc);
        addText(layout,"POKEWALKER V5 | HOTSPOT",22,0xff44ddb3);
        addText(layout,"DSi envia ao Android. Sem roteador ou internet. Os dados sao sinteticos; nenhuma alteracao em Pokemon/saves.",15,Color.WHITE);
        addButton(layout,"1. Abrir configuracoes de hotspot",()->startActivity(new Intent(android.provider.Settings.ACTION_WIRELESS_SETTINGS)));
        addText(layout,"Ative manualmente um hotspot 2.4 GHz COMPATIVEL com Nintendo DSi (aberto, se suportado pelo aparelho). Depois conecte o DSi a ele. Desative o hotspot ao terminar.",14,0xffbdcfca);
        start=addButton(layout,"2. Iniciar receptor (porta 30822)",this::startReceiver);
        stop=addButton(layout,"Parar receptor",this::stopReceiver);
        addText(layout,"No homebrew DSi V5, pressione B para PING, A para 2048 bytes, X para 8192 bytes. O DSi usara automaticamente o gateway Wi-Fi como IP do Android.",14,0xffbdcfca);
        log=addText(layout,"Aguardando. Mantenha esta tela aberta durante o teste.",14,Color.WHITE);
        stop.setEnabled(false);
    }
    private TextView addText(LinearLayout l,String text,int size,int color){TextView v=new TextView(this);v.setText(text);v.setTextColor(color);v.setTextSize(size);v.setPadding(0,dp(12),0,dp(12));l.addView(v);return v;}
    private Button addButton(LinearLayout l,String text,Runnable callback){Button b=new Button(this);b.setText(text);b.setAllCaps(false);l.addView(b,new LinearLayout.LayoutParams(-1,dp(56)));b.setOnClickListener(v->callback.run());return b;}
    private void startReceiver(){
        if(server!=null)return;
        try {DSiV5Server s=new DSiV5Server(this::note);s.start();server=s;start.setEnabled(false);stop.setEnabled(true);}
        catch(Exception e){Diagnostics.error(this,"DSI_V5_START",e);note("Falha ao iniciar: "+e.getMessage());}
    }
    private void stopReceiver(){if(server!=null){server.close();server=null;note("Receptor parado");}start.setEnabled(true);stop.setEnabled(false);}
    @Override protected void onDestroy(){stopReceiver();super.onDestroy();}
}
