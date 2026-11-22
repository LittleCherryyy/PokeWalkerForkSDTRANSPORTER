package io.github.sdtransporter.pokewalker;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.widget.RemoteViews;
import java.io.File;
import java.util.ArrayList;

/**
 * Home screen widget showing one Pokewalker profile: species/level, today's
 * steps, watts and tracking status. Each widget instance remembers its own
 * profile (chosen in WidgetConfigActivity when it's added), so you can place
 * several widgets on the home screen, each following a different Walker.
 *
 * Reads a fresh, read-only copy of that profile's saved state on every
 * refresh - it never changes which profile is "selected" in the app itself,
 * so having widgets open never disturbs what you're doing inside the app.
 */
public final class PokewalkerWidgetProvider extends AppWidgetProvider {
    static final String ACTION_REFRESH = "io.github.sdtransporter.pokewalker.WIDGET_REFRESH";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] appWidgetIds) {
        for (int id : appWidgetIds) updateWidget(context, manager, id);
    }

    @Override
    public void onDeleted(Context context, int[] appWidgetIds) {
        for (int id : appWidgetIds) WidgetConfigActivity.clearProfileFor(context, id);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (ACTION_REFRESH.equals(intent.getAction())) {
            AppWidgetManager manager = AppWidgetManager.getInstance(context);
            int[] ids = manager.getAppWidgetIds(new ComponentName(context, PokewalkerWidgetProvider.class));
            for (int id : ids) updateWidget(context, manager, id);
        }
    }

    /** Builds a read-only WalkerStore for an arbitrary profile id, without touching
     *  which profile is globally "selected" in WalkerProfiles - safe to call from a
     *  widget refresh at any time, concurrently with the app being open. */
    private static WalkerStore readOnlyStore(Context context, String profileId) {
        File filesDir = context.getApplicationContext().getFilesDir();
        File directory = profileId.equals("default") ? filesDir : new File(new File(filesDir, "profiles"), profileId);
        return new WalkerStore(directory, profileId);
    }

    static void updateWidget(Context context, AppWidgetManager manager, int widgetId) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_pokewalker);
        String profileId = WidgetConfigActivity.profileFor(context, widgetId);

        ArrayList<WalkerProfiles.Entry> entries = WalkerStore.profileEntries(context);
        String profileName = "Walker";
        boolean known = false;
        for (WalkerProfiles.Entry entry : entries) if (entry.id.equals(profileId)) { profileName = entry.name; known = true; }

        if (!known) {
            // The profile this widget was pointed at no longer exists (deleted
            // in the app). Prompt the user to pick a profile again instead of
            // silently showing stale or wrong data.
            views.setTextViewText(R.id.widget_profile, "Not configured");
            views.setTextViewText(R.id.widget_main, "Tap to choose a profile");
            views.setTextViewText(R.id.widget_steps, "?");
            views.setTextViewText(R.id.widget_sub, "profile removed");
            Intent reconfigure = new Intent(context, WidgetConfigActivity.class);
            reconfigure.putExtra(AppWidgetManager.EXTRA_APPWIDGET_ID, widgetId);
            PendingIntent reconfigureIntent = PendingIntent.getActivity(context, widgetId, reconfigure,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
            views.setOnClickPendingIntent(R.id.widget_root, reconfigureIntent);
            views.setOnClickPendingIntent(R.id.widget_refresh, reconfigureIntent);
            manager.updateAppWidget(widgetId, views);
            return;
        }

        views.setTextViewText(R.id.widget_profile, profileName);

        synchronized (WalkerStore.LOCK) {
            WalkerStore state = readOnlyStore(context, profileId);

            if (!state.active()) {
                views.setTextViewText(R.id.widget_main, "No partner");
                views.setTextViewText(R.id.widget_steps, "---");
                views.setTextViewText(R.id.widget_sub, "send from HGSS");
            } else if (!state.error.isEmpty()) {
                views.setTextViewText(R.id.widget_main, "paused");
                views.setTextViewText(R.id.widget_steps, "---");
                views.setTextViewText(R.id.widget_sub, "tap to open app");
            } else {
                long[] info = Native.info(state.data);
                String partner = info[Native.HAS_POKEMON] != 0
                        ? Native.species((int) info[Native.SPECIES]) + " · Lv " + info[Native.LEVEL]
                        : "No partner";
                views.setTextViewText(R.id.widget_main, partner);
                views.setTextViewText(R.id.widget_steps, String.valueOf(info[Native.TODAY]));
                views.setTextViewText(R.id.widget_sub,
                        info[Native.WATTS] + " watts" + (state.tracking() ? "" : " · paused"));
            }
        }

        PendingIntent open = PendingIntent.getActivity(context, widgetId,
                new Intent(context, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        views.setOnClickPendingIntent(R.id.widget_root, open);

        PendingIntent refresh = PendingIntent.getBroadcast(context, widgetId,
                new Intent(context, PokewalkerWidgetProvider.class).setAction(ACTION_REFRESH),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        views.setOnClickPendingIntent(R.id.widget_refresh, refresh);

        manager.updateAppWidget(widgetId, views);
    }
}
