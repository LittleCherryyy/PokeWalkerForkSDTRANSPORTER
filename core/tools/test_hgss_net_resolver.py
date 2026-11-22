#!/usr/bin/env python3
# Synthetic test of the ARM signature strategy used by walker_hgss_net.c.
def bl(pc,target):
    off=(target-(pc+8))>>2
    return 0xEB000000 | (off & 0xFFFFFF)
def target(pc,w):
    imm=w&0xffffff
    if imm&0x800000: imm-=1<<24
    return pc+8+(imm<<2)
base=0x02000000
init=base+0x1000; auth=base+0x1400; conn=base+0x1800
for caller in [0x200,0x600]:
    words=[0]*32
    words[2]=0xE3A01002; words[3]=0xE3A02001; words[4]=0xE3A03014
    words[5]=bl(base+caller+5*4,init)
    words[6]=0xE3A00002; words[7]=bl(base+caller+7*4,auth); words[8]=bl(base+caller+8*4,conn)
    assert target(base+caller+5*4,words[5])==init
    assert target(base+caller+7*4,words[7])==auth
    assert target(base+caller+8*4,words[8])==conn
print('HGSS DWC synthetic signature: OK')
