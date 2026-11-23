# HGSS Pokéwalker Virtual — V9.9 dual ABI model (2026-11-22)

Source: user-generated `wifi_v99_hgss_dual_abi.json` for original US Rev0
HeartGold `IPKE` (SHA-1 `4fcded0e2713dc03929845de631d0932ea2b5a37`)
and SoulSilver `IPGE` (SHA-1 `f8dc38ea20c17541a43b58c5e6d18c1732c7e582`).

All three candidate regions have equal static analysis results in the two games.

## Observed candidate origins

| Region | Tested entry | Tracked register | Unrestricted-call model | Hypothetical callee-saved model | Reachable from selected entry in abstract model? |
|---|---|---|---|---|---|
| A | `0x020D1808` | r0 | none | none | No |
| A alternative | `0x020D1690` | r0 | none | none | No |
| B | `0x020D1FA0` | r8 | `call@0x020D1FB8` | `runtime_load@0x020D1FB4` | Yes |
| B alternative | `0x020D1F84` | r8 | none | none | No |
| C | `0x020D2058` | r7 | `call@0x020D2070` | `entry_unknown_r0` | Yes |
| C alternative | `0x020D1FA0` | r7 | none | none | No |

Interpretation: The unlimited call-clobber model can erase potentially meaningful
r7/r8 provenance. Under the alternative AAPCS-like assumption, the r8 base
possibly comes from a memory load at `0x020D1FB4`, while r7 possibly
originates in the function's incoming r0 argument, copied at `0x020D2060`.
Both are model-dependent: there is **no verified Nintendo ABI**, no actual
RAM read, no verified function entry, and no observed runtime execution.

A's two false reachability results do NOT demonstrate A's store is dead:
the bounded model has unresolved indirect branches and missing outside edges.

## V10.0 next step

The read-only `tools/v10_0/hgss_callsite_argument_abi_audit.py`:
- inspects the exact A32 addressing of the r8 source load
- checks the r7 <- r0 move in original ROM bytes
- searches all A32 words in reconstructed ARM9 for direct calls to the three
  tentative entrypoints
- produces bounded nearest possible r0 writer candidates before each call
- records entry prologue register-save masks and potential intermediate returns
  or forward-branch blockers

No code is executed on the DSi and no ROM/save/Android/bootstrap data is
modified. All results remain syntactic hypotheses; do not infer safe worker
thread creation, ARM7 radio/IRQ control, or working Wi-Fi from them.
