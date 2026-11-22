package io.github.sdtransporter.pokewalker;

import android.app.Activity;
import android.appwidget.AppWidgetManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.TextView;
import java.util.ArrayList;

/**
 * Shown once when a Pokewalker widget is dropped on the home screen (and
 * again if the saved profile was later deleted). Lets the user pick which
 * profile THIS widget instance should display; the choice is stored keyed
 * by widgetId, so two widgets can each follow a different Walker.
 */
public final class WidgetConfigActivity extends Activity {
    static final String PREFS = "pokewalker_widget_profiles";

    private int widgetId = AppWidgetManager.INVALID_APPWIDGET_ID;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Cancel by default: if the user backs out without picking a
        // profile, the host must not add a half-configured widget.
        setResult(RESULT_CANCELED);

        Bundle extras = getIntent().getExtras();
        if (extras != null) widgetId = extras.getInt(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId);
        if (widgetId == AppWidgetManager.INVALID_APPWIDGET_ID) { finish(); return; }

        ArrayList<WalkerProfiles.Entry> entries = WalkerStore.profileEntries(this);

        ListView list = new ListView(this);
        list.setBackgroundColor(0xFF1A1A2E);

        TextView header = new TextView(this);
        header.setText("Choose the Walker profile for this widget");
        header.setTextColor(0xFFFFFFFF);
        header.setTextSize(16);
        header.setPadding(32, 40, 32, 24);
        list.addHeaderView(header, null, false);

        ArrayList<String> names = new ArrayList<>();
        for (WalkerProfiles.Entry entry : entries) names.add(entry.name);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, names);
        list.setAdapter(adapter);

        list.setOnItemClickListener((AdapterView<?> parent, View view, int position, long id) -> {
            int headers = list.getHeaderViewsCount();
            if (position < headers) return;
            WalkerProfiles.Entry chosen = entries.get(position - headers);
            saveProfileFor(this, widgetId, chosen.id);

            PokewalkerWidgetProvider.updateWidget(this, AppWidgetManager.getInstance(this), widgetId);

            Intent result = new Intent();
            result.putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId);
            setResult(RESULT_OK, result);
            finish();
        });

        setContentView(list);
    }

    static void saveProfileFor(android.content.Context context, int widgetId, String profileId) {
        SharedPreferences.Editor editor = context.getSharedPreferences(PREFS, MODE_PRIVATE).edit();
        editor.putString(String.valueOf(widgetId), profileId);
        editor.apply();
    }

    static String profileFor(android.content.Context context, int widgetId) {
        return context.getSharedPreferences(PREFS, MODE_PRIVATE).getString(String.valueOf(widgetId), "default");
    }

    static void clearProfileFor(android.content.Context context, int widgetId) {
        context.getSharedPreferences(PREFS, MODE_PRIVATE).edit().remove(String.valueOf(widgetId)).apply();
    }
}
