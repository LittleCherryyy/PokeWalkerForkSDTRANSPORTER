# Virtual Pokéwalker V8.9 — original HGSS ARM9 scheduler field opcodes

## Observed hardware result: user's V8.8 screenshot (Nov 22 2026)

The user loaded the experimental V8.8 `nds-bootstrap` via
TWiLight Menu++ Nightly on the Nintendo DSi and photographed
`V8.8 OS LAYOUT 2.X` while in Goldenrod Pokémon Center.

The original game ARM9 opcode signature and scheduler-available
read guard passed; the six fixed, aligned data words displayed:

| Exact 32-bit NTR address | Raw word | Meaning proven |
| --- | --- | --- |
| 0x021E169C | 0x00000003 | None |
| 0x021E16A0 | 0x00000000 | None |
| 0x021E16A4 | 0x021E1770 | Aligned plausible main-RAM address only |
| 0x021E16A8 | 0x021E3864 | Aligned plausible main-RAM address only |
| 0x021E16AC | 0x00000000 | None |
| 0x021E16B0 | 0x0000001F | Integer 31; not an aligned NTR pointer |

The middle pair remains identical to the user's separate V8.6
screenshots in Goldenrod Pokémon Center and Route 35.

**Revised hypothesis assessment:** The public NitroSDK
`include/nitro/os/common/thread.h` has two distinct `OSThreadInfo`
layouts:

- `SDK_THREAD_INFINITY` variant (normally NitroSDK >= 3):
  current at base+4, list at base+8, callback at base+12.
- Older SDK fixed 16-entry array:
  current at base+8, list at base+12, callback at base+16,
  `max_entry` u16 at base+2 and `entry[0]` at base+20.

The public `pret/pokeheartgold` Meson build selects NitroSDK 2.0.
That motivated testing the **older** candidate structure at
`0x021E169C`. Its hypothetical `max_entry` is 0 and
`entry[0]` is 31, which is *not* an aligned NTR main-RAM
pointer. This is serious evidence **against** that specific
layout/base combination. It does not establish that
`0x021E16A0` is the true `SDK_THREAD_INFINITY` structure,
because those four words could be an unrelated or customized data
structure, and the actual compiled SDK details are not yet proven.

Sources for variant layouts and historical build selection:
- https://github.com/ljtpetersen/ntrtwl-NitroSDK/blob/main/include/nitro/os/common/thread.h
- https://github.com/pret/pokeheartgold/blob/master/meson.build

## V8.9 offline deliverable

`tools/v8_9/hgss_scheduler_field_xrefs.py` analyzes two user-owned,
unmodified original USA Rev0 HGSS ROM files. It rechecks the strict
original ROM identity and the established V8.4 exact ARM9 opcode
and static literal reference gates. It inspects **only** the
instruction *immediately after* a validated unconditional ARM
PC-relative LDR literal load. This extends V8.5 with ARM
`LDRH/STRH` immediate, 16-bit memory accesses because older
NitroSDK `OSThreadInfo` has u16 fields.

ARM9 instruction families recognized:
- `LDRH/STRH` unconditional immediate halfword
- `LDR/STR` unconditional immediate word
- `LDRB/STRB` unconditional immediate byte

Only valid, in-image static literal addresses are inspected.
The script outputs the computed **effective address**, direction,
width, source instruction address, and cross-game match status.
It DOES NOT read the data at the computed address, follow any
pointers, export code bytes or call game/ROM/NitroSDK/Wi-Fi APIs.

An ARM-shaped word in data can produce a false static match:
even an identical cross-title match is not proof of a running
function or a particular OS struct field.

The V8.9 output explicitly keeps both struct identities unproven
and marks thread creation, free worker stack, ARM7 radio ownership
and Wi-Fi as disabled. No .sav/.walker changes or Android APK update.

## Next user action

After successful GitHub Actions host tests, download
`Pokewalker-V8_9-Scheduler-Field-Xrefs-Windows`, extracting
all prerequisite `tools/v7_3` through `tools/v8_9` directories
in their relative paths. Drag both original USA Rev0 HG/SS ROM
backups to

`tools/v8_9/COMPARAR_CAMPOS_THREADS.bat`

Send only `tools/v8_9/wifi_v89_hgss_thread_field_xrefs.json`.
If the tool fails, share the error text, not the ROMs.

**Keep the V8.8 DSi bootstrap installed**, with no Android or hotspot
changes. Further live reading of actual thread objects and any
creation/wakeup or NTR-mode Wi-Fi startup remain forbidden until
a verified, independent memory/scheduler/ARM7 ownership design exists.
