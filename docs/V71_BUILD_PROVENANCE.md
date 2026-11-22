# V7.1 — Build provenance and testability

## Verified development build

The full forked `core/bootstrap/retail` make target compiled successfully in GitHub Actions [run 44982241279](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/actions/runs/44982241279), using the historical toolchain image `devkitpro/devkitarm:20240918` and a statically compiled host `lzss` utility.

This result **does not certify runtime Wi-Fi**, transfer correctness, HGSS boot stability on hardware, or save integrity. No nds-bootstrap .nds should be distributed as a V7.1 in-game Wi-Fi release until those separate gates are met.

## Official upstream compatibility data

The imported fork omitted some game compatibility inputs from its Git tree. CI retrieves the official folders only, at the pinned **DS-Homebrew/nds-bootstrap** commit:

```
f6728baaa28a6fffbd070badce60d0b470180e1e
```

Official source: https://github.com/DS-Homebrew/nds-bootstrap

Locations included in CI:
- `retail/preLoadSettings/files-*`
- `retail/apfix/files/` (including `files/cht`), plus `files-bugged/`
- `retail/mobiclipOffsets/files/`
- `retail/dsi2dsSavePatches/files/` and `files-bugged/`

The pipeline uses Git sparse checkout and merges **missing** files without overwriting tracked fork patches, then builds the compatibility packs using the fork's original Makefiles. It never creates empty placeholder packs. Inputs are pulled only at CI runtime and are not silently committed as new proprietary binaries. Respect each upstream file's applicable attribution/licensing requirements.

## Remaining V7.1 in-game networking blockers

- The DSi hotspot standalone diagnostic passed on hardware: 6 PINGs, 8192 synthetic echo bytes, 10/10 successful requests.
- The full nds-bootstrap *build* now passes.
- The ARM7/ARM9 runtime transport and WCM/SOCL call entrypoints are **not** validated as resident during HGSS.
- Source overlay references in public HGSS decompilation do not establish callable addresses or lifetime.
- The V7.1 resolver intentionally keeps all unverified call entrypoints blank and `ready=0`.
- `tools/v7_1/network_symbols.json` and its CI verification block accidental promotion of unreviewed guessed function addresses.

**Next meaningful hardware test:** a separate build demonstrating PING ↔ OP_OK during HGSS, using Android hotspot only. Until then, no new console test is requested and no PUSH/PULL/CONFIRM should be enabled.

## Credit

This project derives from [SD-Transporter by Shinygati](https://github.com/Shinygati/SD-Transporter) and builds on nds-bootstrap, TWiLight Menu++, devkitPro, Pokéwalker reverse engineering, and numerous original contributors. Preserve their copyright and licensing notices; see `ATTRIBUTION.md`, `CREDITS-UPSTREAM.md`, and `LICENSE`. Android home-screen widget and skins are a first-class workstream (issue #2), not replaced by the network research.

## Ping-only resident ARM9 preparation

V7.1 now includes a deliberately restricted, small ARM9 module in the **actual DSi cardengine source directory** (`cardenginei/arm9/source/walker_ping_diagnostic.c`). It exposes only:
- `walkerV71MakePing(output, capacity)`: builds exactly 88 protocol bytes, no save payload
- `walkerV71CheckPingOk(frame, length)`: accepts only the exact PING acknowledgement header, and rejects truncated/oversized frames, nonzero CRC, session/trainer bytes, malformed magic/version/flags, and any transfer opcode

Both functions use the common `walker_ping_only.h` framing implementation. Native tests run the exact ARM9 module against malformed packets; C-to-Java interoperability tests verify the same 88-byte format accepted by Android V18. A separate devkitARM cross-compile check validates the portable header.

**Crucial distinction:** this is only a protocol primitive *linked into* the DSi cardengine; neither function is currently invoked from a runtime network path. There is still no resident Wi-Fi initialization, TCP handshake, or PING sent while HGSS runs. The unsigned WCM/SOCL pointers remain zero and transactions PUSH/PULL/CONFIRM remain disabled. It is not a testable HGSS transfer release.

The Android home-screen widget and skins remain separate tracked work and should be included in future APK updates without discarding upstream attribution.

### Resident cardengine symbol/linker validation

Added a CI symbol check using `arm-none-eabi-nm` on the primary DSi `cardenginei_arm9.elf`: it must contain both `walkerV71MakePing` and `walkerV71CheckPingOk` rather than merely accepting source files in the tree.

A complete build exposed a `.bss` overflow in `cardenginei_arm9_dldi` after introducing this helper; the runtime source is now conditioned on `!DLDI && !GSDD && !TWLSDK`, so that alternative cardengines do not import the experimental path or have their fixed memory limits expanded. Recheck whole-build CI before treating the change as verified.

The PING-only helper remains uncalled by any Wi-Fi backend; no new in-game functionality has been shown on hardware.

## 2026-11-22 — PING-only linked symbol verification

The previous `v71-bootstrap-build.yml` edit had accidentally duplicated sections and broken YAML. It was reconstructed as a valid two-job workflow with the historical devkitARM r65-compatible SDK, pinned official compatibility sources, and explicit non-release status.

In GitHub Actions [run 44983036243](https://github.com/LittleCherryyy/PokeWalkerForkSDTRANSPORTER/actions/runs/44983036243), the **actual primary DSi ARM9 ELF** was checked with `arm-none-eabi-nm`, and both `walkerV71MakePing` and `walkerV71CheckPingOk` were present. The independent ARM7/ARM9/IGM modules passed. The **complete experimental nds-bootstrap build step also passed**.

These symbols currently encode/validate packets **only**; they do not open sockets or perform any resident Wi-Fi handshake. No HGSS hardware PING or Pokémon transfer has been verified. No modified bootstrap from this experiment should be promoted as a functional in-game direct-sync release until the resident runtime is independently tested with disposable saves.

## V7.1 — Bounded hotspot PING state machine (experimental)

New implementation:
- `common/include/walker_ping_fsm.h` defines a small reusable nonblocking I/O callback interface: `connect_gateway(30821)`, `send_some`, `recv_some`, `close_connection`. The intended destination is **only the connected Android hotspot DHCP gateway**; no IP entry, home router, or separate DSi homebrew is part of the final workflow.
- `cardenginei/arm9/source/walker_ping_fsm.c` implements PING → OP_OK using a **maximum of one callback per step**, a bounded tick budget (default 300 invocations), partial sends/receives, no retries of completed state and strict 88-byte response validation. This is entirely independent of EEPROM and save data. It is **not** a working Wi-Fi backend: the caller must supply proven, genuinely nonblocking socket functions and their lifecycle.
- `tools/v7_1/test_ping_fsm.c` drives the actual C code with fake sockets and checks port, framing, partial I/O, deliberate failures, malformed replies, timeout and non-reentrant one-operation-per-step behavior. GitHub Actions also cross-compiles the code for ARM using a new `-fsyntax-only` check.
- DSi NTR game still links the earlier `walkerV71MakePing` / `walkerV71CheckPingOk` low-level framing helpers only.

**Memory budget finding:** linking the additional FSM straight into `cardenginei_arm9` (without a working backend or caller) caused a real fixed-VRAM linker overflow of **592 bytes** in GitHub Actions run `44983413107`. We did not expand the memory region. The module was placed behind compile flag `WALKER_PING_FSM_EXPERIMENT`, so it is checked on host and by cross-compiler but omitted from game binaries. An explicitly reviewed resident memory/overlay placement strategy is required before enabling the FSM or any WCM/SOCL call sites. These changes do not justify deploying a test build for HGSS yet.

Hardware-dependent questions remaining:
- Can nds-bootstrap safely retain a nonblocking Wi-Fi driver across HGSS boot in DS mode, given ARM7 ownership and HGSS's own wireless libraries?
- Are the relevant WCM/SOCL functions actually resident for the exact HGSS revision and available during the Pokéwalker menu, rather than only referenced in overlays?
- Where will the PING FSM reside without exceeding fixed cardengine memory, and how can frame-paced polling avoid interrupt latency and SD save operations?
- Android hotspot network configuration must be compatible with the DS-mode Wi-Fi radio (as previously tested on the standalone diagnostic).

All original SD-Transporter, nds-bootstrap and dependency copyright/licensing notices remain intact. Android widget development, skins, and Premier Ball corrections remain a separate tracked workstream.
