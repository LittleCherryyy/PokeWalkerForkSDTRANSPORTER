#!/usr/bin/env python3
"""V10.4 - generate an opt-in melonDS ARM9 GDB trace bundle from V10.3 JSON.

No ROM is opened, copied or modified. No live emulator, network connection or
save is touched by this generator. The generated GDB script, if a user chooses
to run it, pauses the emulator at original ARM9 instruction PCs and logs a
bounded number of register snapshots; breakpoints affect emulated execution.
An emulator hit DOES NOT prove DSi nds-bootstrap or in-game Wi-Fi operation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

HG_SHA = '4fcded0e2713dc03929845de631d0932ea2b5a37'
SS_SHA = 'f8dc38ea20c17541a43b58c5e6d18c1732c7e582'
REGION_REQUIREMENTS = {
    'A': {'0x020D1808': False, '0x020D1868': True},
    'B': {'0x020D1FA0': True},
    'C': {'0x020D2058': True},
}
# Ordered for consistent traces; symbolic meaning is from V10.0–V10.3.
PROBES = (
    ('A_ENTRY_ALT',     0x020D1868),
    ('A_BXNE_LR',       0x020D1898),
    ('A_STORE',         0x020D18A4),
    ('B_ENTRY',         0x020D1FA0),
    ('B_CALL',          0x020D1FB8),
    ('B_BYPASS',        0x020D200C),
    ('B_STORE',         0x020D2034),
    ('C_ENTRY',         0x020D2058),
    ('C_CALL',          0x020D2070),
    ('C_BYPASS',        0x020D209C),
    ('C_STORE',         0x020D20D4),
)
BASENAME = 'pw_v104_arm9_trace'
MAX_HITS_DEFAULT = 64
MAX_HITS_ALLOWED = 256


def validate(report):
    if report.get('tool') != 'hgss-v10.3-NZCV-consistent-overapproximate-CFG':
        raise ValueError('expected V10.3 CPSR report, not another JSON')
    games = (('heartgold', 'IPKE', HG_SHA),
             ('soulsilver', 'IPGE', SS_SHA))
    for key, code, sha in games:
        game = report.get(key, {})
        if game.get('game_code') != code or game.get('rom_sha1') != sha:
            raise ValueError('original USA Rev0 ROM identity mismatch: ' + key)
        regions = game.get('regions', {})
        for region, expected in REGION_REQUIREMENTS.items():
            found = {entry['entry']: entry for entry in regions.get(region, [])}
            if set(found) != set(expected):
                raise ValueError('unexpected entries in V10.3 '+key+' '+region)
            for entry, reachable in expected.items():
                result = found[entry]['targets']['store']
                if result['v103_cpsr_consistent_possible'] is not reachable:
                    raise ValueError('V10.3 store witness changed: '+key+' '+region)
                if result['v102_permissive_possible'] is not reachable:
                    raise ValueError('V10.2 store witness changed: '+key+' '+region)
    if report.get('comparison', {}).get('all_match') is not True:
        raise ValueError('HG/SS comparison not confirmed identical')
    if report.get('in_game_wifi_verified') is not False:
        raise ValueError('unexpected runtime networking conclusion')
    if report.get('rom_or_save_modified') is not False:
        raise ValueError('unexpected ROM/save mutation in input report')
    return True


def build_gdb(port, max_hits, already_connected=False):
    if not 1 <= port <= 65535 or not 1 <= max_hits <= MAX_HITS_ALLOWED:
        raise ValueError('port or hit limit out of range')
    lines = [
        '# V10.4 - ARM9 *emulator-only* trace; use original unpatched HGSS ROM',
        '# Requires melonDS build with GDB stub enabled; run GDB separately.',
        '# Not a DSi, Android, bootstrap, Pokewalker or live-WiFi test.',
        'set confirm off',
        'set pagination off',
        'set architecture arm',
        'set logging overwrite on',
        f'set logging file {BASENAME}.log',
        'set logging enabled on',
        'set $pw_v104_hits = 0',
    ]
    if already_connected:
        lines.append('printf "PW_V104_EXISTING_CONNECTION remote_ARM9_port='+str(port)+'\\n"')
    else:
        lines.extend([f'target remote localhost:{port}',
                      f'printf "PW_V104_CONNECTED remote_ARM9_port={port}\\n"'])
    for name,pc in PROBES:
        lines.extend([
            f'break *0x{pc:08X}',
            'commands',
            '  silent',
            '  set $pw_v104_hits = $pw_v104_hits + 1',
            (f'  printf "PW_V104_HIT tag={name} '
             f'site=0x{pc:08X} hit=%u pc=0x%08x cpsr=0x%08x '
             'r0=0x%08x r1=0x%08x r7=0x%08x r8=0x%08x '
             'lr=0x%08x sp=0x%08x\\n", '
             '$pw_v104_hits, $pc, $cpsr, $r0, $r1, $r7, $r8, $lr, $sp'),
            f'  if $pw_v104_hits >= {max_hits}',
            '    printf "PW_V104_LIMIT_REACHED - disabling all trace breakpoints\\n"',
            '    disable breakpoints',
            '    set logging enabled off',
            '  end',
            '  continue',
            'end',
        ])
    lines.extend(['printf "PW_V104_BREAKPOINTS_READY\\n"', 'continue'])
    return '\n'.join(lines)+'\n'


def readme(port,max_hits):
    return f"""POKEWALKER V10.4 — EMULATOR ARM9 TRACE (OPT-IN)

WHY
V10.3 did not exclude any candidate path. A trace is needed to distinguish
mere instruction syntax from execution. This bundle is for a debugger-enabled
melonDS emulator. IT DOES NOT TEST Wi-Fi ON THE DSi.

REQUIREMENTS
1. An emulator that exposes an ARM9 GDB stub, e.g. a suitable melonDS build.
   In melonDS: Config > Emu settings > Devtools > Enable GDB stub.
   Check/set ARM9 port {port}; use Break on startup if convenient.
2. A separate GDB with 32-bit ARM support, such as arm-none-eabi-gdb or
   gdb-multiarch. These are external programs, not installed by this bundle.
3. A COPY of an original USA Rev0 HeartGold OR SoulSilver ROM for testing,
   with a SEPARATE test save; do not use the DSi's only save file.
4. This script assumes those original ARM9 PCs are mapped at runtime.

RUN (from the folder containing the generated files)
- Start melonDS with the original ROM and the ARM9 GDB stub enabled.
- Start ARM-capable GDB in the trace folder. For a FIRST connection:
    source {BASENAME}.gdb
- If you already used 'target remote localhost:{port}' manually and
  'info registers' works, DO NOT DISCONNECT. Use the other generated file:
    source {BASENAME}_attached.gdb
- The attached variant does not send target remote again; it installs
  the same breakpoints in the current ARM9 GDB session.
- Either script sets 11 breakpoints, resumes emulation, and logs at
  most {max_hits} instruction stops.
- IMPORTANT: after a failed connect, quit GDB and restart melonDS
  fully to clear potentially stale GDB stub negotiation state.
- Navigate the game's menus normally. Breakpoints may noticeably slow
  the emulator; do not treat timing/networking as representative of DSi.
- Press Ctrl+C in GDB to interrupt. Use 'disconnect' or 'quit' to finish.
- Inspect the generated {BASENAME}.log in the current working directory.

WHAT TO SHARE
The text log with lines beginning PW_V104_, or a concise hit summary.
A hit on A_STORE / B_STORE / C_STORE confirms the emulator reached that PC,
NOT that the target RAM field was actually updated or it is an OSThreadInfo.
A lack of hits during one session does NOT prove the code never runs.

SAFETY
No patching or editing original ROM/save files is needed. Debugger
breakpoints can influence *emulated memory and timing*. Use test-only
copies and avoid write-enabled save syncing. Do not run the script against
real DSi hardware. This bundle has no Wi-Fi / IR / Android / TCP actions.

SOURCES
- https://blocksds.skylyrac.net/docs/guides/debugging/
- https://github.com/melonDS-emu/melonDS
- Project V10.0 through V10.3 analysis artifacts
"""


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,help='Original V10.3 JSON')
    p.add_argument('--output-dir',type=Path)
    p.add_argument('--arm9-port',type=int,default=3333)
    p.add_argument('--max-hits',type=int,default=MAX_HITS_DEFAULT)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args(argv)
    try:
        if args.self_test:
            g=build_gdb(3333,8)
            assert g.count('\nbreak *')==len(PROBES)
            assert 'PW_V104_HIT tag=A_STORE site=0x020D18A4' in g
            assert 'disable breakpoints' in g
            assert g.endswith('continue\n')
            assert 'PW_V104_HIT tag=C_STORE' in g
            attached=build_gdb(3333,8,already_connected=True)
            assert 'target remote' not in attached
            assert 'PW_V104_EXISTING_CONNECTION' in attached
            assert attached.count('\nbreak *')==len(PROBES)
            print('V10.4 synthetic manifest-generation test: PASS')
            return 0
        if not args.report or not args.output_dir:
            p.error('--report and --output-dir required unless --self-test')
        report=json.loads(args.report.read_text(encoding='utf-8'))
        validate(report)
        out=args.output_dir.resolve()
        out.mkdir(parents=True,exist_ok=True)
        (out/(BASENAME+'.gdb')).write_text(build_gdb(args.arm9_port,args.max_hits),
                                             encoding='utf-8',newline='\n')
        (out/(BASENAME+'_attached.gdb')).write_text(
            build_gdb(args.arm9_port,args.max_hits,already_connected=True),
            encoding='utf-8',newline='\n')
        (out/'README_v104_runtime_trace.txt').write_text(readme(args.arm9_port,args.max_hits),
                                                         encoding='utf-8')
        (out/'probe_manifest.json').write_text(json.dumps({
            'version':'v10.4','input_report':args.report.name,
            'game_codes':['IPKE','IPGE'],'arm9_port':args.arm9_port,
            'trace_max_hits':args.max_hits,
            'breakpoints':[{'tag':name,'address':f'0x{addr:08X}'} for name,addr in PROBES],
            'manual_connection_script':BASENAME+'_attached.gdb',
            'emulator_execution_proven':False,
            'real_DSi_execution_proven':False,
            'resident_wifi_verified':False,
            'rom_or_save_modified':False,
        },indent=2)+'\n',encoding='utf-8')
        print('V10.4 emulator-only trace files:',out)
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
