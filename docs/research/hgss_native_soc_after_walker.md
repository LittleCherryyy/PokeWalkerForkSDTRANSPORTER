# Alternative resident Wi-Fi: reuse HGSS's Nitro SOC stack AFTER the IR overlay unloads

Scope: **real Nintendo DSi**, original HeartGold/SoulSilver in DS mode,
no extra user-launched NDS app. This is architecture research, not a
working radio implementation.

## Concrete executable code evidence

The independent `pret/pokeheartgold` project shows original game code
with native socket entrypoints:
- `asm/overlay_13_thumb_2.s`, `ov13_022228CC` calls **SOC_Startup**
  and waits for `CPSMyIp` to be configured.
- `lib/NitroDWC/asm/overlay_39_arm.s`, `ov39_02229AD4` invokes
  **SOC_Socket** followed by **SOC_Fcntl**.
- `lib/NitroDWC/asm/include/overlay_00_arm.inc` exposes
  `SOC_Socket`, `SOC_Connect`, `SOC_Send`, `SOC_Recv`,
  `SOC_Close`, `SOC_Startup`, `WCM_Init`, `WCM_StartupAsync`.
  
Sources:
- https://github.com/pret/pokeheartgold/blob/master/asm/overlay_13_thumb_2.s
- https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/overlay_39_arm.s
- https://github.com/pret/pokeheartgold/blob/master/lib/NitroDWC/asm/include/overlay_00_arm.inc

The already analyzed USA Rev0 ROM overlay map establishes that **overlay
0 (NitroDWC) and overlay 112 (Pokéwalker)** occupy the same linked RAM
range, from `0x021E5900`. They cannot coexist *at their original
addresses*. The game's native sockets are therefore NOT callable simply
because `SOC_Socket` can be found in a disassembly.

## Candidate path to true in-game Android transfer

1. Keep SD Transporter's existing virtual IR hook as-is until HeartGold
   finishes the original Pokémon checkout and returns to game control.
   Preserve the durable 64 KiB `.walker` and `.walker.directlock`.
2. Observe/identify the game's **actual overlay unload and load
   mechanism**. Do not replace or page overlays from ARM7 VBlank.
3. After the game has released overlay 112, arrange for **game-managed**
   loading/initialization of the NitroDWC networking overlay 0 at the
   correct original address, in a non-IRQ ARM9 execution context.
   A forced load during another overlay's lifetime is not safe.
4. Verify independently that the game's original ARM7 Nitro WFC service
   is initialized and available, the relevant SOC/WCM initialization
   flow has completed, and the DS is associated to the phone's
   **open 2.4 GHz hotspot**.
5. Only then bind a `WalkerDirectRadioOps` backend to verified, live
   `SOC_*` entrypoints; use the existing 88+65536-byte TCP sender,
   verifying session-bound Android `OP_OK` before reporting success.
6. Integrate controlled teardown and return to gameplay without
   leaving game overlay refcounts, threads, interrupts or networking
   state inconsistent. Persist the phone ownership lock across reboot.

**Crucial constraint:** those symbols are evidence of what the game can
do in its *normal* network state, not evidence that their ABI and
initialization are valid in Pokéwalker mode, nor that activating the
network overlay is harmless. Different ROM revisions need independent
signature/overlay-table validation.

## Comparison with standalone DSWifi service

An independent DSWifi7 driver is another possible architecture but is
not a drop-in C socket library. DSWifi requires simultaneous ARM7/ARM9
modules, shared uncached RAM queues, FIFO synchronization, WiFi IRQ,
a hardware timer and its own initialization. It must coexist with
the game's ownership of those resources. Linking a socket client and
calling `Wifi_InitDefault()` in a stock retail game is insufficient.
See https://blocksds.skylyrac.net/dswifi/md_documentation_2library__design.html
and https://blocksds.skylyrac.net/dswifi/md_documentation_2internet__mode.html

**Decision:** prioritize verifying the game's post-Pokéwalker native
WFC initialization and overlay lifecycle *before* attempting a second
independent ARM7 Wi-Fi stack that would need additional reserved memory
and resource arbitration. Avoid new emulator instruction traces unless
they directly answer those overlay and SOC lifecycle questions.

**No user hardware test or APK/nds-bootstrap release** until a radio
backend is actually linked and the entire send-to-phone transaction
works safely. This file establishes a plan; it does not claim a solved
Wi-Fi implementation.
