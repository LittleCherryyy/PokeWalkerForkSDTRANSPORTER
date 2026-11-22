# HGSS V10.2 — bounded ARM9 path witnesses (2026-11-22)

Evidence: user-produced \`wifi_v102_hgss_cfg_paths.json\` from original
US Rev0 HeartGold (IPKE) and SoulSilver (IPGE). The report's
\`comparison.all_equal\` is true for A/B/C. All paths are **syntactic**.

## Results: candidate path to original ARM9 store of 0x021E16A8

| Region | Tested entry | Original store PC | V10.2 abstract path? | Crucial assumptions |
|---|---|---|---|---|
| A original | \`0x020D1808\` | \`0x020D18A4\` | No | Earlier LDM-PC return stops the bounded path |
| A alternative | \`0x020D1868\` | \`0x020D18A4\` | Yes | Skip conditional B at \`0x020D1888\`; skip conditional BXNE LR at \`0x020D1898\` |
| B | \`0x020D1FA0\` | \`0x020D2034\` | Yes | BL at \`0x020D1FB8\` assumed to return; conditional B taken from \`0x020D200C\` to \`0x020D201C\`, skipping an unconditional LDM-PC |
| C | \`0x020D2058\` | \`0x020D20D4\` | Yes | BL at \`0x020D2070\` assumed to return; conditional B taken from \`0x020D209C\` to \`0x020D20B0\`, skipping an unconditional LDM-PC |

A alternative is called by two direct A32 BL **syntax candidates**:
\`0x020D1CB8\`, \`0x020D1D30\`. B has eight candidates, C six.

The modeled path to A's store is **13 A32 edges**, B **23**, C **25**.
All paths still need unknown CPSR outcomes. B and C also require
unproved call-return assumptions. None of the store sites is proven to
execute in the game.

## Why V10.3 exists

V10.2 allows independent choices for successive conditional branches,
even when no intervening instruction could have changed ARM's CPSR flags.
This can create impossible paths such as BEQ-taken immediately followed by
BNE-taken without any NZCV modification. It does not mean such a
contradiction exists in the actual HGSS paths; it is a limitation of V10.2.

\`tools/v10_3/hgss_cpsr_path_consistency.py\` enumerates all 16 initial
N/Z/C/V combinations and filters conditional choices against the same
flags until flag-writing instructions or calls may make flags unknown again.
All flag-writing instructions conservatively reset to **any** NZCV tuple:
this avoids inventing arithmetic outputs but still only provides a
*possible-path overapproximation*, never an execution proof.

Synthetic tests cover contradicting conditions, flag refresh, a
conditional BX-LR skip, and unconditional return termination. These
synthetic tests passed in development. Tests on original ROM pair remain
pending user execution.

## Safety gate

No save or ROM modifications; no worker/thread creation, ARM7 radio
ownership, Wi-Fi bridge deployment or Pokéwalker transfer is justified
by these static findings alone. The next goal is narrowing predicate
assumptions, verifying call paths and SDK ABI before touching runtime.
