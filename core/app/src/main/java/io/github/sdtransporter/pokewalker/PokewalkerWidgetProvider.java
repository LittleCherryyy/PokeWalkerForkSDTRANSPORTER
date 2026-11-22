package io.github.sdtransporter.pokewalker;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.widget.RemoteViews;

/**
 * Home screen widget showing the currently selected Pokewalker profile:
 * species/level, today's steps, watts and tracking status. Tapping the
 * widget opens MainActivity; tapping the refresh icon re-reads the saved
 * state (useful right after the background WalkingService credits steps).
 *
 * Reuses the app's own WalkerStore/Native code, so it reflects whatever
 * profile is currently selected in WalkerProfiles - no separate storage.
 */
public final class PokewalkerWidgetProvider extends AppWidgetProvider {
    static final String ACTION_REFRESH = "io.github.sdtransporter.pokewalker.WIDGET_REFRESH";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] appWidgetIds) {
        for (int id : appWidgetIds) updateWidget(context, manager, id);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (ACTION_REFRESH.equals(intent.getAction())) {
            AppWidgetManager manager = AppWidgetManager.getInstance(context);
            int[] ids = manager.getAppWidgetIds(new android.content.ComponentName(context, PokewalkerWidgetProvider.class));
            for (int id : ids) updateWidget(context, manager, id);
        }
    }

    static void updateWidget(Context context, AppWidgetManager manager, int widgetId) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_pokewalker);

        synchronized (WalkerStore.LOCK) {
            WalkerStore state = WalkerStore.get(context);
            String profileName = WalkerStore.profileName(context);
            views.setTextViewText(R.id.widget_profile, profileName);

            if (!state.active()) {
                views.setTextViewText(R.id.widget_main, "No walker linked");
                views.setTextViewText(R.id.widget_sub, "Send a Pokémon from HGSS to begin");
            } else if (!state.error.isEmpty()) {
                views.setTextViewText(R.id.widget_main, "Tracking paused");
                views.setTextViewText(R.id.widget_sub, state.error);
            } else {
                long[] info = Native.info(state.data);
                String partner = info[Native.HAS_POKEMON] != 0
                        ? Native.species((int) info[Native.SPECIES]) + " · Lv " + info[Native.LEVEL]
                        : "No partner";
                views.setTextViewText(R.id.widget_main, partner);
                views.setTextViewText(R.id.widget_sub,
                        info[Native.TODAY] + " steps today · " + info[Native.WATTS] + " watts"
                                + (state.tracking() ? "" : " · paused"));
            }
        }

        PendingIntent open = PendingIntent.getActivity(context, 0,
                new Intent(context, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        views.setOnClickPendingIntent(R.id.widget_root, open);

        PendingIntent refresh = PendingIntent.getBroadcast(context, 0,
                new Intent(context, PokewalkerWidgetProvider.class).setAction(ACTION_REFRESH),
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        views.setOnClickPendingIntent(R.id.widget_refresh, refresh);

        manager.updateAppWidget(widgetId, views);
    }
}
