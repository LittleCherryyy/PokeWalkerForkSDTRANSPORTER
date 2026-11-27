/* Native DS interface, designed for 256x192 screens. GPL-3.0-or-later. */
#include "ui.h"
#include "nds_ui.h"
#include "species.h"
#include "../../shared/walkerclassic.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define RGB(r, g, b)                                                           \
  (0x8000 | ((r) >> 3) | (((g) >> 3) << 5) | (((b) >> 3) << 10))
static const uint16_t BG = RGB(12, 24, 32), PANEL = RGB(24, 45, 53),
                      INK = RGB(242, 250, 242), MUTED = RGB(175, 198, 191),
                      TEAL = RGB(84, 232, 188), GOLD = RGB(255, 213, 112),
                      RED = RGB(255, 154, 154), LCD = RGB(198, 219, 168),
                      RED_SHELL = RGB(221, 53, 62), WHITE = RGB(250, 250, 240),
                      BLACK = RGB(9, 15, 19), GREEN = RGB(115, 220, 150);
static UIState cached[2];
static int valid[2];
static void text(int x, int y, uint16_t color, const char *s, int columns) {
  ndsUiText(x, y, 1, color, s, columns);
}
static void fmt(int x, int y, uint16_t color, int columns, const char *format,
                ...) {
  char buffer[256];
  va_list args;
  va_start(args, format);
  vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);
  text(x, y, color, buffer, columns);
}
static void plain(char *out, const char *in, unsigned size) {
  unsigned n = 0;
  while (*in && n + 1 < size) {
    unsigned char c = *in++;
    if (c < 128)
      out[n++] = c;
    else if (c == 0xc3 && *in) {
      unsigned char d = *in++;
      out[n++] = (d == 0xa9 ? 'e' : d == 0x89 ? 'E' : '?');
    } else {
      while (((unsigned char)*in & 0xc0) == 0x80)
        in++;
      out[n++] = '.';
    }
  }
  out[n] = 0;
}
static void wrap(int x, int y, uint16_t color, const char *value, int columns,
                 int lines) {
  char buffer[512];
  plain(buffer, value, sizeof(buffer));
  const char *p = buffer;
  for (int row = 0; row < lines && *p; row++) {
    while (*p == ' ' || *p == '\n')
      p++;
    unsigned n = 0, space = 0;
    while (p[n] && p[n] != '\n' && n < (unsigned)columns) {
      if (p[n] == ' ')
        space = n;
      n++;
    }
    if (p[n] && p[n] != '\n' && space)
      n = space;
    char line[40];
    memcpy(line, p, n);
    line[n] = 0;
    if (row == lines - 1 && p[n] && n >= 3)
      memcpy(line + n - 3, "...", 3);
    text(x, y + row * 11, color, line, columns);
    p += n;
  }
}
static void panel(int x, int y, int w, int h, int selected) {
  ndsUiRect(x, y + 2, w, h, BLACK);
  ndsUiRect(x, y, w, h, selected ? TEAL : RGB(53, 79, 84));
  ndsUiRect(x + 1, y + 1, w - 2, h - 2,
            selected ? RGB(28, 73, 67) : PANEL);
  if (selected)
    ndsUiRect(x + 3, y + 3, 2, h - 6, GOLD);
}
/* A compact Pokéwalker mark: red cap, white base, black seam and LCD. */
static void deviceIcon(int x, int y, int size) {
  int radius = size / 2 - 1, center = size / 2;
  for (int row = 0; row < size; row++) {
    int dy = row - center, half = radius;
    while (half > 0 && half * half + dy * dy > radius * radius)
      half--;
    if (half <= 0)
      continue;
    ndsUiRect(x + center - half, y + row, half * 2 + 1, 1, BLACK);
    int inner = half - (size >= 24 ? 2 : 1);
    if (inner <= 0)
      continue;
    uint16_t shell = row < center ? RED_SHELL : WHITE;
    ndsUiRect(x + center - inner, y + row, inner * 2 + 1, 1, shell);
  }
  ndsUiRect(x + 4, y + center, size - 8, 1, BLACK);
  int lcdW = size * 11 / 20, lcdH = size * 7 / 20;
  if (lcdW < 6)
    lcdW = 6;
  if (lcdH < 4)
    lcdH = 4;
  int lcdX = x + (size - lcdW) / 2;
  int lcdY = y + (size - lcdH) / 2 - (size >= 24 ? 1 : 0);
  ndsUiRect(lcdX - 1, lcdY - 1, lcdW + 2, lcdH + 2, BLACK);
  ndsUiRect(lcdX, lcdY, lcdW, lcdH, LCD);
  ndsUiRect(lcdX + 2, lcdY + lcdH - 2, lcdW - 4, 1, RGB(88, 121, 89));
  ndsUiRect(x + center - 1, y + size - 4, 3, 2, BLACK);
  ndsUiRect(x + center, y + size - 4, 1, 1, TEAL);
}
static void badge(int x, int y, const char *label, uint16_t color,
                  int columns) {
  int width = columns * 8 + 8;
  ndsUiRect(x, y, width, 12, color);
  ndsUiRect(x + 1, y + 1, width - 2, 10, BG);
  text(x + 4, y + 2, color, label, columns);
}
static void header(const char *title) {
  ndsUiRect(0, 0, 256, 30, RGB(16, 32, 40));
  deviceIcon(7, 3, 22);
  ndsUiText(36, 9, 1, INK, title, 26);
  ndsUiRect(8, 28, 240, 1, TEAL);
  ndsUiRect(8, 29, 64, 1, GOLD);
}
static void footer(const char *hint) {
  ndsUiRect(0, 176, 256, 16, RGB(16, 32, 40));
  ndsUiRect(0, 176, 256, 1, RGB(53, 79, 84));
  text(8, 180, INK, hint, 30);
}
static void bar(int x, int y, int w, int h, float progress, uint16_t color) {
  if (progress < 0)
    progress = 0;
  if (progress > 1)
    progress = 1;
  ndsUiRect(x, y, w, h, PANEL);
  ndsUiRect(x + 1, y + 1, (int)((w - 2) * progress), h - 2, color);
}
static int has(const char *value, const char *needle) {
  return value && needle && strstr(value, needle) != NULL;
}
static int transferProgress(const char *status, unsigned long *current,
                           unsigned long *total) {
  const char *p = strstr(status, "Sending Pokemon: ");
  if (!p)
    p = strstr(status, "Sending Pok\xc3\xa9mon: ");
  if (!p)
    p = strstr(status, "Receiving return: ");
  if (!p)
    return 0;
  p = strchr(p, ':');
  if (!p)
    return 0;
  char *end = NULL;
  unsigned long sent = strtoul(p + 1, &end, 10);
  if (!end || *end != ' ')
    return 0;
  while (*end == ' ')
    end++;
  if (*end != '/')
    return 0;
  unsigned long expected = strtoul(end + 1, &end, 10);
  if (!expected || end == p + 1)
    return 0;
  *current = sent;
  *total = expected;
  return 1;
}
static void portrait(const uint8_t *ee, unsigned offset, int w, int h, int x,
                     int y, int scale) {
  if (!ee || offset + (unsigned)(w * h / 4) > WALKER_FILE_SIZE)
    return;
  const uint16_t shades[] = {LCD, RGB(153, 180, 132), RGB(92, 126, 91),
                             RGB(43, 69, 57)};
  int flip=w==32 && h==24 && offset>=0x91be && offset<0x933e && !(ee[WALKER_ROUTE+14]&1);
  for (int py = 0; py < h; py++)
    for (int px = 0; px < w; px++) {
      unsigned pos = offset + ((py / 8) * w + px) * 2, bit = py & 7;
      unsigned c = ((ee[pos] >> bit) & 1) * 2 + ((ee[pos + 1] >> bit) & 1);
      if (c)
        ndsUiRect(x + (flip?w-1-px:px) * scale, y + py * scale, scale, scale, shades[c]);
    }
}
int uiInit(void) {
  memset(valid, 0, sizeof(valid));
  return ndsUiInit();
}
void uiExit(void) {}
void uiBegin(int bottom) { (void)bottom; }
void uiEnd(void) { ndsUiEnd(); }
void uiNotify(UIState *s, const char *value, uint64_t now) {
  snprintf(s->toast, sizeof(s->toast), "%s", value);
  s->toastScreen = s->screen;
  s->toastUntil = now + 5000;
}
void uiUpdateClock(UIState *s, uint64_t now) {
  s->clockMs = now;
  if (now >= s->toastUntil || s->screen != s->toastScreen) {
    s->toast[0] = 0;
    s->toastUntil = 0;
  }
}
void uiTop(const UIState *s) {
  UIState key = {0};
  key.info = s->info;
  key.loaded = s->loaded;
  key.pending = s->pending;
  key.walkingEnabled = s->walkingEnabled;
  key.secondsPerStep = s->secondsPerStep;
  key.phoneLocked = s->phoneLocked;
  key.frame = (s->frame / 24) & 1;
  key.battle = s->battle;
  key.screen = s->screen == UI_BATTLE || s->screen == UI_LIST ? s->screen : 0;
  snprintf(key.filename, sizeof(key.filename), "%s", s->filename);
  if (valid[0] && !memcmp(&key, &cached[0], sizeof(key)))
    return;
  cached[0] = key;
  valid[0] = 1;
  ndsUiBegin(0, BG);
  deviceIcon(7, 2, 22);
  ndsUiText(36, 8, 1, TEAL, "POKEWALKER", 24);
  text(36, 19, MUTED, "SD TRANSPORTER", 20);
  if(s->screen==UI_LIST && s->loaded) {
    ndsUiRect(8, 30, 240, 1, TEAL);
    wrap(8, 38, INK, s->filename, 29, 2);
    text(8,65,TEAL,"TRAINER",30);
    text(8,75,INK,s->info.registered&&s->info.trainer[0]?s->info.trainer:"Unavailable",30);
    if(s->info.registered)fmt(8,100,GOLD,30,"Trainer ID: %05lu",(unsigned long)s->info.trainerId);
    else text(8,100,GOLD,"Trainer ID unavailable",30);
    text(8,129,INK,s->info.hasPokemon?speciesName(s->info.species):"No companion",30);
    return;
  }
  if (!s->loaded || !s->info.hasPokemon) {
    ndsUiRect(60, 38, 136, 99, PANEL);
    deviceIcon(116, 45, 32);
    text(88, 85, GOLD, "NO PARTNER", 13);
    if (s->loaded && s->info.registered) {
      fmt(8, 112, TEAL, 30, "%lu steps  %u watts", (unsigned long)(s->info.strollSteps+s->pending),s->info.watts);
    }
    wrap(16, 149, INK,
         s->phoneLocked ? "Walker is checked out to a phone."
                        : s->loaded && s->info.registered ? "No partner. Send a Pokémon from HGSS." : "Choose an active walker below.",
         28, 2);
    return;
  }
  fmt(8, 20, INK, 30, "%s  Lv %u", speciesName(s->info.species), s->info.level);
  if (s->screen == UI_BATTLE) {
    ndsUiRect(40, 37, 176, 75, LCD);
    portrait(s->ee, 0x91be + key.frame * 192, 32, 24, 46, 49, 2);
    portrait(s->ee, 0x9a7e + s->battle.encounter * 384 + key.frame * 192, 32,
             24, 144, 49, 2);
    fmt(8, 123, INK, 30, "Partner HP %d/4", s->battle.playerHp);
    fmt(8, 138, GOLD, 30, "Wild HP    %d/4", s->battle.enemyHp);
    text(8, 158, MUTED,
         speciesName(walkerRoutePokemonId(s->ee, s->battle.encounter)), 30);
  } else {
    /* Integer 2x scale preserves every pixel of the original walker portrait.
     */
    ndsUiRect(60, 34, 136, 100, PANEL);
    ndsUiRect(64, 36, 128, 96, LCD);
    portrait(s->ee, 0x933e + key.frame * 768, 64, 48, 64, 36, 2);
    bar(8, 135, 240, 3, (s->info.stepsThisWatt + s->pending) % 20 / 20.f, TEAL);
    text(8, 140, MUTED, "STROLL STEPS", 16);
    text(176, 140, MUTED, "WATTS", 9);
    char value[32];
    snprintf(value, sizeof(value), "%lu",
             (unsigned long)(s->info.strollSteps + s->pending));
    ndsUiText(8, 151, 2, INK, value, 9);
    snprintf(value, sizeof(value), "%u", s->info.watts);
    ndsUiText(176, 151, 2, GOLD, value, 4);
  }
  fmt(8, 171, TEAL, 30, "Today %lu  %s",
      (unsigned long)(s->info.todaySteps + s->pending),
      s->walkingEnabled ? "Walking" : "Paused");
  text(8, 183, MUTED, s->info.route[0] ? s->info.route : "Your next adventure",
       30);
}
void uiBottom(const UIState *s) {
  UIState key = *s;
  key.frame = s->screen == UI_SCAN ? s->frame / 8 : 0;
  key.clockMs = key.toastUntil = 0;
  key.now = 0;
  key.progress = (int)(s->progress * 100) / 100.f;
  if (valid[1] && !memcmp(&key, &cached[1], sizeof(key)))
    return;
  cached[1] = key;
  valid[1] = 1;
  ndsUiBegin(1, BG);
  if (s->saving) {
    header("Saving...");
    wrap(8, 42, INK, s->saveStage, 30, 3);
    wrap(8, 90, GOLD, "Please wait. Keep the console on until saving finishes.", 30, 4);
    footer("Controls locked while saving");
    return;
  }
  if (s->saveError) {
    header(s->discardPrompt ? "Discard changes" : "Save failed");
    if (s->discardPrompt) {
      wrap(8, 40, INK,
           "Discard unsaved changes and reload the file on the card?", 30, 4);
      wrap(8, 105, GOLD, "Progress still in memory will be lost.", 30, 3);
      footer("A Discard   B Keep");
    } else {
      wrap(8, 38, RED, s->saveStage, 30, 2);
      wrap(8, 66, INK, s->saveReason, 30, 7);
      panel(8, 150, 116, 23, s->saveChoice == 0);
      panel(132, 150, 116, 23, s->saveChoice == 1);
      text(16, 158, INK, "Retry save", 12);
      text(140, 158, INK, "Discard...", 12);
      footer("D-pad A Select Y Retry");
    }
    return;
  }
  if (s->screen == UI_CLASSIC && s->classicPixels) {
    ndsUiWalkerShell(s->classicPixels, s->classicContrast);
    return;
  }
  if (s->screen == UI_FOLDER_PICKER) {
    header("Choose search folder");
    wrap(8, 36, TEAL, s->folderPath, 30, 2);
    if (!s->folderCount)
      text(8, 63, INK, "No subfolders", 30);
    int first = s->folderCursor / 6 * 6;
    for (int row = 0; row < 6 && first + row < s->folderCount; row++) {
      int index = first + row, y = 58 + row * 17;
      panel(8, y, 240, 15, index == s->folderCursor);
      text(14, y + 4, INK, strrchr(s->folderPaths[index], '/') + 1, 27);
    }
    text(8, 163, s->folderLimited ? GOLD : MUTED,
         s->folderLimited ? "Folder list limit reached" : "Y Scan /roms  X Cancel", 30);
    footer("B Up  START Scan here");
    return;
  }
  if (s->screen == UI_SCAN) {
    header(s->validation ? "Checking files" : "Finding walkers");
    deviceIcon(16, 41, 40);
    wrap(66, 42, INK,
         s->validation ? "Reading your walker files."
                       : s->scanRoot,
         22, 3);
    float progress = s->validation ? s->progress : (s->frame % 120) / 119.f;
    bar(8, 94, 240, 12, progress, TEAL);
    fmt(8, 116, INK, 30, "%d folders  %d files", s->dirs, s->files);
    fmt(8, 135, TEAL, 30, "%d walkers found", s->count);
    if (s->validation)
      fmt(8, 155, MUTED, 30, "Checked %d of %d", s->done, s->total);
    footer("X Folders  START Cancel");
    return;
  }
  if (s->screen == UI_LIST) {
    header("Your walkers");
    if (!s->count) {
      panel(8, 38, 240, 106, 0);
      deviceIcon(108, 48, 40);
      text(69, 95, INK, "No walker files yet", 19);
      wrap(25, 113, MUTED,
           "Press X to choose a folder and search your SD card.", 25, 2);
    }
    for (int row = 0; row < 7 && s->page + row < s->count; row++) {
      int i = s->page + row, y = 35 + row * 19;
      panel(8, y, 240, 17, i == s->cursor);
      const char *p = strrchr(s->paths[i], '/');
      p = p ? p + 1 : s->paths[i];
      char name[512];
      snprintf(name, sizeof(name), "%s", p);
      char *ext = strrchr(name, '.');
      if (ext)
        *ext = 0;
      text(14, y + 5, INK, name, 20);
      if (s->statuses && s->statuses[i] == 1)
        badge(184, y + 2, "READY", TEAL, 5);
      else if (s->statuses && s->statuses[i] == 3)
        badge(184, y + 2, "PHONE", GOLD, 5);
      else if (s->statuses && s->statuses[i] == 2)
        badge(184, y + 2, "SETUP", GOLD, 5);
      else
        badge(184, y + 2, "CHECK", GOLD, 5);
    }
    if (s->scanLimited)
      text(8, 169, GOLD, "Search limit reached", 30);
    footer("X Folder  SEL Backups");
    return;
  }
  if(s->screen==UI_COURSE_CONFIRM){
    header("Special courses");
    panel(8, 37, 240, 70, 0);
    badge(16, 45, "OPTIONAL HGSS DATA", GOLD, 17);
    wrap(16, 65, INK,
         "Enable event routes for this save language. Existing watt unlocks stay unchanged.",
         27, 3);
    panel(8, 116, 240, 42, 0);
    text(16, 123, TEAL, "SAVE PROTECTION", 18);
    wrap(16, 139, MUTED,
         "A verified backup is created before the game save is edited.",
         27, 2);
    footer("A Activate   B Cancel");return;
  }
  if(s->screen==UI_PHONE_TARGET || s->screen==UI_PHONE_RECEIVE_CONFIRM){
    header(s->screen==UI_PHONE_TARGET?"Return destination":"Receive phone copy?");
    if(s->screen==UI_PHONE_TARGET){
      text(8, 33, MUTED, "Choose the original walker file", 28);
      for(int row=0;row<6;row++){int n=(s->phoneCursor/6)*6+row;if(n>=s->phoneCount)break;
        const char *name=strrchr(s->phonePaths[n],'/');panel(8,46+row*20,240,18,n==s->phoneCursor);text(14,52+row*20,INK,name?name+1:s->phonePaths[n],28);
      }
      footer("A Phone X Courses B Cancel");
    }else{
      panel(8, 36, 240, 80, 0);
      badge(16, 44, "RECEIVE RECOVERY COPY", GOLD, 21);
      wrap(16, 65, INK,
           "Only use this if the console walker is missing. The current phone copy will be written to the game's saves folder.",
           27, 4);
      panel(8, 123, 240, 36, 0);
      wrap(16, 130, RED, "An existing active walker is never overwritten.",
           28, 2);
      footer("A Receive copy   B Cancel");
    }return;
  }
  if(s->screen==UI_REWARD_SETTINGS) {
    header("Dowsing rewards");
    panel(8, 36, 240, 93, 0);
    text(16, 44, INK, "OPTIONAL ITEM TABLE", 22);
    text(16, 62, MUTED, "Master Ball      0.01%", 27);
    text(16, 77, MUTED, "PP Max / PP Up   0.29%", 27);
    text(16, 92, MUTED, "TM01-92          1.70%", 27);
    wrap(16, 108, INK, "Remaining 98% keeps the original course rewards.", 27, 2);
    panel(8, 137, 240, 25, 0);
    badge(16, 143, s->expandedItems ? "ENABLED" : "DISABLED",
          s->expandedItems ? GREEN : MUTED, 8);
    footer("A Opt in X Disable B Back");return;
  }
  if(s->screen==UI_RESTORE_BACKUP) {
    header("Restore selected backup?");
    panel(8, 37, 240, 76, 0);
    badge(16, 45, "RECOVERY SOURCE", GOLD, 15);
    wrap(16, 65, INK, s->backupName, 27, 3);
    panel(8, 120, 240, 42, 0);
    wrap(16, 127, RED,
         "Restore revokes phone ownership. Receiving a matching phone copy may duplicate a Pokemon.",
         27, 3);
    footer("A Restore   X Phone copy   B Cancel");return;
  }
  if(s->screen==UI_RECOVER_SAVE) {
    header("Recover interrupted save?");
    panel(8, 36, 240, 44, 0);
    badge(16, 43, "SAVE RECOVERY", GOLD, 13);
    wrap(16, 61, INK, "Final walker copy is missing. Choose a verified recovery file.", 27, 2);
    panel(8, 88, 240, 37, 0);
    wrap(16, 97, GOLD, s->backupName, 27, 2);
    panel(8, 132, 240, 31, 0);
    wrap(16, 139, MUTED, s->backupDetail, 27, 2);
    footer("L/R File A Recover B Cancel");return;
  }
  if(s->screen==UI_BACKUPS || s->screen==UI_BACKUP_DELETE || s->screen==UI_DELETE_ACTIVE) {
    int active=s->screen==UI_DELETE_ACTIVE,confirm=s->screen!=UI_BACKUPS;
    header(active?"Delete active walker?":confirm?"Delete recovery copy?":"Recovery copies");
    if(confirm) {
      panel(8, 38, 240, 69, 0);
      badge(16, 46, active ? "ACTIVE WALKER" : "RECOVERY SNAPSHOT", RED,
            active ? 13 : 18);
      wrap(16, 66, INK, active?"A recovery copy is kept first. A walker on the phone keeps its return permission.":"Only this snapshot is removed. Active data and ownership records stay.",27,4);
      panel(8, 116, 240, 39, 0);
      wrap(16, 124, GOLD, active?s->backupWalker:s->backupName, 27, 3);
      footer("A Delete   B Keep");
    } else {
      panel(8, 34, 240, 58, 0);
      fmt(16, 41, TEAL, 28, "%d / %d recovery copies%s",s->backupCount?s->backupIndex+1:0,s->backupCount,s->backupLimited?" (first 128)":"");
      wrap(16, 59, INK, s->backupCount?s->backupName:"No recovery snapshots yet.",28,2);
      wrap(16, 77, MUTED, s->backupDetail,28,1);
      text(8, 101, TEAL,"START Restore   SELECT Missing",30);
        panel(8,112,240,22,0);text(16,119,INK,"A Delete selected backup",28);
      panel(8,139,240,22,0);text(16,146,GOLD,"X Delete active walker",28);
      footer("L/R Copy Y Walker B Back");
    }
    return;
  }
  if (s->screen == UI_SYNC) {
    const char *status = s->syncStatus;
    int failed = has(status, "failed") || has(status, "Failed") ||
                 has(status, "No phone accepted") || has(status, "unavailable") ||
                 has(status, "could not") || has(status, "Could not") ||
                 has(status, "did not") || has(status, "invalid") ||
                 has(status, "Phone error") || has(status, "rejected") ||
                 has(status, "interrupted") || has(status, "timed out") ||
                 has(status, "Timed out") || has(status, "disconnected") ||
                 has(status, "closed the connection") ||
                 has(status, "No saved Wi-Fi") || has(status, "Wi-Fi stopped");
    int waitingApproval = has(status, "Connect to Console approval") ||
                          has(status, "approval in Connect to Console");
    int accepted = has(status, "accepted TCP") ||
                   has(status, "App approved") ||
                   has(status, "Sending Pokemon:") ||
                   has(status, "Sending Pok\xc3\xa9mon:") ||
                   has(status, "Receiving return:") ||
                   has(status, "Walker sent") || has(status, "Pok\xc3\xa9mon saved") ||
                   has(status, "Pok\xc3\xa9mon returned") ||
                   has(status, "received and saved");
    int waitingApp = has(status, "Waiting for app receiver") || waitingApproval;
    int complete = has(status, "received and saved") ||
                   has(status, "Pok\xc3\xa9mon returned");
    int returning = s->phoneLocked || has(status, "Requesting") ||
                    has(status, "Receiving return") ||
                    has(status, "Pok\xc3\xa9mon returned");
    unsigned long current = 0, total = 0;
    int transferring = transferProgress(status, &current, &total);
    header(returning ? "Return to HGSS" : "Send to phone");
    panel(8, 34, 240, 30, 0);
    text(16, 40, MUTED, "PHONE HOTSPOT", 16);
    fmt(136, 40, TEAL, 14, "%s", s->syncAddress[0] ? s->syncAddress : "TCP 30821");
    if (waitingApp) {
      badge(16, 48, "WAITING FOR APPROVAL", GOLD, 20);
    } else if (failed) {
      badge(16, 48, "RETRY NEEDED", RED, 12);
    } else if (complete) {
      badge(16, 48, "TRANSFER CONFIRMED", GREEN, 18);
    } else if (accepted) {
      badge(16, 48, "TCP CONNECTED", TEAL, 13);
    } else {
      badge(16, 48, "CONNECTING", GOLD, 10);
    }
    panel(8, 70, 240, 56, 0);
    uint16_t connectColor = failed ? RED : accepted ? GREEN : GOLD;
    uint16_t dataColor = failed ? RED : transferring || has(status, "Requesting") ||
                                 has(status, "Walker sent") ||
                                 has(status, "Pok\xc3\xa9mon saved") || complete
                             ? TEAL : MUTED;
    uint16_t verifyColor = failed ? RED : complete ? GREEN :
                               waitingApproval || has(status, "Waiting for the app") ||
                                       has(status, "Confirming with phone")
                                   ? GOLD : MUTED;
    badge(16, 77, "1", connectColor, 1);
    text(36, 79, INK, "Connect", 7);
    badge(96, 77, "2", dataColor, 1);
    text(116, 79, INK, returning ? "Receive" : "Send", 7);
    badge(176, 77, "3", verifyColor, 1);
    text(196, 79, INK, "Verify", 7);
    if (transferring && total) {
      float progress = current >= total ? 1.f : (float)current / (float)total;
      bar(18, 102, 220, 8, progress, TEAL);
      fmt(18, 113, MUTED, 27, "%lu / %lu bytes",
          current, total);
    } else {
      wrap(18, 99, failed ? RED : INK, status, 27, 2);
    }
    panel(8, 132, 240, 34, 0);
    if (complete)
      wrap(16, 139, GREEN,
           returning ? "Phone confirmed. Verified SD copy is active."
                     : "Android confirmed and saved this Pokemon.", 28, 2);
    else if (waitingApp)
      wrap(16, 139, GOLD, "Arm the same direction in app Connect to Console.", 28, 2);
    else if (has(status, "Waiting for the app"))
      wrap(16, 139, GOLD, "Payload sent. Waiting for the app to verify and save it.", 28, 2);
    else if (has(status, "Confirming with phone"))
      wrap(16, 139, GOLD, "SD staging is verified. Waiting for the phone's final ACK.", 28, 2);
    else if (failed)
      wrap(16, 139, RED, "No success is reported. Retry after checking the receiver.", 28, 2);
    else
      wrap(16, 139, MUTED, "Keep Connect to Console armed on the same hotspot.", 28, 2);
    footer(s->phoneLocked ? "A Retry Y Return X Recover B Back" : "A Retry B Back START Exit");
    return;
  }
  if (s->screen == UI_LOCKED || s->screen == UI_FORCE) {
    int force = s->screen == UI_FORCE;
    header(force ? "Force unlock?" : "On phone");
    panel(8, 36, 240, 110, 0);
    deviceIcon(18, 48, 36);
    badge(66, 43, force ? "OWNERSHIP RESET" : "PHONE OWNS WALKER",
          force ? RED : GOLD, force ? 15 : 16);
    wrap(
        66, 64, INK,
        force
            ? "Restore the console snapshot? Recovery copies are kept. "
              "The old phone session cannot sync back until a fresh handoff."
            : "This walker is locked while a phone owns it. Return it over "
              "Wi-Fi, or recover the local snapshot if the phone is "
              "unavailable.",
        22, 7);
    if (force)
      wrap(18, 116, RED, "This ends the current phone session.", 28, 2);
    else
      wrap(18, 116, MUTED,
           "Return over Wi-Fi or use recovery if the phone is unavailable.",
           28, 2);
    footer(force              ? "A Restore and revoke B Cancel"
           : s->wifiAvailable ? "A Retry Y Return X Recover R Backups"
                              : "A Retry Y Return X Recover R Backups");
    return;
  }
  if (s->screen == UI_WIFI) {
    if (s->wifiPhase == 6) {
      header("Network name");
      panel(8, 32, 240, 28, 0);
      text(14, 41, INK, s->wifiSsid, 28);
      if (strlen(s->wifiSsid) > 30)
        text(14, 50, INK, s->wifiSsid + 30, 2);
      unsigned length = strlen(s->wifiSsid);
      if (length < 32)
        text(14 + (length % 28) * 8, 41 + (length / 28) * 11, TEAL, "|", 1);
      if (!strncmp(s->wifiMessage, "Enter a name", 12))
        text(8, 63, GOLD, "A network name is required", 25);
      else
        fmt(8, 63, MUTED, 22, "R Keyboard page %d/2", s->wifiTextPage + 1);
      fmt(208, 63, TEAL, 5, "%u/32", length);
      for (int i = 0; i < 48; i++) {
        int x = 8 + (i % 8) * 30, y = 76 + (i / 8) * 15;
        unsigned ch = 32 + s->wifiTextPage * 48 + i;
        panel(x, y, 28, 13, i == s->wifiKeyCursor);
        char glyph[2] = {ch < 127 ? (char)ch : ' ', 0};
        text(x + (ch == 32 ? 6 : 10), y + 3, INK, ch == 32 ? "SP" : glyph, 2);
      }
      footer("A Add X Del R Page START Done");
      return;
    }
    if (s->wifiPhase == 2) {
      header("WEP key");
      panel(8, 33, 240, 35, 0);
      text(15, 39, MUTED, "10, 26 or 32 hexadecimal digits", 29);
      char masked[33];
      unsigned len = strlen(s->wifiKey);
      memset(masked, '*', len);
      masked[len] = 0;
      fmt(15, 52, INK, 29, "%u / 32: %s", len, masked);
      for (int i = 0; i < 16; i++) {
        int x = 8 + (i % 4) * 60, y = 73 + (i / 4) * 22;
        panel(x, y, 56, 19, i == s->wifiKeyCursor);
        char ch[2] = {"0123456789ABCDEF"[i], 0};
        text(x + 24, y + 6, INK, ch, 1);
      }
      if (s->wifiMessage[0] != 'E')
        wrap(8, 163, GOLD, s->wifiMessage, 30, 1);
      footer("A Add X Delete START Connect");
      return;
    }
    header("Wi-Fi setup");
    if (s->wifiPhase == 1) {
      text(8, 33, MUTED, "Choose a visible network", 28);
      for (int row = 0; row < 6; row++) {
        int i = s->wifiCursor / 6 * 6 + row;
        if (i >= s->wifiCount)
          break;
        int y = 49 + row * 18;
        panel(8, y, 240, 16, i == s->wifiCursor);
        text(14, y + 4, INK, s->wifiNames[i], 20);
        badge(190, y + 2, s->wifiSecurity[i] == 2 ? "WPA"
                         : s->wifiSecurity[i]    ? "WEP"
                                                 : "OPEN",
              s->wifiSecurity[i] == 2 ? RED : TEAL, 4);
      }
      wrap(8, 160, GOLD, s->wifiMessage, 30, 1);
      footer("A Select Y SSID R Scan B Back");
    } else {
      panel(8, 38, 240, 86, 0);
      deviceIcon(18, 50, 34);
      badge(64, 47, s->wifiPhase == 4 ? "CONNECTED" :
                          s->wifiPhase == 3 ? "CONNECTING" :
                          s->wifiPhase == 5 ? "NOT FOUND" : "READY",
            s->wifiPhase == 4 ? GREEN : s->wifiPhase == 5 ? RED : GOLD,
            s->wifiPhase == 4 ? 10 : s->wifiPhase == 3 ? 11 :
                               s->wifiPhase == 5 ? 10 : 5);
      wrap(64, 68, s->wifiPhase == 4 ? GREEN : INK, s->wifiMessage, 22, 4);
      if (s->wifiPhase == 3)
        bar(64, 109, 164, 7, (s->frame % 80) / 79.f, TEAL);
      wrap(8, 133, MUTED, "DS Lite: open or WEP networks.", 30, 2);
      footer(s->wifiPhase == 0 || s->wifiPhase == 5
                 ? "Y Enter SSID R Rescan B Back"
                 : "R Rescan B Back");
    }
    return;
  }
  const char *title = s->screen == UI_HOME       ? "Adventure menu"
                      : s->screen == UI_SETTINGS ? "Settings 1.7.1"
                      : s->screen == UI_RADAR    ? "Poke Radar"
                      : s->screen == UI_DOWSE    ? "Dowsing"
                      : s->screen == UI_BATTLE   ? "Choose a move"
                      : s->screen == UI_PACK     ? "Your pack"
                      : s->screen == UI_REPLACE  ? "Choose a slot"
                      : s->screen == UI_CARD     ? "Trainer card"
                                                 : "Journal";
  header(title);
  if (s->screen == UI_HOME) {
    const char *labels[] = {"Pokewalker", "Update steps", "Settings"};
    const char *descriptions[] = {"Open the walker menu", "Refresh today's steps", "Wi-Fi and preferences"};
    for (int i = 0; i < 3; i++) {
      int y = 36 + i * 40;
      panel(8,y,240,36,i==s->selection);
      if (i == 0)
        deviceIcon(16, y + 7, 22);
      else
        ndsUiRect(20, y + 11, 13, 13, i == s->selection ? GOLD : TEAL);
      text(44,y+7,INK,labels[i],23);
      text(44,y+21,MUTED,descriptions[i],25);
      text(222,y+12,i==s->selection?GOLD:MUTED,">",1);
    }
    if (s->toast[0]) {
      panel(8, 158, 240, 15, 0);
      text(14, 162, TEAL, s->toast, 29);
    }
  } else if (s->screen == UI_SETTINGS) {
    const char *labels[] = {"Time-based steps", "Pedometer", "Step rate",
                            "Phone sync", "Wi-Fi setup"};
    for (int i = 0; i < (s->wifiAvailable ? 5 : 4); i++) {
      int y = 32 + i * (s->wifiAvailable ? 25 : 31);
      panel(8, y, 240, s->wifiAvailable ? 23 : 28, i == s->selection);
      text(16, y + (s->wifiAvailable ? 3 : 6), INK, labels[i], 21);
      char value[24];
      if (i == 2)
        snprintf(value, sizeof(value),
                 s->secondsPerStep >= 3600 ? "%uh" : "%us",
                 s->secondsPerStep >= 3600 ? s->secondsPerStep / 3600
                                           : s->secondsPerStep);
      if (i != 2)
        snprintf(value, sizeof(value), "%s",
                 i == 3              ? "Auto"
                 : i == 4            ? "Setup"
                 : i == 1            ? "N/A"
                 : s->walkingEnabled ? "On"
                                     : "Off");
      text(200, y + (s->wifiAvailable ? 3 : 6), TEAL, value, 5);
      if (s->wifiAvailable)
        text(16, y + 13, MUTED, i == 4 ? "Select a wireless network" :
                                      i == 3 ? "Uses saved Wi-Fi and app" :
                                      i == 2 ? "Steps per walking update" :
                                      i == 1 ? "Motion sensor status" :
                                               "Use elapsed time",
             26);
    }
    panel(8,156,240,20,0);text(16,162,TEAL,"X Backups  SELECT Rewards",28);

  } else if (s->screen == UI_PACK || s->screen == UI_REPLACE) {
    int replace = s->screen == UI_REPLACE;
    panel(8, 35, 240, replace ? 105 : 55, 0);
    text(16, 41, TEAL, replace ? (s->replaceKind ? "CHOOSE AN ITEM SLOT" : "CHOOSE A POKEMON SLOT")
                              : "POKEMON ON THIS WALK", 27);
    for (int i = 0; i < 3; i++) {
      unsigned id = (replace && s->replaceKind) ? walkerItemId(s->ee, i)
                                                : walkerPokemonId(s->ee, i);
      int y = replace ? 61 + i * 23 : 59 + i * 10;
      if (replace)
        panel(15, y, 226, 20, i == s->selection);
      if (replace && s->replaceKind)
        fmt(22, y + 6, INK, 27, "%d. %s", i + 1, itemName(id));
      else
        fmt(replace ? 22 : 16, y + (replace ? 6 : 0), INK, 28, "%d. %s", i + 1,
            id && id != 65535 ? speciesName(id) : "Empty");
    }
    if (!replace) {
      panel(8, 99, 240, 61, 0);
      text(16, 106, GOLD, "ITEMS FOUND", 18);
      for (int i = 0; i < 3; i++) {
        unsigned id = walkerItemId(s->ee, i);
        if (id && id != 65535)
          fmt(16, 123 + i * 11, INK, 28, "%d. %s", i + 1, itemName(id));
        else
          fmt(16, 123 + i * 11, MUTED, 28, "%d. Empty", i + 1);
      }
    } else {
      panel(8, 147, 240, 20, 0);
      text(16, 153, MUTED, "A Replace   B Keep current contents", 29);
    }
    footer(replace ? "D-pad Choose   A Replace   B Keep" : "B Back");
    return;
  } else if (s->screen == UI_CARD) {
    panel(8, 35, 240, 126, 0);
    badge(16, 43, "TRAINER CARD", GOLD, 13);
    wrap(16, 60, INK, s->info.trainer[0] ? s->info.trainer : "Not registered", 27, 2);
    fmt(16, 83, TEAL, 28, "%s  Lv %u", speciesName(s->info.species),s->info.level);
    fmt(16, 101, INK, 28, "Bond  %u / 255", s->info.friendship);
    fmt(16, 119, MUTED, 28, "%u Pokemon   %u items", s->info.pokemonCount,s->info.itemCount);
    fmt(16, 137, MUTED, 28, "Steps %lu  Today %lu",
        (unsigned long)s->info.totalSteps, (unsigned long)s->info.todaySteps);
    text(16, 153, GOLD, s->info.route[0] ? s->info.route : "Route not set", 28);
    footer("B Back");
    return;
  } else if (s->screen == UI_RADAR) {
    panel(8, 36, 240, 73, 0);
    badge(16, 44, "CURRENT ROUTE", TEAL, 14);
    wrap(16, 66, INK, s->info.route[0] ? s->info.route : "No route selected", 27, 2);
    if (s->ee && s->info.hasPokemon) {
      unsigned visitor = walkerRoutePokemonId(s->ee, 0);
      if (visitor && visitor != 65535)
        fmt(16, 91, MUTED, 27, "Route visitor: %s", speciesName(visitor));
    }
    panel(8, 121, 240, 39, 0);
    fmt(16, 130, GOLD, 28, "%lu steps  %u watts",
        (unsigned long)(s->info.strollSteps + s->pending), s->info.watts);
    wrap(16, 145, MUTED, "Keep walking to discover a visitor.", 27, 1);
    footer("B Back");
    return;
  } else if (s->screen == UI_DOWSE) {
    panel(8, 36, 240, 58, 0);
    deviceIcon(18, 47, 34);
    badge(64, 44, "DOWSING", GOLD, 8);
    wrap(64, 65, INK, "Stored watts can be spent to search this route.", 22, 3);
    panel(8, 105, 240, 55, 0);
    text(16, 113, MUTED, "AVAILABLE WATTS", 20);
    fmt(16, 130, GOLD, 28, "%u", s->info.watts);
    wrap(72, 131, MUTED, s->info.route[0] ? s->info.route : "No route selected", 21, 2);
    footer("B Back");
    return;
  } else if (s->screen == UI_BATTLE) {
    panel(8, 35, 240, 33, 0);
    badge(16, 41, "WILD", GOLD, 4);
    wrap(64, 44, INK,
         s->ee ? speciesName(walkerRoutePokemonId(s->ee, s->battle.encounter)) : "Visitor",
         21, 2);
    for (int i = 0; i < 4; i++) {
      unsigned move = s->ee ? walkerPartnerMove(s->ee, (unsigned)i) : 0;
      const char *name = move ? walkerMoveName(move) : "No move";
      panel(8, 73 + i * 18, 240, 16, i == s->battle.row);
      fmt(16, 77 + i * 18, i == s->battle.row ? INK : MUTED, 28,
          "%d  %.24s", i + 1, name);
    }
    fmt(8, 148, GOLD, 28, "Party HP %d/4   Visitor HP %d/4",
        s->battle.playerHp, s->battle.enemyHp);
    footer("D-pad Choose   A Attack   B Back");
    return;
  } else if (s->screen == UI_RESULT || s->screen == UI_DISCARD_WALKER) {
    panel(8, 37, 240, 43, 0);
    badge(16, 44, s->screen == UI_DISCARD_WALKER ? "UNSAVED CHANGES" : "RESULT", GOLD,
          s->screen == UI_DISCARD_WALKER ? 16 : 6);
    wrap(16, 62, INK, s->message, 27, 2);
    panel(8, 89, 240, 70, 0);
    wrap(16, 98, MUTED, s->detail, 27, 5);
    footer(s->screen == UI_DISCARD_WALKER ? "A Discard  B Keep" : "A Continue B Back");
    return;
  }
  footer(s->screen == UI_HOME ? "START Save and exit  B Back"
         : s->screen == UI_SETTINGS && s->selection == 3
             ? "A Auto sync B Back"
         : s->screen == UI_SETTINGS ? "D-pad/A Change B Back"
                                  : "D-pad/Touch A Select B Back");
}
