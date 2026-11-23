/* Virtual Pokéwalker: launcher-side selection. GPL-3.0-or-later.
 *
 * TWiLight Menu++'s per-game "Virtual Pokéwalker" option (HeartGold and
 * SoulSilver only) writes sd:/_nds/nds-bootstrap/pokewalker.ini:
 *
 *   [<SHA-1 of the ROM path>]
 *   VIRTUAL_WALKER = 1
 *   ROM_PATH = sd:/roms/nds/Pokemon HeartGold.nds
 *
 * Each save gets its own walker: next to "<game>.sav" is "<game>.walker",
 * the walker's 64 KiB EEPROM. A new file is created blank (all 0xFF), which
 * the game treats as a walker that has never been registered. The companion
 * app reads and writes the same file. Problems never block a launch: the
 * game simply finds no walker, and the reason is written to
 * sd:/_nds/nds-bootstrap/pokewalker-error.txt.
 */
#ifndef WALKER_PREPARE_H
#define WALKER_PREPARE_H
#include <stdio.h>
#include <string.h>
#include <string>
#include <sys/stat.h>
#include <easysave/ini.hpp>
#include "configuration.h"
#include "palpark_retail.h"
#include "nitrofs.h"
#include "walker_ds_payload.h"
#include "walker_direct_lock.h"
#include <errno.h>
#include "walker_history.h"
#include "walker_reconcile.h"

#define WALKER_INI_PATH(conf) ((conf)->gameOnFlashcard ? "fat:/_nds/nds-bootstrap/pokewalker.ini" : "sd:/_nds/nds-bootstrap/pokewalker.ini")
#define WALKER_ERROR_PATH(conf) ((conf)->gameOnFlashcard ? "fat:/_nds/nds-bootstrap/pokewalker-error.txt" : "sd:/_nds/nds-bootstrap/pokewalker-error.txt")
#define WALKER_REPAIR_PATH(conf) ((conf)->gameOnFlashcard ? "fat:/_nds/nds-bootstrap/pokewalker-repair.txt" : "sd:/_nds/nds-bootstrap/pokewalker-repair.txt")
#define WALKER_FILE_SIZE  0x10000

static void walkerSkip(configuration *conf, const char *reason, const char *path) {
	conf->walkerCluster = 0;
	FILE *log = fopen(WALKER_ERROR_PATH(conf), "w");
	if (log) {
		/* Keep diagnostics self-contained: the INI section is the SHA-1
		 * of the ROM path, not the visible ROM basename. Avoid requiring
		 * the user to share saves/ROMs or reverse-engineer the section key. */
		char key[41] = {0};
		if (conf->ndsPath) palParkPathKey(conf->ndsPath, key);
		fprintf(log, "Virtual Pokewalker not connected: %s\nWALKER_PATH=%s\nGAME=%s\n"
			"INI_PATH=%s\nINI_SECTION=%s\nSAVE=%s\n"
			"GAME_ON_FLASHCARD=%d\nSAVE_ON_FLASHCARD=%d\nB4DS=%d\n",
			reason, path ? path : "", conf->ndsPath ? conf->ndsPath : "",
			WALKER_INI_PATH(conf), key, conf->savPath ? conf->savPath : "",
			(int)conf->gameOnFlashcard, (int)conf->saveOnFlashcard, (int)conf->b4dsMode);
		fclose(log);
	}
}

/* "sd:/x/Pokemon HeartGold.sav" -> "sd:/x/Pokemon HeartGold.walker" */
static std::string walkerPathForSave(const char *savPath) {
	std::string path(savPath);
	const size_t slash = path.find_last_of('/');
	const size_t dot = path.find_last_of('.');
	if (dot != std::string::npos && (slash == std::string::npos || dot > slash)) path.erase(dot);
	return path + ".walker";
}

static void walkerPrepare(configuration *conf) {
	conf->walkerCluster = 0;
    conf->walkerPayloadOffset = conf->walkerPayloadSize = 0;
	if (!conf->ndsPath || conf->isDSiWare) return;

	/* V7.1.5: Read the ROM header first. Only log silent rejection reasons
	 * for HGSS; do not spam the Walker error file when starting other games.
	 * This remains read-only and changes no game, save or Walker data. */
	char code[4] = {0};
	FILE *rom = fopen(conf->ndsPath, "rb");
	if (rom) {
		fseek(rom, 0x0C, SEEK_SET);
		if (fread(code, 1, 3, rom) != 3) code[0] = 0;
		fclose(rom);
	}
	if (strncmp(code, "IPK", 3) && strncmp(code, "IPG", 3)) return;

	char key[41];
	palParkPathKey(conf->ndsPath, key);
	easysave::ini settings(WALKER_INI_PATH(conf));
	if (settings.fetch(key, "VIRTUAL_WALKER", "0") != "1") {
		walkerSkip(conf, "VIRTUAL_WALKER is not enabled for the current ROM path", conf->ndsPath);
		return;
	}

	/* Both files must be on the filesystem that the selected cardengine owns.
	 * Record the reason instead of silently returning with walkerCluster=0. */
	if (conf->gameOnFlashcard != conf->saveOnFlashcard) {
		walkerSkip(conf, "ROM and save are on different devices", conf->savPath);
		return;
	}
	if (conf->gameOnFlashcard && dsiFeatures() && !conf->b4dsMode) {
		walkerSkip(conf, "DSi NTR Walker needs ROM and save on DSi SD, not flashcart/R4", conf->ndsPath);
		return;
	}
	if (!conf->savPath || !conf->savPath[0]) {
		walkerSkip(conf, "no save file", NULL);
		return;
	}

	const std::string path = walkerPathForSave(conf->savPath);
	struct stat st;
	/* Any outstanding checkout blocks HGSS, including interrupted returns.
     * An inaccessible/corrupt SD directory is NOT proof that a phone lease
     * is absent. Refuse the virtual Walker instead of failing open when
     * stat() returns an error other than ENOENT. */
    errno=0;
    if(stat((path + ".lease").c_str(), &st)==0) {
        walkerSkip(conf, "walker is checked out to a phone; return or recover it", path.c_str());
        return;
    }
    if(errno!=ENOENT) {
        walkerSkip(conf, "cannot safely inspect existing phone lease on SD", path.c_str());
        return;
    }
	if (stat(path.c_str(), &st) != 0) {
		FILE *f = fopen(path.c_str(), "wb");
		if (!f) {
			walkerSkip(conf, "could not create the walker file", path.c_str());
			return;
		}
		static unsigned char blank[0x1000];
		memset(blank, 0xFF, sizeof(blank));
		bool ok = true;
		for (int i = 0; i < WALKER_FILE_SIZE / (int)sizeof(blank) && ok; i++)
			ok = fwrite(blank, 1, sizeof(blank), f) == sizeof(blank);
		fclose(f);
		if (!ok || stat(path.c_str(), &st) != 0) {
			walkerSkip(conf, "could not create the walker file", path.c_str());
			return;
		}
	}
	if (st.st_size != WALKER_FILE_SIZE) {
		walkerSkip(conf, "walker file is not 64 KiB", path.c_str());
		return;
	}

    /* NTR DSi only: preallocate one SD sector before launching the game.
     * The resident ARM7 cardengine does not support filesystem creation.
     * If the DSi lost power after attempting to send, a valid PENDING
     * fence refuses further HGSS launches without manual recovery. */
    unsigned directLockCluster=0;
    if(!conf->gameOnFlashcard && dsiFeatures() && !conf->b4dsMode) {
        const std::string fence=path+".directlock";
        struct stat lockStat;
        if(stat(fence.c_str(),&lockStat)!=0) {
            if(errno!=ENOENT) {
                walkerSkip(conf,"cannot inspect direct lock on SD",fence.c_str());
                return;
            }
            unsigned char prepared[WALKER_LOCK_SIZE];
            walkerLockPrepared(prepared);
            FILE *created=fopen(fence.c_str(),"wb");
            if(!created) {
                walkerSkip(conf,"cannot create direct lock on SD",fence.c_str());
                return;
            }
            bool wrote=fwrite(prepared,1,sizeof(prepared),created)==sizeof(prepared);
            if(fflush(created)!=0)wrote=false;
            if(fclose(created)!=0)wrote=false;
            if(!wrote || stat(fence.c_str(),&lockStat)!=0) {
                walkerSkip(conf,"direct lock allocation failed",fence.c_str());
                return;
            }
        }
        if(lockStat.st_size!=WALKER_LOCK_SIZE || !lockStat.st_ino) {
            walkerSkip(conf,"direct lock invalid size or FAT cluster",fence.c_str());
            return;
        }
        unsigned char check[WALKER_LOCK_SIZE];
        FILE *existing=fopen(fence.c_str(),"rb");
        const bool loaded=existing &&
            fread(check,1,sizeof(check),existing)==sizeof(check) &&
            fgetc(existing)==EOF && !ferror(existing);
        if(existing)fclose(existing);
        if(!loaded) {
            walkerSkip(conf,"direct lock read-back failed",fence.c_str());
            return;
        }
        const int lockStatus=walkerLockDecode(check);
        if(lockStatus<0) {
            walkerSkip(conf,"direct lock metadata damaged: recover manually",fence.c_str());
            return;
        }
        if(lockStatus==WALKER_LOCK_PENDING) {
            walkerSkip(conf,"Pokewalker may be on Android: direct checkout is locked",fence.c_str());
            return;
        }
        directLockCluster=(unsigned)lockStat.st_ino;
    }
    if (!walkerPrelaunchSnapshot(path)) {
        walkerSkip(conf,"could not preserve the pre-launch recovery snapshot",path.c_str());
        return;
    }
    /* With the untouched state preserved above, bring the walker back in line
     * with what the save says is out on a stroll (see walker_reconcile.h). */
    {
        std::string note;
        if (walkerReconcile::run(path, conf->savPath, &note) >= walkerReconcile::ENDED_STROLL) {
            FILE *log = fopen(WALKER_REPAIR_PATH(conf), "w");
            if (log) {
                fprintf(log, "The virtual Pokewalker was repaired before launch.\n%s\nWALKER_PATH=%s\nSAVE=%s\n"
                        "The walker as it was before the repair is in transfers/backups (prelaunch snapshot).\n",
                        note.c_str(), path.c_str(), conf->savPath);
                fclose(log);
            }
        }
    }
    if (conf->gameOnFlashcard) {
        struct nitroFSStruct payload;
        if (nitroFSOpen(NULL, &payload, "nitro:/walker_ds.bin", 0, 0) < 0 || payload.start < 0 ||
            payload.end - payload.start != WALKER_DS_PAYLOAD_SIZE) {
            walkerSkip(conf, "DS walker payload is missing or incomplete", path.c_str());
            return;
        }
        conf->walkerPayloadOffset = payload.start;
        conf->walkerPayloadSize = payload.end - payload.start;
    }
    /* walkerPayloadOffset is unused for DSi NTR (payloadSize == 0).
     * Pass the prepared directlock FAT cluster through this existing
     * loader slot, without altering the DS Lite payload ABI. */
    if(directLockCluster && !conf->walkerPayloadSize)
        conf->walkerPayloadOffset=directLockCluster;
	conf->walkerCluster = st.st_ino;
	remove(WALKER_ERROR_PATH(conf));
}
#endif
