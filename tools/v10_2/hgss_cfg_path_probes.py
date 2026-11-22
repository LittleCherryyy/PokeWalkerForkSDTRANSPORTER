#!/usr/bin/env python3
"""V10.2: conservative bounded A32 control-flow witnesses for HGSS originals.

The original ROM is reconstructed read-only through V9.2 and checked against
V9.6/V10.1. Distinguishes conditional returns from unconditional returns,
and explores bypass branches without assuming CPSR values or game execution.
An abstract path is only a syntactic possibility, NOT evidence of execution,
function ownership, scheduler ABI, Wi-Fi availability or safe thread setup.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import importlib.util
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
FORBIDDEN = {'.nds', '.sav', '.dsv', '.srm', '.walker', '.dat'}
MAX_WINDOW_BYTES = 0x500
MAX_VISITED_PCS = 512
MAX_PATH_STEPS = 192

REGIONS = {
    'A': {'old_entry': 0x020D1808, 'candidate_entries': [0x020D1808, 0x020D1868],
          'source': 0x020D189C, 'store': 0x020D18A4,
          'return_candidate': 0x020D1898, 'bypass_branch': None},
    'B': {'old_entry': 0x020D1FA0, 'candidate_entries': [0x020D1FA0],
          'source': 0x020D202C, 'store': 0x020D2034,
          'return_candidate': 0x020D2018,
          'bypass_branch': {'source': 0x020D200C, 'destination': 0x020D201C}},
    'C': {'old_entry': 0x020D2058, 'candidate_entries': [0x020D2058],
          'source': 0x020D20CC, 'store': 0x020D20D4,
          'return_candidate': 0x020D20AC,
          'bypass_branch': {'source': 0x020D209C, 'destination': 0x020D20B0}},
}

def hx(value: int) -> str:
    return f'0x{value:08X}'

def read_word(image: bytes, base: int, pc: int) -> int:
    offset = pc-base
    if pc % 4 or offset < 0 or offset+4 > len(image):
        raise ValueError(f'outside original ARM9: {hx(pc)}')
    return struct.unpack_from('<I', image, offset)[0]

def branch(word: int, pc: int):
    if word >> 28 == 15 or ((word >> 25) & 7) != 5:
        return None
    off = word & 0xffffff
    if off & 0x800000:
        off -= 1 << 24
    return {'kind': 'BL' if word & (1 << 24) else 'B',
            'target': (pc + 8 + (off << 2)) & 0xffffffff,
            'conditional': word >> 28 != 14}

def control_successors(word: int, pc: int):
    """Return (successor, edge-label) and terminal labels.

    Conditional instructions may execute or be skipped. No flags or paths are
    assumed. A BL return is only a hypothesis; we don't traverse callees.
    """
    cond = word >> 28
    if cond == 15:
        return [], 'unmodeled_NV_or_BLX_immediate'
    conditional = cond != 14
    b = branch(word, pc)
    if b:
        if b['kind'] == 'BL':
            edges = [(pc+4, 'assumed_call_returns')]
            if conditional:
                edges.append((pc+4, 'conditional_BL_skipped'))
            return edges, 'call_target_not_followed'
        edges = [(b['target'], 'conditional_B_taken' if conditional else 'unconditional_B')]
        if conditional:
            edges.append((pc+4, 'conditional_B_skipped'))
        return edges, None
    # BX / BLX register, avoiding a false fallthrough through a return.
    if (word & 0x0ffffff0) in (0x012fff10, 0x012fff30):
        kind = 'BLX_register' if (word & 0x0ffffff0) == 0x012fff30 else 'BX_register'
        if kind == 'BLX_register':
            edges = [(pc+4, 'assumed_indirect_call_returns')]
        else:
            edges = []
        if conditional:
            edges.append((pc+4, 'conditional_'+kind+'_skipped'))
        return edges, kind+'_not_resolved'
    # LDM/POP loading PC is a dynamic branch (usually a return).
    if ((word >> 25) & 7) == 4 and word & (1 << 20) and word & (1 << 15):
        return ([(pc+4, 'conditional_LDM_PC_skipped')] if conditional else []), 'LDM_PC_unknown'
    # LDR PC with A32 single-data-transfer encoding.
    if ((word >> 26) & 3) == 1 and word & (1 << 20) and ((word >> 12) & 15) == 15:
        return ([(pc+4, 'conditional_LDR_PC_skipped')] if conditional else []), 'LDR_PC_unknown'
    # Data-processing instructions that target PC, excluding comparisons and tests.
    if ((word >> 26) & 3) == 0 and ((word >> 25) & 7) not in (4,5):
        op = (word >> 21) & 15
        if op not in (8,9,10,11) and ((word >> 12) & 15) == 15:
            return ([(pc+4, 'conditional_PC_write_skipped')] if conditional else []), 'PC_write_unknown'
    # SVC is an exceptional transfer, not an ordinary call returning predictably.
    if (word >> 24) & 15 == 15:
        return ([(pc+4, 'conditional_SVC_skipped')] if conditional else []), 'SVC_unknown'
    return [(pc+4,'fallthrough')], None

def witness(image: bytes, base: int, entry: int, goal: int):
    if entry >= goal or (goal-entry) > MAX_WINDOW_BYTES or entry % 4 or goal % 4:
        raise ValueError('invalid bounded witness interval')
    end_of_image = base + len(image)
    if not base <= entry < goal < end_of_image:
        raise ValueError('witness interval outside ARM9')
    q = deque([entry])
    previous = {entry: None}
    stops = defaultdict(int)
    edges_outside = 0
    while q:
        if len(previous) > MAX_VISITED_PCS:
            raise ValueError('bounded CFG unexpectedly large')
        pc = q.popleft()
        if pc == goal:
            break
        successors, stop = control_successors(read_word(image,base,pc), pc)
        if stop:
            stops[stop] += 1
        for dest, label in successors:
            if dest % 4 or dest < entry or dest > goal:
                edges_outside += 1
                continue
            if dest not in previous:
                previous[dest] = (pc,label)
                q.append(dest)
    reached = goal in previous
    path = []
    if reached:
        pc = goal
        while previous[pc] is not None:
            origin,label = previous[pc]
            path.append({'from_pc':hx(origin),'to_pc':hx(pc),'choice':label})
            pc = origin
            if len(path)>MAX_PATH_STEPS:
                raise ValueError('path exceeded bounded step limit')
        path.reverse()
    return {
        'entry_hypothesis': hx(entry),
        'target_pc': hx(goal),
        'syntactically_reachable_under_unknown_flags': reached,
        'one_candidate_path': path,
        'potential_return_or_unmodeled_exits': dict(sorted(stops.items())),
        'ignored_edges_outside_bounded_interval': edges_outside,
        'visited_possible_instruction_pcs': len(previous),
        'path_requires_unproved_cpsr_assumptions':any(
            ('conditional' in edge['choice']) for edge in path),
        'path_requires_unproved_call_return':any(
            'assumed_' in edge['choice'] for edge in path),
        'actual_execution_proven': False,
        'function_ownership_proven': False
    }

def branch_and_return_checks(image: bytes, base: int, record: dict):
    ret_pc=record['return_candidate']
    ret=read_word(image,base,ret_pc)
    check={'return_pc':hx(ret_pc), 'condition_code':ret>>28,
           'is_unconditional':(ret>>28)==14}
    if (ret&0x0ffffff0)==0x012fff10:
        check['return_syntax']='BX_register'
        check['return_register']='lr' if ret&15==14 else 'other'
    elif ((ret>>25)&7)==4 and (ret&(1<<20)) and (ret&(1<<15)):
        check['return_syntax']='LDM_loading_PC'
    else:
        check['return_syntax']='not_a_known_return_pattern'
    check['bypass_branch'] = None
    if record['bypass_branch']:
        src=record['bypass_branch']['source']
        expected=record['bypass_branch']['destination']
        b=branch(read_word(image,base,src),src)
        check['bypass_branch']={
            'branch_pc':hx(src),
            'observed_target_pc':hx(b['target']) if b else None,
            'expected_from_v101':hx(expected),
            'branch_target_matches_v101':bool(b and b['target']==expected),
            'conditional':b['conditional'] if b else None,
            'crosses_return_location':bool(b and src<ret_pc<b['target']),
            'runtime_branch_execution_proven':False,
        }
    return check

def direct_callers(image: bytes, base: int, entries: set[int]):
    result={entry:[] for entry in entries}
    for pos in range(0,len(image)-3,4):
        pc=base+pos
        b=branch(struct.unpack_from('<I',image,pos)[0],pc)
        if b and b['kind']=='BL' and b['target'] in result:
            result[b['target']].append(hx(pc))
    return result

def analyze(path: Path, v101, v96, v92):
    verified=v96.analyze(path,v92)
    boundary=v101.analyze(path,v96,v92)
    meta,image=v92.v90.v75.v74.reconstruct(path,include_runtime_image=True)
    if meta['arm9']['runtime_decompressed_sha256'] != verified['arm9_runtime_sha256']:
        raise ValueError('original ARM9 digest mismatch')
    base=int(meta['arm9']['ram_load'],16)
    all_entries=set(entry for rec in REGIONS.values() for entry in rec['candidate_entries'])
    caller_index=direct_callers(image,base,all_entries)
    regions={}
    for label,record in REGIONS.items():
        old=boundary['regions'][label]
        if int(old['original_source_pc'],16)!=record['source'] or \
           int(old['original_store_pc'],16)!=record['store']:
            raise ValueError('V10.1 anchor mismatch in '+label)
        checks=branch_and_return_checks(image,base,record)
        results=[]
        for entry in record['candidate_entries']:
            results.append({
                'entry':hx(entry),
                'direct_BL_candidate_callsite_pcs':caller_index[entry][:32],
                'callsite_list_truncated':len(caller_index[entry])>32,
                'direct_BL_candidate_callsite_count':len(caller_index[entry]),
                'source_witness':witness(image,base,entry,record['source']),
                'store_witness':witness(image,base,entry,record['store'])
            })
        regions[label]={
            'previous_entry_guess':hx(record['old_entry']),
            'original_source_pc':hx(record['source']),
            'original_store_pc':hx(record['store']),
            'return_and_bypass_syntax':checks,
            'entry_hypothesis_paths':results,
        }
    return {'game_code':verified['game_code'],'rom_sha1':verified['rom_sha1'],
            'arm9_runtime_sha256':verified['arm9_runtime_sha256'],
            'regions':regions}

def comparison(hg,ss):
    by={hg['game_code']:hg,ss['game_code']:ss}
    if set(by)!={'IPKE','IPGE'}:
        raise ValueError('requires original US Rev0 HeartGold/SoulSilver pair')
    a,b=by['IPKE'],by['IPGE']
    equivalent={label:a['regions'][label]==b['regions'][label] for label in REGIONS}
    return {'tool':'hgss-v10.2-A32-bounded-return-bypass-path-witnesses',
            'heartgold':a,'soulsilver':b,
            'comparison':{'matching_abstract_region_results':equivalent,
                          'all_equal':all(equivalent.values())},
            'limitations':['CPSR conditions are not modeled; any static witness may be infeasible',
                           'BL/BLX assumed to return without traversing callees',
                           'Only A32 immediate branches and selected PC writes are modeled',
                           'Unknown indirect branches, Thumb, overlays not followed',
                           'Candidate function entries are not verified',
                           'No actual code execution, thread ABI, live registers, or Wi-Fi ownership proved'],
            'safe_to_create_resident_worker':False,
            'in_game_wifi_demonstrated':False,
            'rom_or_save_modified':False,
            'next_gate':'Review bounded witness paths and register origins without mistaking conditional returns for unconditional function boundaries.'}

def self_test():
    base=0x02000000
    # Conditional BXNE LR is not a compulsory return: it can be skipped.
    a=struct.pack('<4I',0x112fff1e,0xe1a00000,0xe1a00000,0xe1a00000)
    result=witness(a,base,base,base+8)
    assert result['syntactically_reachable_under_unknown_flags']
    assert result['one_candidate_path'][0]['choice']=='conditional_BX_register_skipped'
    # A conditional BNE goes around an unconditional LDM{PC} return.
    b=struct.pack('<4I',0x1a000000,0xe8bd8000,0xe1a00000,0xe1a00000)
    assert branch(0x1a000000,base)['target']==base+8
    result=witness(b,base,base,base+8)
    assert result['syntactically_reachable_under_unknown_flags']
    assert result['one_candidate_path'][0]['choice']=='conditional_B_taken'
    # An unconditional return stops all forward paths.
    c=struct.pack('<4I',0xe8bd8000,0xe1a00000,0xe1a00000,0xe1a00000)
    assert not witness(c,base,base,base+8)['syntactically_reachable_under_unknown_flags']
    # Test bypass branch validation without needing original copyrighted ROM.
    rec={'return_candidate':base+4,
         'bypass_branch':{'source':base,'destination':base+8}}
    check=branch_and_return_checks(b,base,rec)
    assert check['is_unconditional']
    assert check['bypass_branch']['branch_target_matches_v101']
    assert check['bypass_branch']['crosses_return_location']
    print('V10.2 synthetic CFG return-bypass tests: PASS')
    return 0

def load(alias: str, path: Path):
    spec=importlib.util.spec_from_file_location(alias,path)
    if spec is None or spec.loader is None:
        raise ValueError('missing original-ROM dependency: '+str(path))
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('heartgold',nargs='?',type=Path)
    p.add_argument('soulsilver',nargs='?',type=Path)
    p.add_argument('--rom-dir',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--self-test',action='store_true')
    args=p.parse_args(argv)
    try:
        if args.self_test:
            return self_test()
        v101=load('v102_v101',HERE.parent/'v10_1'/'hgss_function_boundary_literals.py')
        v96=load('v102_v96',HERE.parent/'v9_6'/'hgss_full_arm9_effective_xrefs.py')
        v92=load('v102_v92',HERE.parent/'v9_2'/'hgss_store_value_backtrace.py')
        if args.rom_dir:
            if args.heartgold or args.soulsilver:
                raise ValueError('choose --rom-dir OR two files')
            v95=load('v102_v95',HERE.parent/'v9_5'/'hgss_full_rom_index.py')
            hg,ss=v95.discover_roms(args.rom_dir)
        elif args.heartgold and args.soulsilver:
            hg,ss=args.heartgold.resolve(),args.soulsilver.resolve()
        else:
            raise ValueError('provide original ROM pair or --rom-dir')
        if hg==ss or (args.output and (args.output.resolve() in (hg,ss) or
                                       args.output.suffix.lower() in FORBIDDEN)):
            raise ValueError('refusing duplicate ROM or ROM/save output overwrite')
        result=comparison(analyze(hg,v101,v96,v92),analyze(ss,v101,v96,v92))
        payload=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(payload,encoding='utf-8')
            print('V10.2 read-only CFG report:',args.output)
            for label,record in result['heartgold']['regions'].items():
                for hypothesis in record['entry_hypothesis_paths']:
                    print(label,hypothesis['entry'],
                          'source:',hypothesis['source_witness']['syntactically_reachable_under_unknown_flags'],
                          'store:',hypothesis['store_witness']['syntactically_reachable_under_unknown_flags'])
        else:
            print(payload,end='')
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print('ERROR:',exc,file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
