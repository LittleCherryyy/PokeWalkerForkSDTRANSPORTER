package io.github.sdtransporter.pokewalker;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.*;
import android.graphics.drawable.GradientDrawable;
import android.hardware.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
public final class MainActivity extends Activity {
    private static final int INK=0xffe9f6f0,MUTED=0xff9ebeb7,MINT=0xff44ddb3,GOLD=0xfffcca66,PANEL=0xff17303b;
    private WalkerStore state;
    private LinearLayout contentRoot,homeMetrics;
    private LinearLayout panel;
    private TextView stats, appTitle;
    private TextView homeProfileChip,stepMetric,wattsMetric,partnerMetric,partnerDetail;
    private WalkerPicture picture;
    private String page="home";
    private TextView syncReceiverStatus, syncConnectionStatus, syncNetworkEvents, syncPhoneWalkerStatus, syncLastEvent;
    private TextView syncStatusBadge,syncStatusTitle,syncStatusDetail,syncStepTcp,syncStepFrame,syncStepSaved;
    private PhonePeerSession peerSession;
    private Runnable pendingPeerPermission;
    private int[] classic=new int[40];
    private byte[] classicPixels;
    private int[] visitReward;
    private long visitStarted;
    private long classicLastInputAt;
    private String classicProfile="";
    private int pressedImageButton=-1;
    private boolean imageHeld;
    private final Runnable imageHold=()->{if(page.equals("classic")&&pressedImageButton==1){imageHeld=true;classicPress(3);}};
    private android.media.AudioTrack classicAudio;
    private final Runnable classicClock=new Runnable(){public void run(){if(page.equals("classic")){
        long now=SystemClock.elapsedRealtime();
        if(classic[0]!=0&&now-classicLastInputAt>=5000L){classicLastInputAt=now;classicPress(3);}
        else classicPress(-1);
        handler.postDelayed(this,100);
    }}};
    private boolean syncBusy;
    private File recoveryExport;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private int generation,encounter,round,rounds,target=-1,attempts,hidden,empty=-1,item;
    private int[] battle;
    private boolean battleAnimating;
    private int battleVisualAction=-1,previousPlayerHp=4,previousWildHp=4;
    private long battleAnimationStart;
    private long radarDeadline;
    private ProgressBar radarProgress;
    private final Runnable redraw=new Runnable(){public void run(){if(syncBusy&&!state.syncing){syncBusy=false;home();startTracking(false);}updateHeader();refreshSyncReceiverStatus();handler.postDelayed(this,500);}};
    @Override public void onCreate(Bundle bundle){
        super.onCreate(bundle);state=WalkerStore.get(this);
        getWindow().setStatusBarColor(0xff0b1a28);getWindow().setNavigationBarColor(0xff0b1a28);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(0xff0b1a28);
        contentRoot=new LinearLayout(this);contentRoot.setOrientation(LinearLayout.VERTICAL);contentRoot.setPadding(dp(16),dp(12),dp(16),dp(20));scroll.addView(contentRoot);
        appTitle=text("Pokéwalker",25,INK);appTitle.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);contentRoot.addView(appTitle);
        homeProfileChip=text("",14,INK);homeProfileChip.setGravity(Gravity.CENTER_VERTICAL);homeProfileChip.setPadding(dp(12),dp(3),dp(12),dp(3));homeProfileChip.setBackground(round(0xff122833,dp(15)));homeProfileChip.setMinHeight(dp(38));contentRoot.addView(homeProfileChip);
        picture=new WalkerPicture();contentRoot.addView(picture,new LinearLayout.LayoutParams(-1,dp(250)));
        stats=text("",12,MINT);stats.setGravity(Gravity.CENTER_VERTICAL);stats.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);stats.setPadding(dp(12),0,dp(12),0);stats.setBackground(round(0xff123a3a,dp(12)));stats.setMinHeight(dp(32));contentRoot.addView(stats);
        homeMetrics=new LinearLayout(this);homeMetrics.setOrientation(LinearLayout.HORIZONTAL);homeMetrics.setGravity(Gravity.CENTER_VERTICAL);homeMetrics.setPadding(dp(8),dp(8),dp(8),dp(8));homeMetrics.setBackground(round(PANEL,dp(14)));
        addMetric(homeMetrics,"PASSOS",0);addMetricDivider(homeMetrics);addMetric(homeMetrics,"WATTS",1);addMetricDivider(homeMetrics);addMetric(homeMetrics,"PERFIL",2);
        LinearLayout.LayoutParams metricsLp=new LinearLayout.LayoutParams(-1,-2);metricsLp.topMargin=dp(8);contentRoot.addView(homeMetrics,metricsLp);
        panel=new LinearLayout(this);panel.setOrientation(LinearLayout.VERTICAL);contentRoot.addView(panel);setContentView(scroll);
        // Keep controls clear of gesture navigation, system bars and cutouts.
        scroll.setOnApplyWindowInsetsListener((view,insets)->{
            if(Build.VERSION.SDK_INT>=30){
                android.graphics.Insets safe=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
                view.setPadding(safe.left,safe.top,safe.right,safe.bottom);
            }else view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        scroll.requestApplyInsets();
        picture.setOnTouchListener((view,event)->{
            if(event.getActionMasked()==MotionEvent.ACTION_DOWN){
                handler.removeCallbacks(imageHold);imageHeld=false;pressedImageButton=picture.imageButton(event.getX(),event.getY());
                if(page.equals("classic")&&pressedImageButton==1)handler.postDelayed(imageHold,menuHoldMillis());
                view.getParent().requestDisallowInterceptTouchEvent(pressedImageButton>=0);return true;
            }
            if(event.getActionMasked()==MotionEvent.ACTION_CANCEL){handler.removeCallbacks(imageHold);pressedImageButton=-1;return true;}
            if(event.getActionMasked()==MotionEvent.ACTION_MOVE){if(picture.imageButton(event.getX(),event.getY())!=pressedImageButton){handler.removeCallbacks(imageHold);pressedImageButton=-1;}return true;}
            if(event.getActionMasked()!=MotionEvent.ACTION_UP)return true;
            handler.removeCallbacks(imageHold);
            if(page.equals("peer")&&peerSession!=null){if(event.getY()>view.getHeight()*.65f){float x=event.getX()/view.getWidth();if(x<.4f)peerSession.select(-1);else if(x>.6f)peerSession.select(1);else peerSession.choose();}return true;}
            if(!page.equals("classic")){openClassic();return true;}
            int button=picture.imageButton(event.getX(),event.getY());if(!imageHeld&&button>=0&&button==pressedImageButton)classicPress(button);pressedImageButton=-1;
            return true;
        });
        picture.setContentDescription("Pokewalker. Tap to open original-style controls.");
        home();handler.post(redraw);
        startTracking(false);
        handler.post(()->{try{DirectSyncService.restoreAfterPackageUpdate(this);}catch(RuntimeException ex){toast("Não foi possível retomar o receptor: "+ex.getMessage());}});
        handler.post(()->handleWidgetIntent(getIntent()));
    }
    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);handler.post(()->handleWidgetIntent(intent));}
    private void handleWidgetIntent(Intent intent){
        if(intent==null)return;
        if(intent.getBooleanExtra("widget_open_error",false))widgetErrorScreen(intent.getStringExtra("widget_profile_id"));
        else if(intent.getBooleanExtra("widget_open_sync",false)){
            if(selectWidgetProfile(intent.getStringExtra("widget_profile_id"))){
                // A widget tap can resume a phone-side return after Android
                // reclaimed the process. Keep the Pokémon locked until the
                // SD Transporter confirms the same session, and re-arm only
                // the listener/direction here; this does not send any data.
                if(state.returnPending&&(!DirectSyncService.enabled(this)||
                   DirectSyncService.armedOperation(this)!=DirectSyncProtocol.OP_ARM_PULL))
                    startConsoleReceiver();
                syncScreen();handler.postDelayed(()->{if(page.equals("sync"))syncScreen();},400);
            }
        }else if(intent.getBooleanExtra("widget_open_connect",false)&&selectWidgetProfile(intent.getStringExtra("widget_profile_id")))connectMenu();
    }
    private boolean selectWidgetProfile(String profileId){
        if(profileId==null||profileId.isEmpty()||profileId.equals(state.profileId))return true;
        if(profilesBusy()){toast("Aguarde a transferência terminar antes de trocar de perfil.");return false;}
        try{if(state.error.isEmpty())state.save();state=WalkerStore.selectProfile(this,profileId);startTracking(false);return true;}
        catch(IOException ex){toast("Não foi possível abrir o perfil do widget: "+ex.getMessage());return false;}
    }
    @Override protected void onResume(){super.onResume();if(page.equals("classic")){handler.removeCallbacks(classicClock);handler.post(classicClock);}WalkerStore selected=WalkerStore.get(this);boolean changed=state!=selected;state=selected;syncBusy=peerSession==null&&state.syncing;if(changed)home();}
    @Override protected void onPause(){handler.removeCallbacks(imageHold);pressedImageButton=-1;handler.removeCallbacks(classicClock);stopClassicAudio();super.onPause();}
    @Override protected void onDestroy(){handler.removeCallbacks(redraw);handler.removeCallbacks(classicClock);stopClassicAudio();if(peerSession!=null)peerSession.close();pendingPeerPermission=null;generation++;super.onDestroy();}
    private int dp(float x){return (int)(x*getResources().getDisplayMetrics().density+.5f);}
    private TextView text(String s,int size,int color){TextView v=new TextView(this);v.setText(s);v.setTextSize(size);v.setTextColor(color);v.setPadding(0,dp(5),0,dp(5));return v;}
    private void heading(String title){appTitle.setText(title);appTitle.setVisibility(View.VISIBLE);homeProfileChip.setVisibility(View.GONE);homeMetrics.setVisibility(View.GONE);stats.setVisibility(View.VISIBLE);picture.setVisibility(View.VISIBLE);picture.getLayoutParams().height=dp(page.equals("radar")||page.equals("dowsing")?260:320);picture.requestLayout();panel.removeAllViews();}
    private void addMetric(LinearLayout parent,String title,int which){
        LinearLayout column=new LinearLayout(this);column.setOrientation(LinearLayout.VERTICAL);column.setGravity(Gravity.CENTER);column.setPadding(dp(4),dp(2),dp(4),dp(2));
        TextView heading=text(title,10,MUTED);heading.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);heading.setGravity(Gravity.CENTER);column.addView(heading);
        TextView value=text("—",20,INK);value.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);value.setGravity(Gravity.CENTER);column.addView(value);
        TextView detail=text("",11,MUTED);detail.setGravity(Gravity.CENTER);column.addView(detail);
        if(which==0){stepMetric=value;}else if(which==1){wattsMetric=value;}else{partnerMetric=value;partnerDetail=detail;}
        parent.addView(column,new LinearLayout.LayoutParams(0,-2,1));
    }
    private void addMetricDivider(LinearLayout parent){View divider=new View(this);divider.setBackgroundColor(0xff294852);LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(dp(1),dp(44));parent.addView(divider,lp);}
    private void note(String message){panel.addView(text(message,17,MUTED));}
    private void flowStep(String number,String title,String detail){flowStep(panel,number,title,detail);}
    private void flowStep(LinearLayout parent,String number,String title,String detail){
        LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.HORIZONTAL);card.setGravity(Gravity.CENTER_VERTICAL);card.setPadding(dp(12),dp(10),dp(12),dp(10));
        GradientDrawable background=new GradientDrawable();background.setColor(0xff122833);background.setCornerRadius(dp(12));background.setStroke(dp(1),0xff294852);card.setBackground(background);
        TextView badge=text(number,16,MINT);badge.setGravity(Gravity.CENTER);badge.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);badge.setBackground(round(0xff21483f,dp(9)));
        LinearLayout.LayoutParams badgeLp=new LinearLayout.LayoutParams(dp(38),dp(38));badgeLp.rightMargin=dp(12);card.addView(badge,badgeLp);
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);copy.addView(text(title,16,INK));copy.addView(text(detail,14,MUTED));card.addView(copy,new LinearLayout.LayoutParams(0,-2,1));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(7);parent.addView(card,lp);
    }
    private GradientDrawable round(int color,int radius){GradientDrawable shape=new GradientDrawable();shape.setColor(color);shape.setCornerRadius(radius);return shape;}
    private Button button(String label,Runnable action){
        Button b=new Button(this);b.setText(label);b.setTextSize(17);b.setTextColor(INK);b.setAllCaps(false);
        GradientDrawable background=new GradientDrawable();background.setColor(PANEL);background.setCornerRadius(dp(12));b.setBackground(background);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,dp(55));lp.topMargin=dp(8);panel.addView(b,lp);
        if(label.length()>2){b.setCompoundDrawablesWithIntrinsicBounds(new PixelMenuIcon(this,PixelMenuIcon.kind(label)),null,null,null);b.setCompoundDrawablePadding(dp(12));b.setPadding(dp(14),0,dp(14),0);b.setGravity(Gravity.CENTER_VERTICAL|Gravity.LEFT);}
        b.setOnClickListener(v->action.run());return b;
    }
    private Button patch(LinearLayout row,String label,Runnable action){
        Button b=button(label,action);panel.removeView(b);LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(60),1);lp.setMargins(dp(3),dp(4),dp(3),dp(4));row.addView(b,lp);return b;
    }
    private View grassPatch(LinearLayout row,int number,boolean rustling,boolean searched,Runnable action){
        GrassPatchView view=new GrassPatchView(this,number,rustling,searched);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(108),1);lp.setMargins(dp(3),dp(4),dp(3),dp(4));row.addView(view,lp);
        view.setOnClickListener(v->action.run());view.setEnabled(!searched);return view;
    }
    private LinearLayout patchRow(){LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);panel.addView(row);return row;}
    private void toast(String message){Toast.makeText(this,message,Toast.LENGTH_LONG).show();}
    private boolean owned(){if(!state.error.isEmpty()){home();toast("Retry saving before using activities.");return false;}if(syncBusy||state.syncing){toast("Please wait for sync to finish.");return false;}if(!state.active()){toast("Receive a Pokémon from your console first.");return false;}if(state.returnPending){toast("Finish returning your Pokémon before using activities.");return false;}return true;}
    private int random(int n){return Native.command(state.data,0,0)%n;}
    private void save(){state.changed();if(!state.error.isEmpty())toast(state.error);}
    private String packSummary(boolean item){
        StringBuilder names=new StringBuilder();
        for(int n=0;n<3;n++){int id=Native.command(state.data,item?7:6,n);if(id>0&&id<=(item?536:493)){if(names.length()>0)names.append(", ");names.append(item?Native.item(id):Native.species(id));}}
        return names.length()==0?"None":names.toString();
    }
    private void updateHeader(){
        synchronized(WalkerStore.LOCK){
            String profile=WalkerStore.profileName(this,state.profileId);
            homeProfileChip.setText("◉   "+profile.toUpperCase(java.util.Locale.ROOT)+"   ▾");
            String badge="CAMINHADA ATIVA";
            if(!state.error.isEmpty())badge="ATENÇÃO · SAVE PROTEGIDO";
            else if(state.returnPending)badge="RETORNO AGUARDANDO CONFIRMAÇÃO";
            else if(!state.active()){
                int armed=DirectSyncService.armedOperation(this);
                boolean selectedReceiver=DirectSyncService.enabled(this)&&
                        DirectSyncService.processRunning()&&
                        state.profileId.equals(DirectSyncService.targetProfileId(this))&&
                        armed==DirectSyncProtocol.OP_ARM_PUSH;
                String receiverStatus=DirectSyncService.status(this);
                if(!selectedReceiver)badge="SEM POKÉMON · CONNECT PARA RECEBER";
                else if(receiverStatus.startsWith("Listening for DSi")||
                        receiverStatus.startsWith("Waiting for DSi"))
                    badge="RECEPTOR ATIVO · AGUARDANDO HGSS";
                else if(receiverStatus.startsWith("Starting listener"))
                    badge="INICIANDO RECEPTOR · AGUARDE";
                else if(receiverStatus.startsWith("DSi TCP connected"))
                    badge="CONSOLE CONECTADO · AGUARDANDO DADOS";
                else if(receiverStatus.startsWith("DSi TCP closed before complete frame"))
                    badge="DSI DESCONECTOU · TENTE HGSS";
                else if(receiverStatus.startsWith("DSi TCP disconnected after protocol frame"))
                    badge="CONSOLE DESCONECTADO · RECEPTOR ATIVO";
                else if(receiverStatus.startsWith("DSi TCP timeout"))
                    badge="CONEXÃO EXPIRADA · TENTE HGSS";
                else if(receiverStatus.startsWith("Last DSi request failed"))
                    badge="PEDIDO RECUSADO · RECEPTOR ATIVO";
                else badge="RECEPTOR COM PROBLEMA · TOQUE CONNECT";
            }
            else if(state.revoked)badge="SESSÃO REVOGADA";
            else if(!state.trackingIssue.isEmpty())badge="RASTREAMENTO PAUSADO";
            else if(state.mode==2)badge="CAMINHADA ATIVA";
            else if(state.mode==1)badge="CONTADOR POR TEMPO";
            else if(state.mode==0)badge="CAMINHADA PAUSADA";
            if(!badge.contentEquals(stats.getText()))stats.setText(badge);
            if(state.data==null){stepMetric.setText("0");wattsMetric.setText("0");partnerMetric.setText("—");partnerDetail.setText("aguardando console");}
            else {
                long[] info=Native.info(state.data);
                stepMetric.setText(String.valueOf(info[Native.TODAY]));wattsMetric.setText(String.valueOf(info[Native.WATTS]));
                if(info[Native.HAS_POKEMON]!=0){partnerMetric.setText(Native.species((int)info[Native.SPECIES]));partnerDetail.setText("Lv "+info[Native.LEVEL]);}
                else{partnerMetric.setText("—");partnerDetail.setText("sem parceiro");}
            }
            picture.invalidate();
        }
    }
    private void stopClassicAudio(){if(classicAudio!=null){classicAudio.release();classicAudio=null;}}
    private void playClassicScore(int score,int volume){
        if(state.data==null)return;
        short[] pcm=Native.classicSound(state.data,score);stopClassicAudio();
        if(pcm!=null&&pcm.length>0)try{
            classicAudio=new android.media.AudioTrack.Builder().setAudioAttributes(new android.media.AudioAttributes.Builder().setUsage(android.media.AudioAttributes.USAGE_GAME).setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION).build()).setAudioFormat(new android.media.AudioFormat.Builder().setSampleRate(22050).setChannelMask(android.media.AudioFormat.CHANNEL_OUT_MONO).setEncoding(android.media.AudioFormat.ENCODING_PCM_16BIT).build()).setTransferMode(android.media.AudioTrack.MODE_STATIC).setBufferSizeInBytes(pcm.length*2).build();
            classicAudio.setVolume(new float[]{.16f,.33f,.55f}[Math.max(0,Math.min(2,volume))]);classicAudio.write(pcm,0,pcm.length);classicAudio.play();
        }catch(RuntimeException ex){stopClassicAudio();}
    }
    private void showVisit(int[] reward){
        if(reward==null||visitReward==reward)return;
        visitReward=reward;
        visitStarted=SystemClock.elapsedRealtime();
        picture.invalidate();
        handler.postDelayed(()->playVisitScore(reward,9),4000);
        handler.postDelayed(()->playVisitScore(reward,6),8000);
    }
    private void playVisitScore(int[] reward,int score){
        synchronized(WalkerStore.LOCK){
            if(!isDestroyed()&&visitReward==reward&&(page.equals("visit")||page.equals("peer")))
                playClassicScore(score,state.classicVolume);
        }
    }
    private void addHomeSyncCard(){
        LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(dp(14),dp(12),dp(14),dp(12));card.setBackground(round(PANEL,dp(16)));
        LinearLayout header=new LinearLayout(this);header.setOrientation(LinearLayout.HORIZONTAL);header.setGravity(Gravity.CENTER_VERTICAL);card.addView(header);
        TextView icon=text("↔",18,MINT);icon.setGravity(Gravity.CENTER);icon.setBackground(round(0xff21483f,dp(11)));header.addView(icon,new LinearLayout.LayoutParams(dp(40),dp(40)));
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);LinearLayout.LayoutParams copyLp=new LinearLayout.LayoutParams(0,-2,1);copyLp.leftMargin=dp(11);header.addView(copy,copyLp);
        copy.addView(text("Console Wi-Fi Sync",17,INK));copy.addView(text("Enviar e devolver pelo hotspot",13,MUTED));
        TextView action=text("Abrir sincronização",15,0xff06221d);action.setGravity(Gravity.CENTER);action.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);action.setBackground(round(MINT,dp(12)));action.setMinHeight(dp(48));
        LinearLayout.LayoutParams actionLp=new LinearLayout.LayoutParams(-1,dp(50));actionLp.topMargin=dp(12);card.addView(action,actionLp);action.setOnClickListener(v->openConsoleSync());
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(9);panel.addView(card,lp);
    }
    private void addHomeTile(LinearLayout row,String title,String subtitle,Runnable action){
        LinearLayout tile=new LinearLayout(this);tile.setOrientation(LinearLayout.VERTICAL);tile.setPadding(dp(12),dp(10),dp(12),dp(10));tile.setBackground(round(PANEL,dp(13)));tile.setMinimumHeight(dp(76));tile.setFocusable(true);tile.setClickable(true);
        TextView name=text(title,15,INK);name.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);tile.addView(name);tile.addView(text(subtitle,12,MUTED));tile.setOnClickListener(v->action.run());
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-2,1);lp.setMargins(dp(3),dp(8),dp(3),dp(4));row.addView(tile,lp);
    }
    private void openClassic(){
        synchronized(WalkerStore.LOCK){
            if(!state.error.isEmpty()||state.syncing||syncBusy){toast("Conclua a sincronização ou a recuperação antes de abrir os menus.");return;}
            classicProfile=state.profileId;classic=new int[40];classic[19]=state.classicVolume;classic[20]=state.classicContrast;classic[26]=WalkerClassicData.secondsOfDay();
            classicLastInputAt=SystemClock.elapsedRealtime();
            byte[] image=WalkerClassicData.image(state);
            if(state.returnPending)image=image.clone();
            classicPixels=Native.classicFrame(image,classic,SystemClock.elapsedRealtime());
        }
        generation++;page="classic";renderClassicControls();
        handler.removeCallbacks(classicClock);handler.post(classicClock);
    }
    private void renderClassicControls(){
        panel.removeAllViews();appTitle.setVisibility(View.GONE);stats.setVisibility(View.GONE);
        picture.getLayoutParams().height=dp(360);picture.requestLayout();
        LinearLayout controls=patchRow();patch(controls,"◀",()->classicPress(0));Button centre=patch(controls,"●",()->classicPress(1));patch(controls,"▶",()->classicPress(2));
        final boolean[] held={false};
        final Runnable back=()->{if(page.equals("classic")&&centre.isAttachedToWindow()){held[0]=true;classicPress(3);}};
        centre.setOnTouchListener((view,event)->{
            switch(event.getActionMasked()){
            case MotionEvent.ACTION_DOWN:held[0]=false;view.getParent().requestDisallowInterceptTouchEvent(true);handler.postDelayed(back,menuHoldMillis());return true;
            case MotionEvent.ACTION_MOVE:if(event.getX()<0||event.getY()<0||event.getX()>view.getWidth()||event.getY()>view.getHeight()){handler.removeCallbacks(back);held[0]=true;}return true;
            case MotionEvent.ACTION_UP:handler.removeCallbacks(back);if(!held[0])view.performClick();return true;
            case MotionEvent.ACTION_CANCEL:handler.removeCallbacks(back);return true;
            default:return true;
            }
        });
        button("Voltar ao app",this::home);
    }
    private void classicPress(int button){
        if(!page.equals("classic"))return;
        if(button>=0)classicLastInputAt=SystemClock.elapsedRealtime();
        synchronized(WalkerStore.LOCK){
            if(!state.profileId.equals(classicProfile)||state.syncing||!state.error.isEmpty()){handler.removeCallbacks(classicClock);stopClassicAudio();home();return;}
            boolean protectedReturn=state.returnPending;
            byte[] image=WalkerClassicData.image(state);
            if(protectedReturn)image=image.clone();
            byte[] before=image.clone();
            classic[26]=WalkerClassicData.secondsOfDay();
            Native.classicInput(image,classic,button,Native.now(),SystemClock.elapsedRealtime(),state.expandedItems);
            boolean controlsChanged=state.classicVolume!=classic[19]||state.classicContrast!=classic[20];
            state.classicVolume=classic[19];state.classicContrast=classic[20];
            boolean dataChanged=!protectedReturn&&state.data!=null&&!java.util.Arrays.equals(before,state.data);
            if(controlsChanged||dataChanged){
                try{
                    boolean reward=false;if(dataChanged)for(int n=0xce8c;n<0xcef0;n++)if(before[n]!=state.data[n]){reward=true;break;}
                    if(reward)state.archiveCurrent("reward");state.save();
                }catch(IOException ex){state.error="Save failed. Keep the app open and retry. "+ex.getMessage();state.mode=0;handler.removeCallbacks(classicClock);home();return;}
            }
            if(classic[10]>0&&state.data!=null&&!protectedReturn){
                int score=classic[10]-1;classic[10]=0;
                playClassicScore(score,classic[19]);
            }
            if(classic[10]>0)classic[10]=0;
            classic[26]=WalkerClassicData.secondsOfDay();
            classicPixels=Native.classicFrame(image,classic,SystemClock.elapsedRealtime());picture.invalidate();
            if(classic[0]==10){handler.removeCallbacks(classicClock);connectMenu();}
            else if(classic[0]==8&&classic[2]==1){handler.removeCallbacks(classicClock);openConsoleSync();}
        }
    }
    private void home(){
        if(page.equals("sync")&&DirectSyncService.enabled(this)&&
           state.profileId.equals(DirectSyncService.targetProfileId(this))){
            DirectSyncService.stop(this);
            WidgetConfigActivity.clearStatusForProfile(this,state.profileId);
        }
        handler.removeCallbacks(classicClock);stopClassicAudio();
        visitReward=null;
        if(peerSession!=null){peerSession.close();peerSession=null;}
        generation++;battleAnimating=false;page="home";appTitle.setText("Pokéwalker");appTitle.setVisibility(View.VISIBLE);
        homeProfileChip.setVisibility(View.VISIBLE);homeProfileChip.setOnClickListener(v->profilesScreen());
        picture.setVisibility(View.VISIBLE);picture.getLayoutParams().height=dp(250);picture.requestLayout();
        stats.setVisibility(View.VISIBLE);homeMetrics.setVisibility(View.VISIBLE);panel.removeAllViews();
        synchronized(WalkerStore.LOCK){
            if(!state.error.isEmpty()){
                note("Este perfil está protegido. O save original foi preservado.");note(state.error);
                if(state.visitBlocked)button("Recuperar perfil",()->{synchronized(WalkerStore.LOCK){state=WalkerStore.recoverVisits(this);home();}});
                else if(state.data!=null)button("Tentar salvar novamente",()->{synchronized(WalkerStore.LOCK){save();home();}});
                button("Escolher outro perfil",this::profilesScreen);
            }
            if(state.returnPending)note("Retorno pendente. A cópia do celular fica bloqueada até o console confirmar.");
            if(state.revoked)note("Esta sessão foi revogada. Use o menu de recuperação para concluir o retorno.");
            if(state.active()&&!state.trackingIssue.isEmpty())note("O rastreamento de passos está pausado; os menus do Pokéwalker e a sincronização continuam disponíveis.");
            if(state.active()&&!state.returnPending){
                if(state.battleRewardChoice>=0)button("Resgatar prêmio da batalha",this::claimBattleReward);
            }
        }
        button("Abrir menus do Pokéwalker",this::openClassic);
        button("Connect · Nearby phone",this::connectMenu);
        button("Configurações",this::settings);updateHeader();
    }
    private boolean profilesBusy(){if(syncBusy)return true;for(WalkerStore s:WalkerStore.all(this))if(s.syncing)return true;return false;}
    private void connectMenu(){
        if(!owned())return;handler.removeCallbacks(classicClock);stopClassicAudio();generation++;page="connect";heading("Connect");
        button("Another profile on this phone",this::visitProfiles);button("Nearby phone · Bluetooth",this::nearbyPurpose);button("Back",this::home);
    }
    private void nearbyPurpose(){
        if(!owned())return;generation++;page="nearby";heading("Nearby phone");
        note("Keep both phones open in Pokewalker. Choose the same activity on each phone.");
        button("Visit another Pokewalker",()->nearbyRoles(false));button("Friendly battle · 30 watts",()->nearbyRoles(true));button("Back",this::connectMenu);
    }
    private void nearbyRoles(boolean battle){
        if(!owned())return;generation++;page="nearby";heading(battle?"Friendly battle":"Visit a Pokewalker");
        note(battle?"Each player pays 30 watts once both accept. Winner receives a rare item reward. Expanded items must be enabled on both phones; otherwise rewards use course items. Battles use retained moves, power, accuracy and PP; status moves brace against the next attack. Type matchups and other special effects are not simulated.":"Both Pokémon remain in their own profiles. Each Pokewalker receives its normal daily visit gift.");
        button("Host a connection",()->peerPermission(()->beginPeer(battle,true)));button("Search nearby phones",()->peerPermission(()->beginPeer(battle,false)));button("Back",this::nearbyPurpose);
    }
    private void peerPermission(Runnable action){
        String[] wanted=Build.VERSION.SDK_INT>=31?new String[]{Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT,Manifest.permission.BLUETOOTH_ADVERTISE}:new String[]{Manifest.permission.ACCESS_FINE_LOCATION};
        java.util.ArrayList<String> missing=new java.util.ArrayList<>();for(String name:wanted)if(checkSelfPermission(name)!=PackageManager.PERMISSION_GRANTED)missing.add(name);
        if(!missing.isEmpty()){pendingPeerPermission=action;requestPermissions(missing.toArray(new String[0]),30);return;}action.run();
    }
    private void beginPeer(boolean battle,boolean host){
        if(!owned())return;generation++;classicPixels=null;page="peer";heading(battle?"Friendly battle":"Nearby visit");
        try{
            peerSession=new PhonePeerSession(this,state,battle,new PhonePeerSession.Listener(){
                public void changed(){if(!isDestroyed()&&page.equals("peer"))peerScreen();}
                public void device(String id,String name){if(isDestroyed()||!page.equals("peer")||peerSession==null)return;button(name,()->{if(peerSession!=null)peerSession.connect(id);});}
                public void closed(){startTracking(false);}
            });
            peerScreen();if(host)peerSession.host();else peerSession.search();
        }catch(IOException|SecurityException ex){if(peerSession!=null){peerSession.close();peerSession=null;}result("Bluetooth unavailable",ex.getMessage());}
    }
    private void peerScreen(){
        if(peerSession==null||!page.equals("peer"))return;
        heading(peerSession.battle?"Friendly battle":"Nearby visit");if(!peerSession.remoteName.isEmpty())note(peerSession.remoteName);note(peerSession.message);
        showVisit(peerSession.visitReward);
        byte[] frame=peerSession.frame();if(frame!=null){classicPixels=frame;picture.invalidate();}
        if(peerSession.canAccept())button(peerSession.battle?"Accept · 30 watts":"Start visit",()->{
            if(peerSession==null)return;
            if(peerSession.rewardsDiffer())new AlertDialog.Builder(this).setTitle("Reward settings differ")
                .setMessage("One phone has Expanded Dowsing items disabled. This battle will use only original course items, with rarer finds weighted more heavily. Each player still pays 30 watts.")
                .setPositiveButton("Continue · 30 watts",(d,w)->{if(peerSession!=null&&peerSession.canAccept())peerSession.accept();})
                .setNegativeButton("Cancel",null).show();
            else peerSession.accept();
        });
        if(peerSession.canMove()){
            LinearLayout row=patchRow();patch(row,"◀",()->peerSession.select(-1));patch(row,"●",()->peerSession.choose());patch(row,"▶",()->peerSession.select(1));
        }
        button("Disconnect",this::home);
    }
    private void claimBattleReward(){
        if(!owned()||state.battleRewardChoice<0)return;generation++;page="claimReward";heading("Battle reward");note(Native.item(Native.command(state.data,8,state.battleRewardChoice)));
        for(int n=0;n<3;n++){final int slot=n;button("Replace slot "+(n+1)+" · "+Native.item(Native.command(state.data,7,n)),()->new AlertDialog.Builder(this).setTitle("Replace this item?").setMessage("The battle reward will replace the item in this slot.").setPositiveButton("Replace",(d,w)->finishBattleReward(slot)).setNegativeButton("Cancel",null).show());}
        button("Leave reward",()->new AlertDialog.Builder(this).setTitle("Leave this reward?").setMessage("Your current pack is kept. This battle reward cannot be claimed again.").setPositiveButton("Leave",(d,w)->finishBattleReward(-1)).setNegativeButton("Cancel",null).show());button("Back",this::home);
    }
    private void finishBattleReward(int slot){
        synchronized(WalkerStore.LOCK){if(!owned()||state.battleRewardChoice<0)return;try{
            int choice=state.battleRewardChoice;if(slot>=0&&Native.command(state.data,10,((slot+1)<<16)|choice)!=1)throw new IOException("Reward could not be stored");
            state.battleRewardChoice=-1;state.archiveCurrent("battle-reward");state.save();home();
        }catch(IOException ex){state.error=ex.getMessage();home();}}
    }
    private void visitProfiles(){
        if(!owned())return;handler.removeCallbacks(classicClock);stopClassicAudio();
        generation++;page="connectProfiles";heading("Connect another Pokewalker");
        note("The Pokémon play together and each Pokewalker receives a gift. The same two devices can meet once per day. Their partners stay in their own profiles.");
        for(WalkerProfiles.Entry entry:WalkerStore.profileEntries(this))if(!entry.id.equals(state.profileId)){
            final String id=entry.id;
            button(entry.name,()->new AlertDialog.Builder(this).setTitle("Connect with "+entry.name+"?").setMessage("Both profiles are saved together before gifts are confirmed.").setPositiveButton("Connect",(d,w)->{
                synchronized(WalkerStore.LOCK){
                    try{
                        int[] reward=WalkerStore.visit(this,id);
                        generation++;page="visit";heading("A friendly meeting");
                        showVisit(reward);
                        note("Both gifts were saved. Meet again tomorrow.");
                        button("Continue",this::home);
                    }catch(IOException ex){toast(ex.getMessage());home();}
                }
            }).setNegativeButton("Cancel",null).show());
        }
        button("Back",this::home);
    }
    private void profilesScreen(){
        if(profilesBusy()){toast("Wait for the transfer to finish.");return;}
        generation++;page="profiles";heading("Walker profiles");note("All active profiles earn steps. Each profile keeps its own Pokémon, trainer pairing and backups.");
        synchronized(WalkerStore.LOCK){
            for(WalkerProfiles.Entry e:WalkerStore.profileEntries(this)){
                WalkerStore candidate=null;for(WalkerStore item:WalkerStore.all(this))if(item.profileId.equals(e.id))candidate=item;
                final String id=e.id;
                button((id.equals(state.profileId)?"Selected · ":"")+e.name,()->{
                    synchronized(WalkerStore.LOCK){if(profilesBusy()){toast("Wait for sync to finish.");return;}try{if(state.error.isEmpty())state.save();state=WalkerStore.selectProfile(this,id);home();startTracking(false);}catch(IOException ex){toast(ex.getMessage());}}
                });
                if(candidate!=null&&!candidate.error.isEmpty())note(candidate.error);
                if(candidate!=null)note(candidate.data==null?"No active Pokémon":Native.text(candidate.data,3)+(candidate.returnPending?" · Return pending":candidate.revoked?" · Revoked":" · On phone"));
            }
        }
        button("Add walker profile",()->profileNamePrompt(true));button("Rename selected profile",()->profileNamePrompt(false));button("Back",this::home);
    }
    private void profileNamePrompt(boolean create){
        if(profilesBusy()){toast("Wait for the transfer to finish.");return;}
        EditText name=new EditText(this);name.setSingleLine(true);name.setHint("For example: HeartGold");if(!create)name.setText(WalkerStore.profileName(this));
        new AlertDialog.Builder(this).setTitle(create?"Add walker profile":"Rename profile").setView(name).setPositiveButton("Save",(dialog,which)->{
            synchronized(WalkerStore.LOCK){if(profilesBusy()){toast("Wait for sync to finish.");return;}try{if(state.error.isEmpty())state.save();if(create)state=WalkerStore.createProfile(this,name.getText().toString());else WalkerStore.renameProfile(this,name.getText().toString());profilesScreen();startTracking(false);}catch(IOException ex){toast(ex.getMessage());}}
        }).setNegativeButton("Cancel",null).show();
    }
    private void result(String title,String detail){generation++;page="result";heading(title);note(detail);button("Continue",this::home);}
    private int menuHoldMillis(){
        int value=getSharedPreferences("controls",MODE_PRIVATE).getInt("menu_hold_ms",1000);
        return value==250||value==500||value==1000||value==1500||value==2000||value==3000?value:1000;
    }
    private String menuHoldLabel(int milliseconds){return milliseconds==250?"0.25 seconds":milliseconds==500?"0.5 seconds":milliseconds==1000?"1 second":milliseconds==1500?"1.5 seconds":(milliseconds/1000)+" seconds";}
    private void settings(){
        generation++;page="settings";heading("Settings");
        button("Back",this::home);
        button("Menu button hold: "+menuHoldLabel(menuHoldMillis()),()->{
            final int[] durations={250,500,1000,1500,2000,3000};String[] labels=new String[durations.length];int checked=0;
            for(int n=0;n<durations.length;n++){labels[n]=menuHoldLabel(durations[n]);if(durations[n]==menuHoldMillis())checked=n;}
            new AlertDialog.Builder(this).setTitle("Menu button hold").setSingleChoiceItems(labels,checked,(dialog,n)->{
                getSharedPreferences("controls",MODE_PRIVATE).edit().putInt("menu_hold_ms",durations[n]).apply();dialog.dismiss();settings();
            }).setNegativeButton("Cancel",null).show();
        });
        note("Hold the centre button for this long to return to the main LCD while browsing. Applies to every profile.");
        button("Pokéwalker skin: "+SkinManager.name(SkinManager.profileSkin(this,state.profileId)),()->{
            String current=SkinManager.profileSkin(this,state.profileId);
            new AlertDialog.Builder(this).setTitle("Pokéwalker skin")
                .setSingleChoiceItems(SkinManager.NAMES,SkinManager.indexOf(current),(dialog,n)->{
                    SkinManager.setProfileSkin(this,state.profileId,SkinManager.IDS[n]);
                    picture.invalidate();dialog.dismiss();settings();
                }).setNegativeButton("Cancel",null).show();
        });
        button("Expanded Dowsing rewards: "+(state.expandedItems?"On":"Off"),()->{
            if(state.syncing||state.returnPending){toast("Finish syncing first.");return;}
            if(state.expandedItems){synchronized(WalkerStore.LOCK){state.expandedItems=false;save();}settings();return;}
            new AlertDialog.Builder(this).setTitle("Enable expanded rewards?").setMessage("Adds Master Ball, PP items, TMs, vitamins, Rare Candy, EV-training items, evolution items, held items and Heart Scales. 92% of Dowsing finds still use the course. Off by default. Battle rewards expand only when both phones enable this option.")
                .setPositiveButton("Opt in",(dialog,which)->{synchronized(WalkerStore.LOCK){if(state.syncing||state.returnPending)return;state.expandedItems=true;save();}settings();}).setNegativeButton("Cancel",null).show();
        });
        boolean sensor=((SensorManager)getSystemService(SENSOR_SERVICE)).getDefaultSensor(Sensor.TYPE_STEP_COUNTER)!=null;
        note("One step source is active at a time. Physical steps are the default; no automatic timer fallback is used.");
        button("Phone pedometer: "+(state.mode==2?"On":"Off")+(sensor?"":" (unavailable)"),()->{
            if(!sensor){toast("This phone has no step counter sensor.");return;}
            chooseMode(state.mode==2?0:2);settings();
        });
        button("Time-based counter: "+(state.mode==1?"On":"Off"),()->{chooseMode(state.mode==1?0:1);settings();});
        button("Time-based rate: one step / "+state.rate+" seconds",()->{
            final int[] rates={1,2,5,10,30,60,300,3600,86400};String[] labels=new String[rates.length];int checked=0;
            for(int n=0;n<rates.length;n++){labels[n]=rates[n]+" seconds";if(rates[n]==state.rate)checked=n;}
            new AlertDialog.Builder(this).setTitle("Time per step").setSingleChoiceItems(labels,checked,(dialog,n)->{
                synchronized(WalkerStore.LOCK){if(state.returnPending||state.syncing){toast("Finish the pending sync before changing the rate.");return;}if(state.active()&&state.mode==1)Native.timer(state.data,Native.now(),state.rate);state.rate=rates[n];if(state.active())Native.resume(state.data,Native.now(),state.rate);save();}
                dialog.dismiss();settings();
            }).setNegativeButton("Cancel",null).show();
        });
        note("Tracking continues with an ongoing notification while the screen is off. Pause tracking here to stop it.");button("Diagnostics · battery, crashes and errors",()->startActivity(new Intent(this,DiagnosticsActivity.class)));button("Recovery copies",this::recoveryCopies);if(state.data!=null)button("Delete active walker",this::deleteActive);button("Privacy policy",()->startActivity(new Intent(this,PrivacyActivity.class)));button("About and licences",()->startActivity(new Intent(this,PrivacyActivity.class).putExtra("credits",true)));
    }
    private void recoveryCopies(){
        if(syncBusy){toast("Please wait for sync to finish.");return;}
        page="recovery";generation++;heading("Recovery copies");
        note("These snapshots preserve earlier walkers. Exporting a copy does not reactivate a revoked session or replace your active walker.");
        File[] files=state.recoveryDirectory().listFiles((dir,name)->name.endsWith(".walker"));
        if(files==null||files.length==0)note("No recovery copies yet.");
        else {
            java.util.Arrays.sort(files,(a,b)->Long.compare(b.lastModified(),a.lastModified()));
            for(File file:files){
                String label=java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.SHORT,java.text.DateFormat.SHORT).format(new java.util.Date(file.lastModified()));
                try{byte[] copy=java.nio.file.Files.readAllBytes(file.toPath());if(copy.length==65536&&Native.walkable(copy))note(Native.text(copy,3));}catch(IOException ignored){}
                button("Export copy · "+label,()->{
                    recoveryExport=file;Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);intent.setType("application/octet-stream");intent.addCategory(Intent.CATEGORY_OPENABLE);intent.putExtra(Intent.EXTRA_TITLE,"Pokewalker-recovery.walker");startActivityForResult(intent,70);
                });
                button("Delete copy · "+label,()->new AlertDialog.Builder(this).setTitle("Delete recovery copy?").setMessage("Permanently delete this snapshot? Your active walker and session records are kept.")
                    .setPositiveButton("Delete",(dialog,which)->{synchronized(WalkerStore.LOCK){if(state.syncing){toast("Wait for sync to finish.");return;}try{state.deleteRecovery(file);toast("Recovery copy deleted.");}catch(IOException ex){toast(ex.getMessage());}}recoveryCopies();}).setNegativeButton("Cancel",null).show());
            }
        }
        button("Back",this::settings);
    }
    private void deleteActive(){
        if(syncBusy||state.syncing){toast("Wait for sync to finish.");return;}
        new AlertDialog.Builder(this).setTitle("Delete active walker?")
            .setMessage("Remove this phone's active walker? A recovery copy is kept first. This phone session will stay inactive. If the console is still locked, use Recover on the console; deleting locally does not notify it.")
            .setPositiveButton("Delete",(dialog,which)->{
                synchronized(WalkerStore.LOCK){try{state.deleteActive();startTracking(false);home();toast("Local walker deleted. Recovery copy kept.");}catch(IOException ex){toast(ex.getMessage());}}
            }).setNegativeButton("Cancel",null).show();
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=70||result!=RESULT_OK||data==null||data.getData()==null||recoveryExport==null)return;
        try(InputStream in=new FileInputStream(recoveryExport);OutputStream out=getContentResolver().openOutputStream(data.getData(),"w")){
            if(out==null)throw new IOException("Cannot open export destination");byte[] block=new byte[4096];int n;
            while((n=in.read(block))!=-1)out.write(block,0,n);out.flush();toast("Recovery copy exported.");
        }catch(IOException ex){toast("Export failed: "+ex.getMessage());}
        recoveryExport=null;
    }
    private void chooseMode(int mode){
        synchronized(WalkerStore.LOCK){
            if(state.returnPending||state.syncing){toast("Finish the pending sync before changing walking mode.");return;}
            if(state.active()&&state.mode==1)Native.timer(state.data,Native.now(),state.rate);
            if(mode!=state.mode){state.sensorLast=-1;state.sensorElapsed=0;}
            state.mode=mode;if(state.active())Native.resume(state.data,Native.now(),state.rate);save();
        }
        startTracking(true);
    }
    private void startTracking(boolean ask){
        boolean any=false,needsSensor=false,hasTimer=false;
        for(WalkerStore item:WalkerStore.all(this))if(item.active()&&!item.returnPending&&!item.syncing&&item.mode!=0){any=true;needsSensor|=item.mode==2;hasTimer|=item.mode==1;}
        if(!any){stopService(new Intent(this,WalkingService.class));return;}
        java.util.ArrayList<String> needed=new java.util.ArrayList<>();
        if(needsSensor && Build.VERSION.SDK_INT>=29 && checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION)!=PackageManager.PERMISSION_GRANTED)
            needed.add(Manifest.permission.ACTIVITY_RECOGNITION);
        if(ask && Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)
            needed.add(Manifest.permission.POST_NOTIFICATIONS);
        boolean consent=getSharedPreferences("walking",MODE_PRIVATE).getBoolean("trackingConsent",false);
        if(!needed.isEmpty()||!consent){
            if(ask) new AlertDialog.Builder(this).setTitle("Walking permissions")
                .setMessage((state.mode==2?"Physical activity access lets the app count and store your walking steps, including while the app is in the background with its tracking notification active.":"The optional timer creates and stores virtual steps while its tracking notification is active, including in the background.")+" Steps stay on this phone unless you choose to return the Pokémon to your console. Location is not accessed. The notification provides a Pause control.")
                .setPositiveButton("Continue",(dialog,which)->{getSharedPreferences("walking",MODE_PRIVATE).edit().putBoolean("trackingConsent",true).apply();if(needed.isEmpty())startTracking(false);else requestPermissions(needed.toArray(new String[0]),20);}).setNegativeButton("Cancel",null).show();
            if(ask||!consent||!hasTimer)return;
        }
        try{startForegroundService(new Intent(this,WalkingService.class));}catch(Exception ex){toast("Could not start tracking: "+ex.getMessage());}
    }
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants){super.onRequestPermissionsResult(request,permissions,grants);if(request==20)startTracking(false);if(request==30){Runnable action=pendingPeerPermission;pendingPeerPermission=null;boolean allowed=grants.length>0;for(int value:grants)allowed&=value==PackageManager.PERMISSION_GRANTED;if(allowed&&action!=null)action.run();else toast("Bluetooth permission is needed to find and connect nearby phones.");}}
    private void radarStart(){
        synchronized(WalkerStore.LOCK){
            if(!owned())return;long[] info=Native.info(state.data);if(info[Native.HAS_POKEMON]==0){toast("Send a Pokémon on a stroll from HGSS first.");return;}int visitor=(int)info[Native.VISITOR];
            if(visitor>0){Native.command(state.data,5,0);save();startBattle(visitor-1);return;}
            if(info[Native.WATTS]<10){toast("Poké Radar needs 10 watts.");return;}
            int[] choice=Native.encounter(state.data);if(choice[0]<0){toast("No usable route encounters.");return;}
            Native.command(state.data,1,10);encounter=choice[0];round=0;rounds=3-encounter+random(2);save();
        }
        page="radar";generation++;nextRustle();
    }
    private void nextRustle(){
        page="radar";target=-1;heading("Poké Radar");note("Wait for a rustling patch. Search "+(round+1)+" / "+rounds);radarButtons();
        final int epoch=generation;final int delay;
        synchronized(WalkerStore.LOCK){delay=500+random(900);save();}
        handler.postDelayed(()->{
            if(epoch!=generation||!page.equals("radar"))return;
            synchronized(WalkerStore.LOCK){target=random(4);save();}
            int[] windows={64,48,32,24};int ms=windows[Math.min(round,3)]*1000/30;radarDeadline=SystemClock.elapsedRealtime()+ms;
            heading("Follow the rustle!");note("Tap the patch marked !");radarButtons();
            handler.postDelayed(()->{if(epoch==generation&&page.equals("radar")&&SystemClock.elapsedRealtime()>=radarDeadline)result("It got away","The rustling stopped.");},ms);
        },delay);
    }
    private void radarButtons(){
        radarProgress=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);radarProgress.setMax(1000);radarProgress.setProgress(target<0?0:1000);panel.addView(radarProgress,new LinearLayout.LayoutParams(-1,dp(12)));
        final int progressEpoch=generation;final ProgressBar current=radarProgress;final long duration=Math.max(1,radarDeadline-SystemClock.elapsedRealtime());
        if(target>=0)handler.post(new Runnable(){public void run(){if(progressEpoch!=generation||!page.equals("radar")||radarProgress!=current)return;long left=radarDeadline-SystemClock.elapsedRealtime();current.setProgress((int)Math.max(0,Math.min(1000,left*1000/duration)));if(left>0)handler.postDelayed(this,40);}});
        LinearLayout row=null;
        for(int n=0;n<4;n++){if(n%2==0)row=patchRow();final int index=n;grassPatch(row,n+1,index==target,false,()->{
            if(target<0)return;
            if(SystemClock.elapsedRealtime()>radarDeadline){result("It got away","Try another Radar search.");return;}
            if(index!=target){if(round==0){generation++;nextRustle();}else result("It got away","The Pokémon escaped.");return;}
            generation++;round++;if(round>=rounds)startBattle(encounter);else nextRustle();
        });}
        button("Leave search",this::home);
    }
    private void startBattle(int which){generation++;battleAnimating=false;battleVisualAction=-1;battleAnimationStart=SystemClock.elapsedRealtime();previousPlayerHp=previousWildHp=4;battle=new int[]{4,4,0,0,0,which,0};battleScreen("Attack, evade or catch.");}
    private void battleScreen(String message){
        page="battle";heading("Wild "+Native.species(Native.command(state.data,9,battle[5])));note(message);note("Your HP: "+battle[0]+" / 4     Wild HP: "+battle[1]+" / 4");
        button("Attack",()->battleAction(0)).setEnabled(!battleAnimating);button("Evade",()->battleAction(1)).setEnabled(!battleAnimating);button("Throw Poké Ball",()->battleAction(2)).setEnabled(!battleAnimating);button("Leave",this::home);
    }
    private void battleAction(int action){
        if(battleAnimating)return;
        previousPlayerHp=battle[0];previousWildHp=battle[1];
        synchronized(WalkerStore.LOCK){if(!owned())return;Native.battle(state.data,battle,action);save();if(!state.error.isEmpty()){home();return;}}
        final int savedReward=battle[4]!=0?saveReward(false,battle[5],-1):-99;
        if(savedReward==-2)return;
        final int epoch=++generation;final String profile=state.profileId;
        battleVisualAction=action;battleAnimationStart=SystemClock.elapsedRealtime();battleAnimating=true;battleScreen(action==2?"The Poké Ball is flying…":action==1?"Evading…":"Attacking…");
        handler.postDelayed(()->{
            if(epoch!=generation||!state.profileId.equals(profile)||!page.equals("battle"))return;
            battleAnimating=false;
            String[] messages={"You attacked; the wild Pokémon replied.","It dodged and attacked!","A critical hit, then a reply!","A stare-down…","It fled!","Caught!","It escaped from the ball and fled.","You evaded and counter-attacked!","Your partner was defeated; up to 10 watts were lost."};
            if(battle[4]!=0){showReward(savedReward,false,battle[5]);return;}
            if(battle[3]!=0){result(messages[battle[6]],"Your walking partner is safe.");return;}battleScreen(messages[battle[6]]);
        },action==2?1800:1200);
    }
    private void dowseStart(){
        synchronized(WalkerStore.LOCK){
            if(!owned())return;if(Native.info(state.data)[Native.HAS_POKEMON]==0){toast("Dowsing needs a walking companion.");return;}if(Native.info(state.data)[Native.WATTS]<3){toast("Dowsing needs 3 watts.");return;}
            item=Native.command(state.data,2,state.expandedItems?1:0);if(item<0){toast("No usable route item data.");return;}
            Native.command(state.data,1,3);hidden=random(6);attempts=2;empty=-1;save();
        }
        generation++;dowseScreen("An item is hidden in one of six patches.");
    }
    private void dowseScreen(String message){
        page="dowsing";heading("Dowsing");note(message);note(attempts+" attempts left");
        LinearLayout row=null;
        for(int n=0;n<6;n++){if(n%3==0)row=patchRow();final int index=n;View b=grassPatch(row,n+1,false,n==empty,()->{
            if(index==hidden){storeReward(true,item,-1);return;}
            empty=index;attempts--;if(attempts==0){result("Nothing found","Try again on your next search.");return;}
            int distance=Math.abs(index%3-hidden%3)+Math.abs(index/3-hidden/3);dowseScreen(distance<=1?"It's near!":"It's far away…");
        });b.setEnabled(n!=empty);}
        button("Leave search",this::home);
    }
    private int saveReward(boolean isItem,int choice,int slot){
        final int result;
        synchronized(WalkerStore.LOCK){if(!owned())return -2;result=Native.command(state.data,isItem?10:3,((slot+1)<<(isItem?16:8))|choice);
            try{if(result>0)state.archiveCurrent("reward");state.save();}
            catch(IOException ex){state.mode=0;state.error="Save failed. Keep the app open and retry saving. "+ex.getMessage();home();return -2;}}
        return result;
    }
    private void storeReward(boolean isItem,int choice,int slot){int saved=saveReward(isItem,choice,slot);if(saved!=-2)showReward(saved,isItem,choice);}
    private void showReward(int result,boolean isItem,int choice){
        if(result<0){
            page="replace";heading("Pack full");note((isItem?"Found "+Native.item(Native.command(state.data,8,choice)):"Caught "+Native.species(Native.command(state.data,9,choice)))+". Choose a slot to replace, or leave the new reward.");
            for(int n=0;n<3;n++){final int target=n;int id=Native.command(state.data,isItem?7:6,n);button("Replace "+(isItem?Native.item(id):(id>0&&id<494?Native.species(id):"Empty")),()->storeReward(isItem,choice,target));}
            button("Keep current pack",this::home);
        } else result(result==1?(isItem?"You found "+Native.item(Native.command(state.data,8,choice))+"!":"You caught "+Native.species(Native.command(state.data,9,choice))+"!"):"Unusable reward",result==1?"Saved. It is ready to return to HGSS.":"No reward was added.");
    }
    private void pack(){generation++;page="pack";heading("Your pack");if(!owned()){home();return;}
        synchronized(WalkerStore.LOCK){for(int n=0;n<3;n++){int id=Native.command(state.data,6,n);note("Pokémon "+(n+1)+": "+(id>0&&id<494?Native.species(id):"Empty"));}
            for(int n=0;n<3;n++){int id=Native.command(state.data,7,n);note("Item "+(n+1)+": "+(Native.item(id)));}for(int n=0;n<10;n++){int id=Native.command(state.data,11,n);if(id>0)note("Friend gift "+(n+1)+": "+Native.item(id));}}
        button("Back",this::home);
    }
    private void card(){generation++;page="card";heading("Trainer card");if(!owned()){home();return;}
        synchronized(WalkerStore.LOCK){long[] i=Native.info(state.data);note("Trainer: "+Native.text(state.data,0));note("Route: "+Native.text(state.data,2));note("Bond: "+i[Native.BOND]+" / 255");note("Today: "+i[Native.TODAY]+" steps");note("Lifetime: "+i[Native.TOTAL]+" steps");}
        button("Back",this::home);
    }
    private void widgetErrorScreen(String profileId){
        WalkerStore affected=profileId==null?state:WalkerStore.forProfile(this,profileId);
        generation++;handler.removeCallbacks(classicClock);stopClassicAudio();page="widgetError";heading("Widget needs attention");
        if(affected==null){note("This widget profile is no longer available. Reconfigure the widget from its profile chooser.");}
        else{
            note("Profile: "+WalkerStore.profileName(this,affected.profileId));
            String issue=affected.error;
            boolean recoverableSave=affected.recoverableWriteFailure();
            if(recoverableSave)note("The saved Pokémon data is still valid, but its latest app state was not saved.");
            else if(affected.data!=null)note("This profile is protected by an interrupted operation. Keep its saved data intact and resolve the operation before using menus.");
            else note("The saved state could not be safely opened or verified. The app has not written over it.");
            note(issue.isEmpty()?"No saved-state error is currently reported.":issue);
            if(recoverableSave)button("Retry verified save",()->{
                synchronized(WalkerStore.LOCK){
                    try{
                        affected.save();
                        PokewalkerWidgetProvider.updateAll(this);
                        toast("Save verified. Pokéwalker menus are available again.");
                        if(state.profileId.equals(affected.profileId))home();else widgetErrorScreen(profileId);
                    }catch(IOException ex){
                        toast("Save still needs attention: "+ex.getMessage());
                        widgetErrorScreen(profileId);
                    }
                }
            });
        }
        button("Choose another profile",this::profilesScreen);button("Back to app",this::home);
    }
    private void syncScreen(){
        generation++;page="sync";heading("Sync do console");picture.setVisibility(View.GONE);stats.setVisibility(View.GONE);homeProfileChip.setVisibility(View.GONE);homeMetrics.setVisibility(View.GONE);
        syncReceiverStatus=null;syncConnectionStatus=null;syncNetworkEvents=null;syncPhoneWalkerStatus=null;syncLastEvent=null;
        syncStatusBadge=null;syncStatusTitle=null;syncStatusDetail=null;syncStepTcp=null;syncStepFrame=null;syncStepSaved=null;
        note("O app escuta. O DSi inicia a conexão.");
        LinearLayout profile=syncCard(PANEL);profile.setOrientation(LinearLayout.HORIZONTAL);profile.setGravity(Gravity.CENTER_VERTICAL);profile.setPadding(dp(12),dp(9),dp(12),dp(9));
        TextView profileDot=text("●",13,0xff0b1a28);profileDot.setGravity(Gravity.CENTER);profileDot.setBackground(round(MINT,dp(16)));profile.addView(profileDot,new LinearLayout.LayoutParams(dp(30),dp(30)));
        TextView profileName=text("PERFIL  ·  "+WalkerStore.profileName(this,state.profileId).toUpperCase(java.util.Locale.ROOT),13,INK);profileName.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);LinearLayout.LayoutParams profileNameLp=new LinearLayout.LayoutParams(0,-2,1);profileNameLp.leftMargin=dp(10);profile.addView(profileName,profileNameLp);addCard(profile);

        LinearLayout status=syncCard(PANEL);status.setOrientation(LinearLayout.VERTICAL);status.setPadding(dp(14),dp(13),dp(14),dp(14));
        syncStatusBadge=text("AGUARDANDO",11,GOLD);syncStatusBadge.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);status.addView(syncStatusBadge);
        syncStatusTitle=text("Receptor ativo",19,INK);syncStatusTitle.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);status.addView(syncStatusTitle);
        syncStatusDetail=text("Esperando conexão do DSi",14,MUTED);status.addView(syncStatusDetail);
        syncConnectionStatus=text("TCP "+DirectSyncProtocol.PORT+" · sem IP manual",13,MINT);syncConnectionStatus.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);status.addView(syncConnectionStatus);
        addCard(status);

        LinearLayout stages=syncCard(PANEL);stages.setOrientation(LinearLayout.VERTICAL);stages.setPadding(dp(13),dp(10),dp(13),dp(11));
        TextView stageHeader=text("ETAPAS DA SESSÃO",11,MUTED);stageHeader.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);stages.addView(stageHeader);
        flowStep(stages,"1","Connect → Console","Arma o perfil e deixa o celular escutando na porta TCP "+DirectSyncProtocol.PORT+".");
        addSyncStep(stages,"2","TCP aceito do DSi","Aguardando conexão",0);
        addSyncStep(stages,"3","Quadro do protocolo","Aguardando pedido",1);
        addSyncStep(stages,"4","Save / retorno confirmado","Nenhuma transferência recebida ainda",2);
        addCard(stages);

        LinearLayout events=syncCard(PANEL);events.setOrientation(LinearLayout.VERTICAL);events.setPadding(dp(13),dp(10),dp(13),dp(11));
        TextView eventHeader=text("EVENTOS RECENTES",11,MUTED);eventHeader.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);events.addView(eventHeader);
        syncNetworkEvents=text(DirectSyncService.connectionEvents(this),13,INK);syncNetworkEvents.setPadding(0,dp(5),0,0);events.addView(syncNetworkEvents);
        syncLastEvent=text("Último evento · "+DirectSyncService.lastEvent(this),12,MUTED);events.addView(syncLastEvent);
        addCard(events);

        LinearLayout phone=syncCard(0xff123a3a);phone.setOrientation(LinearLayout.VERTICAL);phone.setPadding(dp(13),dp(11),dp(13),dp(11));
        TextView phoneHeader=text("POKÉMON NO CELULAR",11,MINT);phoneHeader.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);phone.addView(phoneHeader);
        syncPhoneWalkerStatus=text(receiverWalkerStatus(),15,INK);phone.addView(syncPhoneWalkerStatus);addCard(phone);

        note("No Connect do Pokéwalker, escolha Console. O app identifica a direção pelo Pokémon deste perfil e espera o pedido do homebrew.");
        note("Sem TCP aceito, o app não vê tentativas bloqueadas antes da porta.");
        if(state.returnPending)note("Retorno pendente: mantenha o receptor ligado enquanto o homebrew conclui a gravação no save HGSS.");
        else if(state.active())note("Este perfil tem um Pokémon no celular. Use Return to HGSS (Y) para devolvê-lo.");
        else note("Este perfil está vazio. Use Send to phone (A) para receber do HGSS.");

        boolean enabled=DirectSyncService.enabled(this)&&state.profileId.equals(DirectSyncService.targetProfileId(this));
        button(enabled?"Connect to Console · rearmar":"Iniciar receptor · Connect to Console",()->{
            startConsoleReceiver();handler.postDelayed(this::syncScreen,350);
        });
        if(enabled)button("Parar receptor",()->{
            DirectSyncService.stop(this);WidgetConfigActivity.clearStatusForProfile(this,state.profileId);handler.postDelayed(this::syncScreen,350);
        });
        button("Atualizar status",this::syncScreen);button("Voltar",this::home);
        refreshSyncReceiverStatus();
    }
    private LinearLayout syncCard(int color){LinearLayout card=new LinearLayout(this);card.setBackground(round(color,dp(14)));return card;}
    private void addCard(View card){LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(8);panel.addView(card,lp);}
    private void addSyncStep(LinearLayout parent,String number,String title,String initial,int index){
        LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(0,dp(4),0,dp(4));
        TextView badge=text(number,12,0xff0b1a28);badge.setTypeface(android.graphics.Typeface.DEFAULT,android.graphics.Typeface.BOLD);badge.setGravity(Gravity.CENTER);badge.setBackground(round(0xff9ebeb7,dp(12)));LinearLayout.LayoutParams badgeLp=new LinearLayout.LayoutParams(dp(24),dp(24));badgeLp.rightMargin=dp(10);row.addView(badge,badgeLp);
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);row.addView(copy,new LinearLayout.LayoutParams(0,-2,1));copy.addView(text(title,14,INK));
        TextView detail=text(initial,12,MUTED);copy.addView(detail);if(index==0)syncStepTcp=detail;else if(index==1)syncStepFrame=detail;else syncStepSaved=detail;
        parent.addView(row);
    }
    private String consoleReceiverWaitingStatus(){
        return DirectSyncService.operationFor(state)==DirectSyncProtocol.OP_ARM_PULL
                ?"Connect to Console armado · Return to HGSS · esperando o homebrew"
                :"Connect to Console armado · Send to phone · esperando o homebrew";
    }
    private void startConsoleReceiver(){
        try{
            WidgetConfigActivity.setStatusForProfile(this,state.profileId,consoleReceiverWaitingStatus());
            DirectSyncService.start(this,state.profileId,DirectSyncService.operationFor(state));
        }catch(RuntimeException ex){
            WidgetConfigActivity.setStatusForProfile(this,state.profileId,"Erro: "+ex.getMessage());
            toast("Não foi possível iniciar o receptor DSi Sync: "+ex.getMessage());
        }
    }
    private void openConsoleSync(){
        startConsoleReceiver();
        syncScreen();
        handler.postDelayed(()->{if(page.equals("sync"))syncScreen();},400);
    }
    private void refreshSyncReceiverStatus(){
        if(!page.equals("sync"))return;
        String status=DirectSyncService.status(this);String event=DirectSyncService.lastEvent(this);
        if(syncStatusBadge!=null)syncStatusBadge.setText(syncBadge(status));
        if(syncStatusTitle!=null)syncStatusTitle.setText(syncTitle(status));
        if(syncStatusDetail!=null)syncStatusDetail.setText(connectionStatus());
        if(syncReceiverStatus!=null)syncReceiverStatus.setText("Receptor: "+receiverStatus());
        if(syncConnectionStatus!=null){syncConnectionStatus.setText("TCP "+DirectSyncProtocol.PORT+" · sem IP manual");styleConnectionIndicator();}
        if(syncNetworkEvents!=null)syncNetworkEvents.setText(DirectSyncService.connectionEvents(this));
        if(syncLastEvent!=null)syncLastEvent.setText("Último evento · "+event);
        if(syncPhoneWalkerStatus!=null)syncPhoneWalkerStatus.setText(receiverWalkerStatus());
        boolean accepted=status.startsWith("DSi TCP connected from ")||status.contains("protocol frame")||status.startsWith("DSi direction approved")||status.equals("DSi waiting for Connect to Console direction");
        boolean frame=status.contains("protocol frame")||status.startsWith("DSi direction approved")||status.equals("DSi waiting for Connect to Console direction");
        boolean saved=event.contains("Pokémon salvo no celular")||event.contains("Retorno confirmado pelo DSi");
        if(syncStepTcp!=null){syncStepTcp.setText(accepted?"Conexão TCP aceita":"Aguardando conexão do DSi");syncStepTcp.setTextColor(accepted?MINT:MUTED);}
        if(syncStepFrame!=null){syncStepFrame.setText(frame?"Pedido recebido · aguardando autorização":"Aguardando quadro do protocolo");syncStepFrame.setTextColor(frame?MINT:MUTED);}
        if(syncStepSaved!=null){syncStepSaved.setText(saved?"Transferência confirmada":"Nenhuma transferência confirmada ainda");syncStepSaved.setTextColor(saved?MINT:MUTED);}
    }
    private String syncBadge(String status){if(status.equals("Stopped"))return "PARADO";if(status.startsWith("Could not listen")||status.startsWith("Direct sync error")||status.startsWith("Last DSi request failed"))return "ATENÇÃO";if(status.startsWith("DSi TCP connected")||status.contains("protocol frame")||status.startsWith("DSi direction approved"))return "CONECTADO";return "AGUARDANDO";}
    private String syncTitle(String status){if(status.equals("Stopped"))return "Receptor parado";if(status.startsWith("Could not listen")||status.startsWith("Direct sync error")||status.startsWith("Last DSi request failed"))return "Falha na conexão";if(status.startsWith("DSi TCP connected")||status.contains("protocol frame")||status.startsWith("DSi direction approved"))return "DSi conectado";return "Receptor ativo";}
    private String receiverWalkerStatus(){
        synchronized(WalkerStore.LOCK){
            WalkerStore receiver=DirectSyncService.targetStore(this);
            String pokemon=receiver.data==null?"nenhum":Native.text(receiver.data,3);
            return "Pokémon no celular ("+DirectSyncService.targetProfileName(this)+"): "+pokemon+(receiver.returnPending?" · retorno pendente":"");
        }
    }
    private String receiverStatus(){
        String status=DirectSyncService.status(this);
        if(status.equals("Stopped"))return "parado";
        if(status.startsWith("Starting listener on port "))return "iniciando listener TCP na porta "+DirectSyncProtocol.PORT;
        String listeningPrefix="Listening for DSi on port "+DirectSyncProtocol.PORT+" · ";
        if(status.startsWith(listeningPrefix))return "escutando TCP na porta "+DirectSyncProtocol.PORT+" · direção armada: "+status.substring(listeningPrefix.length());
        if(status.startsWith("Waiting for DSi on port "))return "aguardando o DSi na porta "+DirectSyncProtocol.PORT;
        String acceptedPrefix="DSi TCP connected from ";
        if(status.startsWith(acceptedPrefix))return "TCP aceito do DSi ("+status.substring(acceptedPrefix.length())+") · aguardando quadro";
        if(status.equals("DSi protocol frame received · processing request"))return "quadro do protocolo recebido · processando solicitação";
        if(status.startsWith("DSi direction approved · "))return "direção autorizada pelo Connect to Console · "+status.substring("DSi direction approved · ".length());
        if(status.equals("DSi waiting for Connect to Console direction"))return "TCP aceito · esperando o jogador armar a mesma direção no app";
        if(status.equals("DSi TCP closed before complete frame"))return "TCP do DSi aceito, mas fechado antes do quadro completo";
        if(status.equals("DSi TCP disconnected after protocol frame"))return "cliente fechou o TCP depois de enviar um quadro; receptor continua ativo";
        if(status.equals("DSi TCP timeout waiting for frame"))return "TCP aceito, mas o quadro não chegou antes do tempo limite";
        if(status.equals("DSi connected · processing request"))return "DSi conectado · processando solicitação";
        if(status.startsWith("Could not listen: "))return "não foi possível iniciar a escuta: "+status.substring("Could not listen: ".length());
        if(status.startsWith("Last DSi request failed: "))return "última solicitação falhou: "+status.substring("Last DSi request failed: ".length());
        if(status.startsWith("Direct sync error: "))return "erro de conexão: "+status.substring("Direct sync error: ".length());
        return status;
    }
    private String connectionStatus(){
        String status=DirectSyncService.status(this);
        if(status.equals("Stopped"))return "RECEPTOR PARADO";
        if(status.startsWith("Starting listener on port "))return "INICIANDO · preparando TCP "+DirectSyncProtocol.PORT;
        String listeningPrefix="Listening for DSi on port "+DirectSyncProtocol.PORT+" · ";
        if(status.startsWith(listeningPrefix))return "SEM CONEXÃO ACEITA · escutando na porta "+DirectSyncProtocol.PORT+" · "+status.substring(listeningPrefix.length());
        if(status.startsWith("Waiting for DSi on port "))return "SEM CONEXÃO ACEITA · escutando na porta "+DirectSyncProtocol.PORT;
        String accepted="DSi TCP connected from ";
        if(status.startsWith(accepted))return "TCP CONECTADO · "+status.substring(accepted.length());
        if(status.equals("DSi protocol frame received · processing request"))return "QUADRO RECEBIDO · processando protocolo";
        if(status.startsWith("DSi direction approved · "))return "DIREÇÃO AUTORIZADA · "+status.substring("DSi direction approved · ".length());
        if(status.equals("DSi waiting for Connect to Console direction"))return "TCP CONECTADO · aguardando autorização no Connect to Console";
        if(status.equals("DSi TCP closed before complete frame"))return "DESCONEXÃO · fechou antes do quadro completo";
        if(status.equals("DSi TCP disconnected after protocol frame"))return "DESCONECTADO · listener segue ativo";
        if(status.equals("DSi TCP timeout waiting for frame"))return "TEMPO ESGOTADO · TCP aceito, sem quadro completo";
        if(status.startsWith("Could not listen: "))return "ERRO AO ABRIR A PORTA · "+status.substring("Could not listen: ".length());
        if(status.startsWith("Last DSi request failed: "))return "FALHA NO QUADRO · "+status.substring("Last DSi request failed: ".length());
        if(status.startsWith("Direct sync error: "))return "ERRO NO LISTENER · "+status.substring("Direct sync error: ".length());
        return status;
    }
    private void styleConnectionIndicator(){
        if(syncConnectionStatus==null)return;
        String status=DirectSyncService.status(this);
        int tint;
        if(status.startsWith("DSi TCP connected from ")||status.equals("DSi protocol frame received · processing request")||status.startsWith("DSi direction approved · "))tint=MINT;
        else if(status.startsWith("Listening for DSi")||status.startsWith("Waiting for DSi")||status.startsWith("Starting listener")||status.equals("DSi waiting for Connect to Console direction"))tint=GOLD;
        else if(status.equals("Stopped"))tint=MUTED;
        else tint=0xffff786f;
        syncConnectionStatus.setTextColor(MINT);
        if(syncStatusBadge!=null){syncStatusBadge.setTextColor(tint);syncStatusBadge.setPadding(dp(8),dp(1),dp(8),dp(1));syncStatusBadge.setBackground(round(tint==MINT?0xff123a3a:tint==GOLD?0xff4b3922:0xff402a2c,dp(8)));}
    }
    @Override public void onBackPressed(){if(syncBusy){toast("Please wait for sync to finish.");return;}if(!page.equals("home"))home();else super.onBackPressed();}
    private final class WalkerPicture extends View {
        final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        Bitmap shell; int shellRes;
        WalkerPicture(){super(MainActivity.this);}
        private Bitmap currentShell(){
            int res=SkinManager.resource(SkinManager.profileSkin(MainActivity.this,state==null?"":state.profileId));
            if(shell==null||shellRes!=res){if(shell!=null&&!shell.isRecycled())shell.recycle();shell=BitmapFactory.decodeResource(getResources(),res);shellRes=res;}
            return shell;
        }
        int imageButton(float x,float y){
            float r=Math.min(getWidth()*.46f,getHeight()*.48f),cx=getWidth()/2f,cy=getHeight()/2f;
            for(int button=0;button<3;button++){
                float bx=cx+(button-1)*r*.45f,by=cy+r*(button==1?.61f:.55f);
                float radius=Math.max(dp(24),r*(button==1?.16f:.13f));
                if((x-bx)*(x-bx)+(y-by)*(y-by)<=radius*radius)return button;
            }
            return -1;
        }
        private void bitmap(Canvas c,int offset,int width,int height,float x,float y,float scale,boolean flip){
            int[] colors={0xffb4b7aa,0xff8d9383,0xff555e4c,0xff232b1d};paint.setAntiAlias(false);
            for(int py=0;py<height;py++)for(int px=0;px<width;px++){int at=offset+((py/8)*width+px)*2,bit=py&7,color=((state.data[at]>>bit)&1)*2+((state.data[at+1]>>bit)&1);if(color!=0){paint.setColor(colors[color]);int dx=flip?width-1-px:px;c.drawRect(x+dx*scale,y+py*scale,x+(dx+1)*scale,y+(py+1)*scale,paint);}}
            paint.setAntiAlias(true);
        }
        private void drawBattle(Canvas c,float left,float top,float right,float bottom){
            long elapsed=Math.max(0,SystemClock.elapsedRealtime()-battleAnimationStart);float scale=Math.max(1,(float)Math.floor(Math.min((right-left)/96,(bottom-top)/64)));
            float x=(left+right-96*scale)/2,y=(top+bottom-64*scale)/2;
            int frame=(int)(elapsed/160)&1;float player=56,wild=8;boolean showWild=true,showPlayer=true;
            float t=Math.min(1,elapsed/(battleVisualAction==2?1800f:1200f));
            if(battleVisualAction<0)wild=8-Math.max(0,1-elapsed/450f)*40;
            else if(battleAnimating&&battleVisualAction==0){if(t<.45f)player-=16*(float)Math.sin(t/.45*Math.PI);else wild+=16*(float)Math.sin((t-.45)/.55*Math.PI);if(t>.3f&&t<.48f)showWild=frame==0;if(t>.7f&&t<.86f)showPlayer=frame==0;}
            else if(battleAnimating&&battleVisualAction==1){wild+=16*(float)Math.sin(Math.min(1,t*2)*Math.PI);player+=Math.min(8,t*20);if(battle[6]==7&&t>.5f)player=56-16*(float)Math.sin((t-.5)*2*Math.PI);if(battle[6]==4)wild-=t*42;}
            boolean ball=battleAnimating&&battleVisualAction==2;
            if(ball&&t>.28f)showWild=false;
            if(showWild)bitmap(c,0x9a7e+battle[5]*384+frame*192,32,24,x+wild*scale,y+22*scale,scale,(state.data[0x8f52+battle[5]*16+14]&1)==0);
            if(showPlayer)bitmap(c,0x91be+frame*192,32,24,x+player*scale,y+22*scale,scale,false);
            if(ball){float q=Math.min(1,t/.3f),bx=x+(70-46*q)*scale,by=y+(34-15*(float)Math.sin(q*Math.PI))*scale;if(t>.3f){bx=x+(24+(t<.8f?(float)Math.sin(t*40)*2:0))*scale;by=y+38*scale;}
                paint.setColor(0xff232b1d);c.drawCircle(bx,by,5*scale,paint);paint.setColor(0xffb4b7aa);c.drawCircle(bx,by,3*scale,paint);paint.setColor(0xff232b1d);c.drawRect(bx-4*scale,by-scale/2,bx+4*scale,by+scale/2,paint);
                if(t>.8f&&battle[4]!=0)for(int n=-1;n<=1;n++){float sx=bx+n*9*scale,sy=by-(n==0?13:8)*scale;c.drawRect(sx-scale,sy-3*scale,sx+scale,sy+3*scale,paint);c.drawRect(sx-3*scale,sy-scale,sx+3*scale,sy+scale,paint);}
                if(t>.8f&&battle[4]==0){paint.setColor(0xff232b1d);c.drawLine(bx-9*scale,by-8*scale,bx-3*scale,by-3*scale,paint);c.drawLine(bx+9*scale,by-8*scale,bx+3*scale,by-3*scale,paint);}
            }
            int hpPlayer=battleAnimating&&t<.8f?previousPlayerHp:battle[0],hpWild=battleAnimating&&t<.4f?previousWildHp:battle[1];
            for(int n=0;n<4;n++){paint.setColor(n<hpWild?0xff232b1d:0xff99b484);c.drawRect(x+(8+n*6)*scale,y+54*scale,x+(12+n*6)*scale,y+57*scale,paint);paint.setColor(n<hpPlayer?0xff232b1d:0xff99b484);c.drawRect(x+(56+n*6)*scale,y+54*scale,x+(60+n*6)*scale,y+57*scale,paint);}
        }
        private RectF drawShell(Canvas canvas,float cx,float cy,float r){
            paint.setAntiAlias(true);paint.setFilterBitmap(true);
            canvas.drawBitmap(currentShell(),null,new RectF(cx-r,cy-r,cx+r,cy+r),paint);
            RectF lcd=new RectF(cx-r+2*r*230/1005f,cy-r+2*r*261/1003f,cx-r+2*r*783/1005f,cy-r+2*r*644/1003f);
            Path mask=new Path();mask.addRoundRect(lcd,r*.035f,r*.035f,Path.Direction.CW);
            canvas.save();canvas.clipPath(mask);canvas.drawColor(0xffb4b7aa);return lcd;
        }
        @Override protected void onDraw(Canvas canvas){
            super.onDraw(canvas);float w=getWidth(),h=getHeight(),cx=w/2,cy=h/2,r=Math.min(w*.46f,h*.48f);
            RectF lcd=drawShell(canvas,cx,cy,r);
            synchronized(WalkerStore.LOCK){
                byte[] pixels=null;
                if(visitReward!=null&&(page.equals("visit")||page.equals("peer")))
                    pixels=Native.visitFrame(state.data,visitReward,(int)((SystemClock.elapsedRealtime()-visitStarted)/250));
                else if(page.equals("peer")&&peerSession!=null)pixels=peerSession.frame();
                else if(page.equals("classic"))pixels=classicPixels;
                if(pixels==null&&state.data!=null&&!state.returnPending&&!state.revoked&&!state.returnCompleted)
                    pixels=Native.classicFrame(state.data,new int[40],SystemClock.elapsedRealtime());
                else if(pixels==null&&state.data==null)
                    pixels=Native.classicFrame(WalkerClassicData.image(null),new int[40],SystemClock.elapsedRealtime());
                if(page.equals("battle")&&battle!=null&&state.data!=null)drawBattle(canvas,lcd.left,lcd.top,lcd.right,lcd.bottom);
                else if(pixels!=null){
                    float scale=Math.min(lcd.width()/96,lcd.height()/64),x=lcd.centerX()-48*scale,y=lcd.centerY()-32*scale;
                    int[] colors=WalkerLcdPalette.colors(state.classicContrast);paint.setAntiAlias(false);paint.setFilterBitmap(false);
                    for(int py=0;py<64;py++)for(int px=0;px<96;px++){
                        paint.setColor(colors[pixels[py*96+px]&3]);
                        canvas.drawRect(Math.round(x+px*scale),Math.round(y+py*scale),Math.round(x+(px+1)*scale),Math.round(y+(py+1)*scale),paint);
                    }
                }
            }
            canvas.restore();paint.setAntiAlias(true);
            if(page.equals("peer")||page.equals("classic")||
                    (page.equals("visit")&&SystemClock.elapsedRealtime()-visitStarted<10000))
                postInvalidateDelayed(100);
        }
    }
}
