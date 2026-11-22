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
