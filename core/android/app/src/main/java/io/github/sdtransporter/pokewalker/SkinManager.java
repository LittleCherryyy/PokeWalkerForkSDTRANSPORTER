package io.github.sdtransporter.pokewalker;

import android.content.Context;

/** Lightweight Pokéwalker shell skin registry shared by the app and widgets. */
final class SkinManager {
    private static final String PREFS="pokewalker_skins";
    static final String[] IDS={"poke","great","ultra","master","premier","luxury","heal","dive","dusk","quick","repeat","timer","nest","net","level","lure","moon","friend","love","heavy","fast","safari","dream","beast","cherish","sport","park"};
    static final String[] NAMES={"Poké Ball","Great Ball","Ultra Ball","Master Ball","Premier Ball","Luxury Ball","Heal Ball","Dive Ball","Dusk Ball","Quick Ball","Repeat Ball","Timer Ball","Nest Ball","Net Ball","Level Ball","Lure Ball","Moon Ball","Friend Ball","Love Ball","Heavy Ball","Fast Ball","Safari Ball","Dream Ball","Beast Ball","Cherish Ball","Sport Ball","Park Ball"};
    static final int[] RES={
        R.drawable.walker_shell_poke,
        R.drawable.walker_shell_great_polished,
        R.drawable.walker_shell_ultra,
        R.drawable.walker_shell_master,
        R.drawable.walker_shell_premier,
        R.drawable.walker_shell_luxury,
        R.drawable.walker_shell_heal,
        R.drawable.walker_shell_dive,
        R.drawable.walker_shell_dusk,
        R.drawable.walker_shell_quick,
        R.drawable.walker_shell_repeat,
        R.drawable.walker_shell_timer,
        R.drawable.walker_shell_nest,
        R.drawable.walker_shell_net,
        R.drawable.walker_shell_level,
        R.drawable.walker_shell_lure,
        R.drawable.walker_shell_moon,
        R.drawable.walker_shell_friend,
        R.drawable.walker_shell_love,
        R.drawable.walker_shell_heavy,
        R.drawable.walker_shell_fast,
        R.drawable.walker_shell_safari,
        R.drawable.walker_shell_dream,
        R.drawable.walker_shell_beast,
        R.drawable.walker_shell_cherish,
        R.drawable.walker_shell_sport,
        R.drawable.walker_shell_park
    };
    private SkinManager(){}

    static int indexOf(String id){for(int n=0;n<IDS.length;n++)if(IDS[n].equals(id))return n;return 0;}
    static int resource(String id){return RES[indexOf(id)];}
    static String name(String id){return NAMES[indexOf(id)];}

    static String profileSkin(Context c,String profileId){
        if(profileId==null||profileId.isEmpty())return "poke";
        return c.getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString("profile_"+profileId,"poke");
    }
    static void setProfileSkin(Context c,String profileId,String skin){
        if(profileId==null||profileId.isEmpty())return;
        c.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString("profile_"+profileId,IDS[indexOf(skin)]).apply();
        PokewalkerWidgetProvider.updateAll(c);
    }
    static String widgetSkin(Context c,int widgetId,String profileId){
        return profileSkin(c,profileId);
    }
    static void clearWidgetSkin(Context c,int widgetId){c.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().remove("widget_"+widgetId).apply();}
}
