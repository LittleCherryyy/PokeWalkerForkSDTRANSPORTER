# Virtual Pokéwalker V8.4 — original HGSS thread flag cross-references

## Real Nintendo DSi V8.3 result — 2026-11-22

One supplied photo of an original US HGSS running under the experimental
V8.3 nds-bootstrap shows `V8.3 ARM9 OS FLAG`:

- `OS raw value: 0x00000001`
- `No thread API called`
- `Wi-Fi: NOT ENABLED`

The V8.3 implementation reads a single RAM word at `0x021E1688`
only after authenticating the exact original 4-word
`OS_IsThreadAvailable` ARM instruction/literal signature at
`0x020D1AC4`. A guarded read returning 1 establishes the original
function's boolean result at that moment, without invoking it.

The Nintendo NitroSDK OS_IsThreadAvailable documentation says TRUE
means the thread system has been initialized and is available for
application use:
https://twlsdk.randommeaninglesscharacters.com/docs/nitro/NitroSDK/os/thread/OS_IsThreadAvailable.html

**Interpretation:** A thread subsystem appears initialized and
available in the current game state. That does not prove capacity,
`OSThread` structure layout, a free persistent stack, number of live
threads, safe init context, or radio ownership. A second after-gameplay
photograph of V8.3 would help establish stability; it is not needed
to run this offline V8.4 audit.

## New V8.4 offline analysis

This milestone builds a conservative ARM9 read-only cross-reference
map of the original availability global and candidate aligned addresses
within 64 bytes of it in both HG and SS, without the original ROM bytes
or game saves leaving the user's computer.

The script `tools/v8_4/hgss_thread_flag_xrefs.py`:

1. Gates original USA Rev0 ROM SHA-1, the original decompressed ARM9
   image, V8.0 5/5 OS callsite signatures, V8.1 6-argument caller ABI,
   V8.2 bounded entry scans and overlay 39 ownership.
2. Authenticates the exact 4 original ARM words constituting
   `OS_IsThreadAvailable` (3 instructions and the literal
   `0x021E1688`).
3. Scans the reconstructed, bounded static ARM9 image for word-aligned
   candidate literal values from `0x021E1648`–`0x021E16C8`.
4. Only reports an ARM PC-relative LDR cross-reference when its exact
   address calculation resolves to one of these literal locations.
   Unknown / conditional / Thumb encodings are not guessed.
5. Adds nearest 32-byte SHA-256 hashes for comparing static context
   between HeartGold/SoulSilver, without dumping instructions.
6. Emits metadata JSON only; never executes code, calls OS APIs,
   touches .sav/.walker or enables ARM7 Wi-Fi.

Syntactic matches **can** occur in data that looks like code. A value
near the flag might not be a scheduler structure field. A static match
does not justify reading the new address on a real DSi.

## Windows handoff

After GitHub Actions succeeds, download
`Pokewalker-V8_4-Thread-Flag-Crossrefs-Windows`.
Extract folders preserving their directory hierarchy. Select the two
original USA Rev0 ROM backups and drag both onto:

`tools/v8_4/COMPARAR_REFERENCIAS_THREADS.bat`

Send only `tools/v8_4/wifi_v84_thread_flag_xrefs.json`.
Keep the already-tested V8.3 bootstrap on DSi; do not update Android.
No additional physical console test is requested in this milestone.

## Engineering gates still outstanding

- Prove a specific `OSThread` layout and runtime thread-list pointer.
- Reserve a persistent ARM9 stack/object in bootstrap-owned memory
  while avoiding overlay and cache overlap.
- Find an independent non-IRQ thread creation/dispatch point, not
  cardRead / the IRQ-backed IGM.
- Prove safe ARM7 WM/radio ownership and hotspot association in
  the NTR mode running HGSS.
- Only after these conditions, attempt bounded no-save PING over
  Android hotspot port 30821.

**Wi-Fi and game-save transfer remain disabled.**
