package io.github.sdtransporter.pokewalker;

import android.app.Application;

public final class PokewalkerApp extends Application {
    @Override public void onCreate() {
        super.onCreate();
        Diagnostics.install(this);
        Diagnostics.event(this, "APP", "Process started");
    }
}
