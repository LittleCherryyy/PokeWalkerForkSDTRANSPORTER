package io.github.sdtransporter.pokewalker;

import android.app.Activity;
import android.app.AlertDialog;
import android.appwidget.AppWidgetManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;

/** Profile and shell selection for the Pokéwalker home-screen widget. */
public final class WidgetConfigActivity extends Activity {
    static final String PREFS = "pokewalker_widget_profiles";
    private static final int BG=0xff0b1a28, PANEL=0xff17303b, PANEL_SELECTED=0xff123a3a;
    private static final int INK=0xffe9f6f0, MUTED=0xff9ebeb7, MINT=0xff44ddb3, GOLD=0xfffcca66;
    private int widgetId=AppWidgetManager.INVALID_APPWIDGET_ID;
    private String selectedProfile="",selectedSkin="";
    private ArrayList<WalkerProfiles.Entry> entries=new ArrayList<>();

    @Override protected void onCreate(Bundle state){
        super.onCreate(state);
        setResult(RESULT_CANCELED);
        Bundle extras=getIntent().getExtras();
        if(extras!=null)widgetId=extras.getInt(AppWidgetManager.EXTRA_APPWIDGET_ID,widgetId);
        if(widgetId==AppWidgetManager.INVALID_APPWIDGET_ID){finish();return;}
        entries=WalkerStore.profileEntries(this);
        String saved=profileFor(this,widgetId);
        for(WalkerProfiles.Entry entry:entries)if(entry.id.equals(saved)){selectedProfile=entry.id;break;}
        if(selectedProfile.isEmpty()){
            String current=WalkerStore.get(this).profileId;
            for(WalkerProfiles.Entry entry:entries)if(entry.id.equals(current)){selectedProfile=entry.id;break;}
        }
        if(selectedProfile.isEmpty()&&!entries.isEmpty())selectedProfile=entries.get(0).id;
        selectedSkin=SkinManager.widgetSkin(this,widgetId,selectedProfile);
        showProfileChooser();
    }

    private void showProfileChooser(){
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(BG);
        LinearLayout page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(20),dp(22),dp(20),dp(24));scroll.addView(page);

        TextView back=label("‹   Adicionar widget",23,INK);back.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        back.setContentDescription("Adicionar widget");page.addView(back);
        TextView intro=label("Escolha o perfil deste Pokéwalker",17,INK);intro.setPadding(0,dp(18),0,dp(3));page.addView(intro);
        page.addView(label("O destino do sync acompanha este perfil.",14,MUTED));

        for(WalkerProfiles.Entry entry:entries)page.addView(profileCard(entry));

        LinearLayout preview=card(PANEL);preview.setOrientation(LinearLayout.VERTICAL);preview.setPadding(dp(14),dp(13),dp(14),dp(15));
        addTopGap(page,preview,dp(16));
        preview.addView(label("PRÉVIA DO WIDGET",12,MUTED));
        LinearLayout sampleRow=new LinearLayout(this);sampleRow.setGravity(Gravity.CENTER_VERTICAL);sampleRow.setPadding(0,dp(8),0,dp(2));preview.addView(sampleRow);
        FrameLayout device=new FrameLayout(this);LinearLayout.LayoutParams deviceLp=new LinearLayout.LayoutParams(dp(150),dp(150));deviceLp.rightMargin=dp(12);sampleRow.addView(device,deviceLp);
        ImageView shell=new ImageView(this);shell.setImageResource(SkinManager.resource(selectedSkin));shell.setScaleType(ImageView.ScaleType.FIT_CENTER);device.addView(shell,new FrameLayout.LayoutParams(-1,-1));
        TextView lcd=label(previewPokemon()+"\n"+previewSteps(),9,0xff232b1d);lcd.setTypeface(Typeface.MONOSPACE,Typeface.BOLD);lcd.setGravity(Gravity.CENTER);lcd.setBackgroundColor(0xffb8bdaa);lcd.setPadding(dp(3),0,dp(3),0);lcd.setMaxLines(2);
        FrameLayout.LayoutParams lcdLp=new FrameLayout.LayoutParams(dp(83),dp(55),Gravity.TOP|Gravity.CENTER_HORIZONTAL);lcdLp.topMargin=dp(39);device.addView(lcd,lcdLp);
        LinearLayout previewCopy=new LinearLayout(this);previewCopy.setOrientation(LinearLayout.VERTICAL);sampleRow.addView(previewCopy,new LinearLayout.LayoutParams(0,-2,1));
        previewCopy.addView(label(selectedProfileName(),14,MINT));
        previewCopy.addView(label(previewPokemon().equals("Sem Pokémon")?"Perfil pronto para receber":"Pokémon no celular",14,INK));
        TextView skin=smallAction("Aparência · "+SkinManager.name(selectedSkin));LinearLayout.LayoutParams skinLp=new LinearLayout.LayoutParams(-1,dp(42));skinLp.topMargin=dp(8);previewCopy.addView(skin,skinLp);
        skin.setOnClickListener(v->showSkinChooser());

        LinearLayout info=card(PANEL_SELECTED);info.setOrientation(LinearLayout.VERTICAL);info.setPadding(dp(14),dp(12),dp(14),dp(12));
        TextView infoTitle=label("▣   Sem endereço IP ou porta",14,MINT);info.addView(infoTitle);
        info.addView(label("O widget usa o receptor local do app. Toque no LCD para abrir controles e use os três botões para navegar.",13,MUTED));
        addTopGap(page,info,dp(12));

        TextView add=primaryAction("Adicionar widget");LinearLayout.LayoutParams addLp=new LinearLayout.LayoutParams(-1,dp(56));addLp.topMargin=dp(14);page.addView(add,addLp);
        add.setOnClickListener(v->finishConfiguration());
        page.addView(label("O visual do widget segue o shell escolhido para este perfil.",12,MUTED),new LinearLayout.LayoutParams(-1,-2));
        setContentView(scroll);
    }

    private View profileCard(WalkerProfiles.Entry entry){
        boolean selected=entry.id.equals(selectedProfile);
        LinearLayout row=card(selected?PANEL_SELECTED:PANEL);row.setOrientation(LinearLayout.HORIZONTAL);row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(13),dp(9),dp(13),dp(9));row.setMinimumHeight(dp(72));
        GradientDrawable bg=shape(selected?PANEL_SELECTED:PANEL,dp(14));if(selected)bg.setStroke(dp(1),MINT);row.setBackground(bg);
        TextView badge=label(initial(entry.name),13,BG);badge.setTypeface(Typeface.DEFAULT,Typeface.BOLD);badge.setGravity(Gravity.CENTER);badge.setBackground(shape(MINT,dp(20)));
        LinearLayout.LayoutParams badgeLp=new LinearLayout.LayoutParams(dp(38),dp(38));badgeLp.rightMargin=dp(11);row.addView(badge,badgeLp);
        LinearLayout copy=new LinearLayout(this);copy.setOrientation(LinearLayout.VERTICAL);row.addView(copy,new LinearLayout.LayoutParams(0,-2,1));
        copy.addView(label(entry.name+(entry.id.equals(WalkerStore.get(this).profileId)?" · selecionado":""),15,INK));
        copy.addView(label(profilePokemon(entry.id),12,MUTED));
        TextView radio=label(selected?"◉":"○",22,selected?MINT:MUTED);radio.setGravity(Gravity.CENTER);row.addView(radio,new LinearLayout.LayoutParams(dp(30),dp(40)));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=dp(8);row.setLayoutParams(lp);
        row.setOnClickListener(v->{if(!entry.id.equals(selectedProfile)){selectedProfile=entry.id;selectedSkin=SkinManager.widgetSkin(this,widgetId,selectedProfile);showProfileChooser();}});
        return row;
    }

    private String profilePokemon(String profileId){
        for(WalkerStore store:WalkerStore.all(this))if(store.profileId.equals(profileId)&&store.active()&&store.data!=null){
            long[] info=Native.info(store.data);return Native.species((int)info[Native.SPECIES])+" · Lv "+info[Native.LEVEL];
        }
        return "Nenhum Pokémon no celular";
    }
    private String previewPokemon(){
        for(WalkerStore store:WalkerStore.all(this))if(store.profileId.equals(selectedProfile)&&store.active()&&store.data!=null){long[] info=Native.info(store.data);return Native.species((int)info[Native.SPECIES]);}
        return "Sem Pokémon";
    }
    private String previewSteps(){
        for(WalkerStore store:WalkerStore.all(this))if(store.profileId.equals(selectedProfile)&&store.active()&&store.data!=null){long[] info=Native.info(store.data);return String.format(java.util.Locale.ROOT,"%04d W",info[Native.WATTS]);}
        return "0000 W";
    }
    private String selectedProfileName(){for(WalkerProfiles.Entry entry:entries)if(entry.id.equals(selectedProfile))return entry.name;return "Pokéwalker";}
    private static String initial(String name){return name==null||name.trim().isEmpty()?"P":name.trim().substring(0,1).toUpperCase(java.util.Locale.ROOT);}

    private void showSkinChooser(){
        new AlertDialog.Builder(this).setTitle("Aparência do Pokéwalker")
            .setSingleChoiceItems(SkinManager.NAMES,SkinManager.indexOf(selectedSkin),(dialog,which)->{
                selectedSkin=SkinManager.IDS[which];dialog.dismiss();showProfileChooser();
            }).setNegativeButton("Voltar",null).show();
    }

    private void finishConfiguration(){
        if(selectedProfile.isEmpty())return;
        saveProfileFor(this,widgetId,selectedProfile);clearLegacyHost(this,widgetId);
        SkinManager.setProfileSkin(this,selectedProfile,selectedSkin);clearStatus(this,widgetId);
        PokewalkerWidgetProvider.updateWidget(this,AppWidgetManager.getInstance(this),widgetId);
        try{WalkingService.ensureRunning(this);}catch(Exception ignored){/* Widget remains available without sensor tracking. */}
        setResult(RESULT_OK,new Intent().putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,widgetId));finish();
    }

    private int dp(float x){return (int)(x*getResources().getDisplayMetrics().density+.5f);}
    private TextView label(String value,int size,int color){TextView view=new TextView(this);view.setText(value);view.setTextSize(size);view.setTextColor(color);view.setPadding(0,dp(2),0,dp(2));return view;}
    private TextView smallAction(String value){TextView view=label(value,12,MINT);view.setGravity(Gravity.CENTER);view.setBackground(shape(0xff21483f,dp(8)));view.setMinHeight(dp(42));return view;}
    private TextView primaryAction(String value){TextView view=label(value,16,BG);view.setTypeface(Typeface.DEFAULT,Typeface.BOLD);view.setGravity(Gravity.CENTER);view.setBackground(shape(MINT,dp(14)));return view;}
    private LinearLayout card(int color){LinearLayout view=new LinearLayout(this);view.setBackground(shape(color,dp(14)));return view;}
    private GradientDrawable shape(int color,int radius){GradientDrawable drawable=new GradientDrawable();drawable.setColor(color);drawable.setCornerRadius(radius);return drawable;}
    private static void addTopGap(LinearLayout parent,View view,int top){LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=top;parent.addView(view,lp);}

    static void saveProfileFor(Context context,int id,String profile){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString("profile_"+id,profile).apply();}
    static String profileFor(Context context,int id){SharedPreferences prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE);String profile=prefs.getString("profile_"+id,null);return profile!=null?profile:prefs.getString(String.valueOf(id),"default");}
    static void setStatus(Context context,int id,String status){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString("status_"+id,status).apply();}
    static String statusFor(Context context,int id){return context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString("status_"+id,"");}
    static void clearStatus(Context context,int id){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().remove("status_"+id).apply();}
    static void setStatusForProfile(Context context,String profileId,String status){updateStatusesForProfile(context,profileId,status,false);}
    static void clearStatusForProfile(Context context,String profileId){updateStatusesForProfile(context,profileId,null,true);}
    private static void updateStatusesForProfile(Context context,String profileId,String status,boolean clear){
        AppWidgetManager manager=AppWidgetManager.getInstance(context);int[] ids=manager.getAppWidgetIds(new android.content.ComponentName(context,PokewalkerWidgetProvider.class));
        SharedPreferences.Editor editor=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit();boolean changed=false;
        for(int id:ids)if(profileId.equals(profileFor(context,id))){String key="status_"+id;if(clear)editor.remove(key);else editor.putString(key,status);changed=true;}
        if(changed)editor.apply();PokewalkerWidgetProvider.updateAll(context);
    }
    static void arm(Context context,int id,String action){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString("armed_"+id,action).putLong("armed_at_"+id,System.currentTimeMillis()).apply();}
    static boolean consumeArm(Context context,int id,String action){SharedPreferences prefs=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE);boolean armed=action.equals(prefs.getString("armed_"+id,""))&&System.currentTimeMillis()-prefs.getLong("armed_at_"+id,0)<5000;clearArm(context,id);return armed;}
    static void clearArm(Context context,int id){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().remove("armed_"+id).remove("armed_at_"+id).apply();}
    private static void clearLegacyHost(Context context,int id){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().remove("host_"+id).apply();}
    static void clearProfileFor(Context context,int id){context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().remove("profile_"+id).remove(String.valueOf(id)).remove("host_"+id).remove("status_"+id).remove("armed_"+id).remove("armed_at_"+id).apply();}
}
