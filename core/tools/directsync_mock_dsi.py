#!/usr/bin/env python3
"""Host-side mock for the V14 Direct DSi Sync wire format.

This does not emulate HGSS. It lets us verify the Android listener before the
ARM7 Wi-Fi bridge is ready. Usage:
  python directsync_mock_dsi.py <phone-ip> ping
  python directsync_mock_dsi.py <phone-ip> push file.walker SESSION TRAINER
  python directsync_mock_dsi.py <phone-ip> pull out.walker SESSION TRAINER
  python directsync_mock_dsi.py <phone-ip> confirm SESSION TRAINER CRC32HEX
"""
import socket,struct,sys,zlib
MAGIC=b'PWDSI001'; PORT=30821; HEADER=88
OPS={'push':1,'pull':2,'confirm':3,'ping':4}

def field(value,n):
    raw=value.encode('ascii')
    if len(raw)>n: raise SystemExit('field too long')
    return raw+b'\0'*(n-len(raw))

def frame(op,session='',trainer='',payload=b'',crc=None):
    if crc is None: crc=zlib.crc32(payload)&0xffffffff
    return MAGIC+bytes([1,op])+struct.pack('>HII',0,len(payload),crc)+field(session,32)+field(trainer,36)+payload

def read_exact(sock,n):
    out=b''
    while len(out)<n:
        b=sock.recv(n-len(out))
        if not b: raise EOFError('connection closed')
        out+=b
    return out

def receive(sock):
    h=read_exact(sock,HEADER)
    if h[:8]!=MAGIC or h[8]!=1: raise RuntimeError('bad response')
    op=h[9]; flags,length,crc=struct.unpack('>HII',h[10:20])
    session=h[20:52].split(b'\0',1)[0].decode();trainer=h[52:88].split(b'\0',1)[0].decode()
    body=read_exact(sock,length) if length else b''
    if body and (zlib.crc32(body)&0xffffffff)!=crc: raise RuntimeError('response CRC mismatch')
    return op,session,trainer,crc,body

def main():
    if len(sys.argv)<3: raise SystemExit(__doc__)
    host,cmd=sys.argv[1],sys.argv[2].lower();session=trainer='';payload=b'';crc=None
    if cmd=='push':
        if len(sys.argv)!=6: raise SystemExit(__doc__)
        payload=open(sys.argv[3],'rb').read();session=sys.argv[4];trainer=sys.argv[5]
    elif cmd=='pull':
        if len(sys.argv)!=6: raise SystemExit(__doc__)
        outfile=sys.argv[3];session=sys.argv[4];trainer=sys.argv[5]
    elif cmd=='confirm':
        if len(sys.argv)!=6: raise SystemExit(__doc__)
        session=sys.argv[3];trainer=sys.argv[4];crc=int(sys.argv[5],16)
    elif cmd=='ping': pass
    else: raise SystemExit(__doc__)
    with socket.create_connection((host,PORT),10) as s:
        s.sendall(frame(OPS[cmd],session,trainer,payload,crc))
        op,rs,rt,rc,body=receive(s)
    if op==0x7f:
        raise SystemExit('ERROR: '+body.decode('utf-8','replace'))
    print('OK op=%02x session=%s trainer=%s crc=%08x bytes=%d'%(op,rs,rt,rc,len(body)))
    if cmd=='pull':
        open(outfile,'wb').write(body);print('saved',outfile)

if __name__=='__main__': main()
