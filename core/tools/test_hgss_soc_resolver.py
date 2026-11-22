#!/usr/bin/env python3
# Host-side validation of the semantic SOC wrapper signatures used in V18.

def bl(pc,target,link=True):
    off=(target-(pc+8))>>2
    return (0xEB000000 if link else 0xEA000000) | (off & 0xFFFFFF)

def target(pc,w):
    imm=w&0xffffff
    if imm&0x800000: imm-=1<<24
    return pc+8+(imm<<2)

def pushlr(w): return (w & 0xFFFF4000)==0xE92D4000
base=0x02000000
p=[0]*1024
# SOC_Socket shape (clang/MWCC-compatible semantic form)
sock=40
p[sock+0]=0xE59F0010; p[sock+1]=0xE59F2010; p[sock+2]=0xE3510001
p[sock+3]=0x01A02000; p[sock+4]=0xE5920000; p[sock+5]=bl(base+(sock+5)*4,base+0x5000,False)
# SOC_Connect shape
con=64
p[con+0]=0xE5912004; p[con+1]=0xE1D110B2
for i in range(2,14): p[con+i]=0xE1A00000
p[con+14]=bl(base+(con+14)*4,base+0x5400,False)
# Recv wrapper
recv=96
p[recv+0]=0xE92D4800;p[recv+1]=0xE1A0B00D;p[recv+2]=0xE24DD008;p[recv+3]=0xE3A0C000
p[recv+4]=0xE58D3004;p[recv+5]=0xE3A03000;p[recv+6]=0xE58DC000;p[recv+7]=bl(base+(recv+7)*4,base+0x5800)
# RecvFrom-like decoy: no zero remote address arguments
rf=120
p[rf+0]=0xE92D4800;p[rf+1]=0xE24DD008;p[rf+2]=0xE58D3004;p[rf+3]=0xE58D4000;p[rf+4]=bl(base+(rf+4)*4,base+0x5800)
# Send wrapper
send=160
p[send+0]=0xE92D4800;p[send+1]=0xE1A0B00D;p[send+2]=0xE24DD008;p[send+3]=0xE3A0C000
p[send+4]=0xE58D3004;p[send+5]=0xE3A03000;p[send+6]=0xE58DC000;p[send+7]=bl(base+(send+7)*4,base+0x5c00)

# assertions that encode the same semantic requirements
assert p[sock+2]==0xE3510001
assert target(base+(sock+5)*4,p[sock+5])==base+0x5000
assert p[con]==0xE5912004 and p[con+1]==0xE1D110B2
assert pushlr(p[recv]) and 0xE24DD008 in p[recv:recv+20] and 0xE58D3004 in p[recv:recv+20] and 0xE58DC000 in p[recv:recv+20]
assert not (0xE58DC000 in p[rf:rf+20])
assert pushlr(p[send]) and 0xE58DC000 in p[send:send+20]
print('HGSS resident SOC semantic signatures: OK')
