"""Contract checks for HGSS prelaunch Walker rejection diagnostics.

These checks only verify source paths and messages; they do not prove
that the DSi filesystem, launcher or real-game hook works.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
PATH=ROOT/"core/bootstrap/retail/arm9/include/walker_prepare.h"

class WalkerPrelaunchChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=PATH.read_text(encoding="utf-8")

    def test_game_scoped_logging_before_device_rejections(self):
        s=self.s
        start=s.index("static void walkerPrepare(configuration *conf)")
        f=s[start:]
        # Only HGSS games should write a rejection log from this path.
        self.assertLess(f.index('strncmp(code, "IPK", 3)'),f.index("walkerSkip(conf,"))
        self.assertLess(f.index('settings.fetch(key, "VIRTUAL_WALKER", "0")'),
                        f.index('if (conf->gameOnFlashcard != conf->saveOnFlashcard)'))
        self.assertLess(f.index("if (conf->gameOnFlashcard != conf->saveOnFlashcard)"),
                        f.index("if (conf->gameOnFlashcard && dsiFeatures()"))

    def test_previous_silent_refusals_now_have_reasons(self):
        s=self.s
        self.assertIn("VIRTUAL_WALKER is not enabled for the current ROM path",s)
        self.assertIn("ROM and save are on different devices",s)
        self.assertIn("DSi NTR Walker needs ROM and save on DSi SD, not flashcart/R4",s)
        self.assertIn('walkerSkip(conf, "no save file"',s)

    def test_error_file_contains_paths_and_per_title_key(self):
        s=self.s
        self.assertIn('if (conf->ndsPath) palParkPathKey(conf->ndsPath, key);',s)
        for name in ["INI_PATH=", "INI_SECTION=", "GAME_ON_FLASHCARD=", "SAVE_ON_FLASHCARD=", "B4DS=", "WALKER_PATH="]:
            self.assertIn(name,s)
        self.assertIn("remove(WALKER_ERROR_PATH(conf));",s)
        self.assertIn("conf->walkerCluster = st.st_ino;",s)

    def test_ui_tells_user_where_to_check(self):
        igm=(ROOT/"core/bootstrap/retail/cardenginei/arm9_igm/source/inGameMenu.c").read_text()
        self.assertIn("VIRTUAL POKEWALKER V7.1.5",igm)
        self.assertIn("Check Walker error log",igm)
        self.assertIn("Wi-Fi: NOT ENABLED",igm)

if __name__ == "__main__":
    unittest.main()
