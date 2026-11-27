from pathlib import Path
import shutil,subprocess,sys
import os
root=Path(__file__).resolve().parent;out=root/'source';b=root/'build';b.mkdir(exist_ok=True)
def sdkpath(value):
 if os.name=='nt':
  if value.startswith('/opt/devkitpro') and Path('C:/devkitPro').exists():value='C:/devkitPro'+value[len('/opt/devkitpro'):]
  elif len(value)>3 and value[0]=='/' and value[2]=='/':value=value[1]+':'+value[2:]
 return Path(value)
dkp=sdkpath(os.environ.get('DEVKITPRO', 'C:/devkitPro' if os.name=='nt' else '/opt/devkitpro'))
arm=sdkpath(os.environ.get('DEVKITARM',str(dkp/'devkitARM')))
exe='.exe' if os.name=='nt' else ''
tool=arm/'bin';sdk=dkp/'libnds';calico=dkp/'calico'
arch=['-march=armv5te','-mtune=arm946e-s','-mthumb','-mthumb-interwork']
objects=[];log=[]
sources=sorted(out.glob('*.c'))+[root.parent/'bootstrap/retail/transport/walker_push_stream.c']
for p in sources:
 obj=b/(p.stem+'.o');objects.append(obj)
 cmd=[tool/('arm-none-eabi-gcc'+exe),'-std=gnu11','-DARM9','-D__NDS__','-O2','-g','-Wall','-Wextra','-ffunction-sections','-fdata-sections']+arch+['-I'+str(root/'compat'),'-I'+str(out),'-I'+str(root.parent/'bootstrap/retail/common/include'),'-I'+str(sdk/'include'),'-I'+str(calico/'include'),'-c',p,'-o',obj]
 r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True);log.append(p.name+'\n'+r.stdout+r.stderr)
 if r.returncode:print(log[-1]);(root/'build/build.log').write_text('\n'.join(log));sys.exit(1)
elf=root/'Pokewalker-NDS.elf'
cmd=[tool/('arm-none-eabi-gcc'+exe),'-specs='+str(calico/'share/ds9.specs')]+arch+['-L'+str(sdk/'lib'),'-L'+str(calico/'lib')]+objects+['-ldswifi9','-lfat','-lnds9','-lcalico_ds9','-lm','-Wl,--wrap=dvmDiscCacheCreate','-Wl,--gc-sections','-Wl,-Map='+str(b/'walker.map'),'-o',elf]
r=subprocess.run([str(x) for x in cmd],capture_output=True,text=True);log.append('link\n'+r.stdout+r.stderr);(root/'build/build.log').write_text('\n'.join(log),encoding='utf-8')
if r.returncode:print(log[-1]);sys.exit(1)
banner=root/'assets/pokewalker-icon.bmp'
if not banner.exists():
 raise SystemExit(f'Missing TWiLight Menu banner icon: {banner}')
subprocess.run([str(dkp/'tools/bin'/('ndstool'+exe)),'-c',str(root/'Pokewalker-NDS.nds'),'-9',str(elf),'-7',str(calico/'bin/ds7_maine.elf'),'-b',str(banner),'Pokewalker;Virtual walker companion;SD Transporter'],check=True)
print('NDS build:',root/'Pokewalker-NDS.nds',flush=True)
print('\n'.join(log)[-2200:])
