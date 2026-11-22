package io.github.sdtransporter.pokewalker;

import android.app.Activity;
import android.app.AlertDialog;
import android.appwidget.AppWidgetManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.ListView;
import android.widget.TextView;
import java.util.ArrayList;

public final class WidgetConfigActivity extends Activity {
    static final String PREFS = "pokewalker_widget_profiles";
    private int widgetId = AppWidgetManager.INVALID_APPWIDGET_ID;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setResult(RESULT_CANCELED);
        Bundle extras = getIntent().getExtras();
        if (extras != null) widgetId = extras.getInt(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId);
        if (widgetId == AppWidgetManager.INVALID_APPWIDGET_ID) { finish(); return; }

        ArrayList<WalkerProfiles.Entry> entries = WalkerStore.profileEntries(this);
        ListView list = new ListView(this);
        list.setBackgroundColor(0xFF1A1A2E);
        TextView header = new TextView(this);
        header.setText("Escolha o perfil deste Pokéwalker");
        header.setTextColor(0xFFFFFFFF); header.setTextSize(16); header.setPadding(32,40,32,24);
        list.addHeaderView(header, null, false);
        ArrayList<String> names = new ArrayList<>();
        for (WalkerProfiles.Entry entry : entries) names.add(entry.name);
        list.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, names));
        list.setOnItemClickListener((AdapterView<?> parent, View view, int position, long id) -> {
            int headers = list.getHeaderViewsCount(); if (position < headers) return;
            WalkerProfiles.Entry chosen = entries.get(position - headers);
            promptHost(chosen.id);
        });
        setContentView(list);
    }

    private void promptHost(String profileId) {
        WalkerStore selected = null;
        for (WalkerStore item : WalkerStore.all(this)) if (item.profileId.equals(profileId)) selected = item;
        EditText host = new EditText(this);
        host.setSingleLine(true); host.setInputType(InputType.TYPE_CLASS_TEXT);
        host.setHint("Ex.: 192.168.1.50 ou 192.168.1.50:30820");
        String existing = hostFor(this, widgetId);
        if (existing.isEmpty() && selected != null) existing = selected.host;
        host.setText(existing);
        new AlertDialog.Builder(this)
            .setTitle("Console para enviar/receber")
            .setMessage("Esse endereço fica salvo somente para este widget. Você pode tocar na tela LCD depois para reconfigurar.")
            .setView(host)
            .setPositiveButton("Continuar", (d,w) -> {
                String value = host.getText().toString().trim();
                if (value.isEmpty()) { promptHost(profileId); return; }
                promptSkin(profileId,value);
            })
            .setNegativeButton("Cancelar", null).show();
    }

    private void promptSkin(String profileId,String hostValue) {
        String current=SkinManager.widgetSkin(this,widgetId,profileId);
        int checked=SkinManager.indexOf(current);
        new AlertDialog.Builder(this)
            .setTitle("Skin do Pokéwalker")
            .setSingleChoiceItems(SkinManager.NAMES,checked,(dialog,which)->{
                String skin=SkinManager.IDS[which];
                saveProfileFor(this,widgetId,profileId);
                saveHostFor(this,widgetId,hostValue);
                SkinManager.setWidgetSkin(this,widgetId,skin);
                clearStatus(this,widgetId);
                PokewalkerWidgetProvider.updateWidget(this,AppWidgetManager.getInstance(this),widgetId);
                try{WalkingService.ensureRunning(this);}catch(Exception ignored){}
                Intent result=new Intent();
                result.putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,widgetId);
                setResult(RESULT_OK,result);
                dialog.dismiss();finish();
            })
            .setNegativeButton("Voltar",(dialog,which)->promptHost(profileId))
            .show();
    }

    static void saveProfileFor(android.content.Context c,int id,String profile){c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString("profile_"+id,profile).apply();}
    static String profileFor(android.content.Context c,int id){SharedPreferences p=c.getSharedPreferences(PREFS,MODE_PRIVATE);String modern=p.getString("profile_"+id,null);return modern!=null?modern:p.getString(String.valueOf(id),"default");}
    static void saveHostFor(android.content.Context c,int id,String host){c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString("host_"+id,host).apply();}
    static String hostFor(android.content.Context c,int id){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getString("host_"+id,"");}
    static void setStatus(android.content.Context c,int id,String status){c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString("status_"+id,status).apply();}
    static String statusFor(android.content.Context c,int id){return c.getSharedPreferences(PREFS,MODE_PRIVATE).getString("status_"+id,"");}
    static void clearStatus(android.content.Context c,int id){c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().remove("status_"+id).apply();}
    static void arm(android.content.Context c,int id,String action){c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().putString("armed_"+id,action).putLong("armed_at_"+id,System.currentTimeMillis()).apply();}
    static boolean consumeArm(android.content.Context c,int id,String action){SharedPreferences p=c.getSharedPreferences(PREFS,MODE_PRIVATE);boolean ok=action.equals(p.getString("armed_"+id,""))&&System.currentTimeMillis()-p.getLong("armed_at_"+id,0)<5000;c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().remove("armed_"+id).remove("armed_at_"+id).apply();return ok;}
    static void clearArm(android.content.Context c,int id){c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().remove("armed_"+id).remove("armed_at_"+id).apply();}
    static void clearProfileFor(android.content.Context c,int id){c.getSharedPreferences(PREFS,MODE_PRIVATE).edit().remove("profile_"+id).remove(String.valueOf(id)).remove("host_"+id).remove("status_"+id).remove("armed_"+id).remove("armed_at_"+id).apply();}
}
