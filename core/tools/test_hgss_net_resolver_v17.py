#!/usr/bin/env python3

def bl(pc,target):
    off=(target-(pc+8))>>2
    return 0xEB000000 | (off & 0xFFFFFF)

def target(pc,w):
    imm=w&0xffffff
    if imm&0x800000: imm-=1<<24
    return pc+8+(imm<<2)

base=0x02000000
init=base+0x1000; auth=base+0x1400; conn=base+0x1800
check=base+0x1c00; status=base+0x2000; process=base+0x2400; cleanup=base+0x2800
image=[0]*0x3000

for caller in [0x200,0x600]:
    i=caller//4
    image[i+2]=0xE3A01002; image[i+3]=0xE3A02001; image[i+4]=0xE3A03014
    image[i+5]=bl(base+(i+5)*4,init)
    image[i+6]=0xE3A00002; image[i+7]=bl(base+(i+7)*4,auth); image[i+8]=bl(base+(i+8)*4,conn)
    image[i+20]=bl(base+(i+20)*4,check)
    image[i+26]=bl(base+(i+26)*4,status)
    image[i+34]=bl(base+(i+34)*4,process)

# synthetic GetInetStatus body: retry path cleanup -> InitInetEx
si=(status-base)//4
image[si+40]=bl(base+(si+40)*4,cleanup)
image[si+44]=bl(base+(si+44)*4,init)

# sanity for all branches
for pc,target_addr in [
    (base+0x200+5*4,init),(base+0x200+20*4,check),
    (base+0x200+26*4,status),(base+0x200+34*4,process),
    (base+(si+40)*4,cleanup),(base+(si+44)*4,init)]:
    idx=(pc-base)//4
    assert target(pc,image[idx])==target_addr

# Mirrors the conservative relationships used by C resolver.
for caller in [0x200,0x600]:
    i=caller//4
    assert target(base+(i+8)*4,image[i+8])==conn
    seen=[target(base+(i+k)*4,image[i+k]) for k in (20,26,34)]
    assert seen==[check,status,process]
assert target(base+(si+40)*4,image[si+40])==cleanup
assert target(base+(si+44)*4,image[si+44])==init
print('HGSS DWC V17 connection-state signatures: OK')
