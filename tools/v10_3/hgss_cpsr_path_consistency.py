#!/usr/bin/env python3
"""V10.3: CPSR-aware, bounded A32 path witness check for original HGSS ROMs.

Keeps all 16 possible N/Z/C/V combinations and enforces the same condition
flags until an instruction may update them. Calls and flag-updating
instructions conservatively make flags unknown; no RAM/register values are
read or inferred. The first path found is a *syntactic witness only*.
ROM validation comes from the unchanged V10.2 -> V9.2 verification chain.
Never writes original ROMs, game saves, bootstrap, DSi, or Android data.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
FORBIDDEN = {'.nds', '.sav', '.dsv', '.srm', '.walker', '.dat'}
MAX_STATES = 8192
MAX_PATH_STEPS = 320
ALL_FLAGS = range(16)


def hx(n): return f'0x{n:08X}'


def nzcv(flags):
    return ''.join(c if flags & bit else c.lower() for c,bit in
                   (('N',8), ('Z',4), ('C',2), ('V',1)))


def predicate(cond, flags):
    n,z,c,v = (bool(flags & x) for x in (8,4,2,1))
    return (z,not z,c,not c,n,not n,v,not v,c and not z,
            not c or z,n==v,n!=v,not z and n==v,z or n!=v,True,False)[cond]


def flags_write_model(word):
    """Report a possible flags reset, not actual arithmetic results.

    Unknown instruction classes conservatively reset the abstract flags,
    preserving *over-approximation* rather than inventing instruction output.
    """
    if (word >> 28) == 15:
        return True
    if ((word >> 25) & 7) == 5 or (word & 0x0ffffff0) in (0x012fff10, 0x012fff30):
        return (word & 0x0ffffff0) == 0x012fff30 or bool(word & (1<<24)) and ((word>>25)&7)==5
    cls = (word >> 25) & 7
    if cls in (2,3,4):
        return False  # ordinary word/byte LDR/STR or LDM/STM
    if cls in (6,7):
        return True  # coprocessor/SVC/unknown; some affect CPSR
    if cls == 1:
        return bool(word & (1<<20)) or ((word >> 21)&15) in (8,9,10,11)
    if cls == 0:
        if word & 0x90 == 0x90:
            return True # multiply/extra load-store may be flag-affecting
        # MRS/MSR/other unusual data-processing patterns can modify CPSR.
        if (word & 0x0db0f000) in (0x0120f000, 0x0320f000):
            return True
        return bool(word & (1<<20)) or ((word >> 21)&15) in (8,9,10,11)
    return True


def path(image, base, entry, goal, v102):
    if entry >= goal or goal-entry > v102.MAX_WINDOW_BYTES or entry%4 or goal%4:
        raise ValueError('invalid bounded PC range')
    if entry<base or goal+4>base+len(image):
        raise ValueError('PC range outside original ARM9')
    queue=deque((entry, f) for f in ALL_FLAGS)
    previous={(entry,f):None for f in ALL_FLAGS}
    blocked=Counter()
    dropped_edges=0
    possible_goal=None
    while queue:
        if len(previous)>MAX_STATES:
            raise ValueError('CPSR state search exceeded safety bound')
        pc,flags=queue.popleft()
        if pc==goal:
            possible_goal=(pc,flags)
            break
        word=v102.read_word(image,base,pc)
        cond=word>>28
        executed=predicate(cond,flags)
        successors,stop=v102.control_successors(word,pc)
        if stop:
            blocked[stop]+=1
        # V10.2 may return the same fallthrough PC for skipped vs executed
        # calls; which is taken is now constrained by the same NZCV flags.
        for next_pc,choice in successors:
            skipped=choice.startswith('conditional_') and choice.endswith('_skipped')
            if cond!=14 and choice != 'fallthrough' and ((skipped and executed) or (not skipped and not executed)):
                dropped_edges+=1
                continue
            if next_pc<entry or next_pc>goal or next_pc&3:
                dropped_edges+=1
                continue
            update_flags=executed and (flags_write_model(word) or 'assumed_' in choice)
            for next_flags in (ALL_FLAGS if update_flags else (flags,)):
                state=(next_pc,next_flags)
                if state not in previous:
                    previous[state]=((pc,flags),choice,update_flags)
                    queue.append(state)
    witness=[]
    if possible_goal is not None:
        state=possible_goal
        while previous[state] is not None:
            pred,choice,update_flags=previous[state]
            witness.append({'from_pc':hx(pred[0]), 'to_pc':hx(state[0]),
                            'choice':choice, 'incoming_NZCV':nzcv(pred[1]),
                            'outgoing_NZCV':nzcv(state[1]),
                            'flags_made_unknown_after_instruction':update_flags})
            state=pred
            if len(witness)>MAX_PATH_STEPS:
                raise ValueError('reconstructed witness exceeds bound')
        witness.reverse()
    return {
        'entry':hx(entry), 'target':hx(goal),
        'cpsr_consistent_under_overapproximate_flag_writes':possible_goal is not None,
        'witness':witness,
        'witness_contains_conditional_choice':any('conditional_' in x['choice'] for x in witness),
        'witness_assumes_a_call_returns':any('assumed_' in x['choice'] for x in witness),
        'witness_uses_unknown_flag_updates':any(x['flags_made_unknown_after_instruction'] for x in witness),
        'visited_pc_and_flag_states':len(previous),
        'rejected_inconsistent_or_outside_edges':dropped_edges,
        'terminal_or_unmodeled_classes':dict(sorted(blocked.items())),
        'actual_execution_proven':False,
        'actual_CPSR_values_known':False,
        'callee_saves_or_NitroSDK_ABI_proven':False,
    }


def analyze(rom,v102,v101,v96,v92):
    upstream=v102.analyze(rom,v101,v96,v92)
    meta,image=v92.v90.v75.v74.reconstruct(rom,include_runtime_image=True)
    if meta['arm9']['runtime_decompressed_sha256'] != upstream['arm9_runtime_sha256']:
        raise ValueError('original reconstructed ARM9 SHA256 mismatch')
    base=int(meta['arm9']['ram_load'],16)
    out={}
    for label,up in upstream['regions'].items():
        entry_rows=[]
        for old in up['entry_hypothesis_paths']:
            entry=int(old['entry'],16)
            targets={}
            for typ,pc_key in (('source','original_source_pc'), ('store','original_store_pc')):
                previous=old[typ+'_witness']
                new=path(image,base,entry,int(up[pc_key],16),v102)
                if new['cpsr_consistent_under_overapproximate_flag_writes'] and not previous['syntactically_reachable_under_unknown_flags']:
                    raise ValueError('V10.3 exceeded V10.2 permissive CFG on '+label+' '+typ)
                targets[typ]={
                    'v102_permissive_possible':previous['syntactically_reachable_under_unknown_flags'],
                    'v103_cpsr_consistent_possible':new['cpsr_consistent_under_overapproximate_flag_writes'],
                    'removed_by_CPSR_consistency':previous['syntactically_reachable_under_unknown_flags'] and not new['cpsr_consistent_under_overapproximate_flag_writes'],
                    'cpsr_witness':new
                }
            entry_rows.append({'entry':old['entry'],'targets':targets})
        out[label]=entry_rows
    return {'game_code':upstream['game_code'], 'rom_sha1':upstream['rom_sha1'],
            'arm9_runtime_sha256':upstream['arm9_runtime_sha256'],
            'regions':out}


def compare(hg,ss):
    by={hg['game_code']:hg,ss['game_code']:ss}
    if set(by)!={'IPKE','IPGE'}:
        raise ValueError('original USA Rev0 HGSS pair required')
    a,b=by['IPKE'],by['IPGE']
    match={key:a['regions'][key]==b['regions'][key] for key in a['regions']}
    return {'tool':'hgss-v10.3-NZCV-consistent-overapproximate-CFG',
            'heartgold':a,'soulsilver':b,
            'comparison':{'matching_regions':match,'all_match':all(match.values())},
            'limitations':[
                '16 NZCV combinations are enumerated, not inferred from live values',
                'Flag-modifying instructions reset flags to any combination; not actual ARM arithmetic',
                'Registers, RAM, IRQs, actual call execution, Thumb and overlays are not modeled',
                'A consistent symbolic path need not be feasible in the actual program',
                'The technique eliminates only some contradictory static CFG hypotheses'],
            'safe_to_create_resident_worker':False,
            'in_game_wifi_verified':False,
            'rom_or_save_modified':False,
            'next_gate':'If static NZCV consistency narrows paths, validate predicate inputs/callees before any resident Wi-Fi changes.'}


def self_test(v102):
    # ARM condition truth table.
    assert predicate(0,4) and not predicate(0,0)
    assert predicate(1,0) and not predicate(1,4)
    assert predicate(12,0) and not predicate(12,4)
    base=0x02000000
    # Permissive CFG sees a fictitious BEQ then BNE path, but Z cannot be
    # both 1 and 0 without a flags update. PC4/12 are forced returns.
    impossible=struct.pack('<6I',0x0a000000,0xe12fff1e,0x1a000001,
                           0xe12fff1e,0xe12fff1e,0xe1a00000)
    assert v102.witness(impossible,base,base,base+20)['syntactically_reachable_under_unknown_flags']
    assert not path(impossible,base,base,base+20,v102)['cpsr_consistent_under_overapproximate_flag_writes']
    # An intervening CMP may change flags; the witness is then possible.
    refreshed=struct.pack('<6I',0x0a000000,0xe12fff1e,0xe3500000,
                          0x1a000000,0xe12fff1e,0xe1a00000)
    assert path(refreshed,base,base,base+20,v102)['cpsr_consistent_under_overapproximate_flag_writes']
    # Skipping a conditional BXNE LR when Z=1 is syntactically possible.
    conditional=struct.pack('<3I',0x112fff1e,0xe1a00000,0xe1a00000)
    assert path(conditional,base,base,base+8,v102)['cpsr_consistent_under_overapproximate_flag_writes']
    # An unconditional return is never followed without a bypass.
    terminated=struct.pack('<3I',0xe12fff1e,0xe1a00000,0xe1a00000)
    assert not path(terminated,base,base,base+8,v102)['cpsr_consistent_under_overapproximate_flag_writes']
    print('V10.3 synthetic NZCV consistency tests: PASS')
    return 0


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise ValueError('missing local read-only upstream: '+str(path))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('heartgold',nargs='?',type=Path)
    p.add_argument('soulsilver',nargs='?',type=Path)
    p.add_argument('--rom-dir',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args(argv)
    try:
        v102=load('v103_v102',HERE.parent/'v10_2'/'hgss_cfg_path_probes.py')
        if args.self_test:
            return self_test(v102)
        v101=load('v103_v101',HERE.parent/'v10_1'/'hgss_function_boundary_literals.py')
        v96=load('v103_v96',HERE.parent/'v9_6'/'hgss_full_arm9_effective_xrefs.py')
        v92=load('v103_v92',HERE.parent/'v9_2'/'hgss_store_value_backtrace.py')
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError('choose --rom-dir or original ROM pair, not both')
            v95=load('v103_v95',HERE.parent/'v9_5'/'hgss_full_rom_index.py')
            hg,ss=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError('provide --rom-dir or original USA Rev0 ROM pair')
        if hg==ss or (args.output and (args.output.resolve() in (hg,ss) or
                                       args.output.suffix.lower() in FORBIDDEN)):
            raise ValueError('refusing original-ROM/save output overwrite')
        result=compare(analyze(hg,v102,v101,v96,v92),analyze(ss,v102,v101,v96,v92))
        payload=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding='utf-8')
            print('V10.3 read-only NZCV consistency report:',args.output)
            for region,rows in result['heartgold']['regions'].items():
                for item in rows:
                    print(region,item['entry'],
                          'source:',item['targets']['source']['v103_cpsr_consistent_possible'],
                          'store:',item['targets']['store']['v103_cpsr_consistent_possible'])
        else:
            print(payload,end='')
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
