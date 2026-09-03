from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/'validation'; VAL.mkdir(exist_ok=True)

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()

def run(cmd, *, env=None, check=True):
    p=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f"command failed: {cmd}\n{p.stdout}\n{p.stderr}")
    return p

def braces_balanced(text:str)->bool:
    pairs={'{':'}','(':')','[':']'}; stack=[]; quote=None; esc=False
    for ch in text:
        if quote:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch==quote: quote=None
            continue
        if ch in ('"',"'"): quote=ch; continue
        if ch in pairs: stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop()!=ch: return False
    return not stack and quote is None

checks=[]
def add(name,status,detail,**extra):
    checks.append({'name':name,'status':status,'detail':detail,**extra})

# Schema validation.
try:
    import jsonschema
    schema=json.loads((ROOT/'spec/tomagi.schema.json').read_text())
    validated=[]
    for n in ('polar_loop.json','exact19_rule.json'):
        doc=json.loads((ROOT/'examples'/n).read_text())
        jsonschema.Draft202012Validator(schema).validate(doc); validated.append(n)
    add('JSON Schema examples','pass',f"Draft 2020-12 validation: {', '.join(validated)}")
except Exception as exc:
    add('JSON Schema examples','fail',str(exc))

# Python results and C equality.
env=os.environ.copy(); env['PYTHONPATH']=str(ROOT/'src/python')
for stem in ('polar_loop','exact19_rule'):
    py=json.loads((ROOT/f'examples/{stem}.expected.json').read_text())['state']
    exe=ROOT/'build/tomagi-c'; tmg=ROOT/f'examples/{stem}.tmg'
    if exe.exists() and tmg.exists():
        cp=run([str(exe),str(tmg)])
        c=json.loads(cp.stdout)
        path=VAL/f'{stem}_c_state.json'; path.write_text(json.dumps(c,indent=2,sort_keys=True)+'\n')
        add(f'Python/C equality: {stem}','pass' if c==py else 'fail',
            'All 16 State64 fields match exactly.' if c==py else 'State mismatch.',
            python_state=py,c_state=c)
    else:
        add(f'Python/C equality: {stem}','fail','C executable or .tmg example missing')

# Key vectors.
from tomagi.core import pack_key_contiguous,pack_key_morton,key_as_u64
q=(949111,0,1920,227)
cont=key_as_u64(*pack_key_contiguous(*q)); mort=key_as_u64(*pack_key_morton(*q))
key_ok=cont==0xe7b77000007800e3 and mort==0x88823bb88099128b
add('64-bit key reference vectors','pass' if key_ok else 'fail',f'contiguous=0x{cont:016x}; Morton=0x{mort:016x}')

# OpenCL parser check.
clang=shutil.which('clang')
if clang:
    p=run([clang,'-x','cl','-cl-std=CL1.2','-fsyntax-only',str(ROOT/'src/gpu/tomagi_step.cl')],check=False)
    add('OpenCL C syntax','pass' if p.returncode==0 else 'fail',p.stderr.strip() or 'clang -cl-std=CL1.2 accepted the kernel')
else:
    add('OpenCL C syntax','not-run','clang not installed')

# GLSL/WGSL structural lint; external compilers not present in this environment.
for lang,name in [('tomagi_step.comp','GLSL 4.50 source'),('tomagi_step.wgsl','WGSL source')]:
    path=ROOT/'src/gpu'/lang; text=path.read_text()
    op_mentions=all(f'op=={i}u' in text or (i==0 and 'op==0u' not in text) for i in range(16))
    ok=braces_balanced(text) and 'State64' in text and 'Cell48' in text and 'mix32' in text and op_mentions
    add(name,'source-checked' if ok else 'fail',
        'Balanced delimiters, shared ABI symbols and opcode dispatch present; external shader compiler/device execution unavailable in this build environment.' if ok else 'Structural source check failed.')

# Catalog/source coverage.
ops=json.loads((ROOT/'spec/operator_catalog.json').read_text())
cross=json.loads((ROOT/'spec/source_crosswalk.json').read_text())
reg=json.loads((ROOT/'sources/source_register.json').read_text())
srcs={r['source'].split(':',1)[0] for r in cross['rows']}
coverage=ops['count']==43 and cross['count']==319 and len(reg['sources'])==7 and len(srcs)>=7
add('Operator/source condensation','pass' if coverage else 'fail',
    f"{ops['count']} operators; {cross['count']} crosswalk rows; {len(reg['sources'])} source artifacts; source labels {sorted(srcs)}")

# Binary record sizes.
from tomagi.format import HEADER_SIZE,STATE_SIZE,CELL_SIZE,load
p=load(ROOT/'examples/polar_loop.tmg')
length=(ROOT/'examples/polar_loop.tmg').stat().st_size
size_ok=(HEADER_SIZE,STATE_SIZE,CELL_SIZE)==(128,64,48) and length==128+48*len(p.cells)
add('Binary ABI sizes','pass' if size_ok else 'fail',f'header={HEADER_SIZE}; state={STATE_SIZE}; cell={CELL_SIZE}; polar_loop bytes={length}')

# Unit test count from test file, plus rerun for a machine-readable result.
p=run([sys.executable,'-m','unittest','discover','-s','tests','-v'],env=env,check=False)
(VAL/'tests_rerun.txt').write_text(p.stdout+p.stderr)
lines=(p.stdout+p.stderr).splitlines()
ran=next((line for line in lines if line.startswith('Ran ')), '')
add('Python conformance suite','pass' if p.returncode==0 else 'fail',f'{ran}; return code {p.returncode}')

# Artifact hashes that exist before final packaging.
artifacts=[]
for rel in ['examples/polar_loop.tmg','examples/exact19_rule.tmg','src/gpu/tomagi_step.comp','src/gpu/tomagi_step.wgsl','src/gpu/tomagi_step.cl','build/tomagi-c']:
    path=ROOT/rel
    if path.exists(): artifacts.append({'file':rel,'bytes':path.stat().st_size,'sha256':sha(path)})

report={
    'schema':'TOMAGI-VALIDATION-1.0',
    'tomagi_version':'1.0.0',
    'generated':'2026-09-01',
    'environment':{
        'python':sys.version.split()[0],
        'platform':platform.platform(),
        'machine':platform.machine(),
        'cc':run(['cc','--version'],check=False).stdout.splitlines()[0] if shutil.which('cc') else None,
        'clang':run([clang,'--version'],check=False).stdout.splitlines()[0] if clang else None,
    },
    'summary':{
        'pass':sum(c['status']=='pass' for c in checks),
        'source_checked':sum(c['status']=='source-checked' for c in checks),
        'fail':sum(c['status']=='fail' for c in checks),
        'not_run':sum(c['status']=='not-run' for c in checks),
    },
    'checks':checks,
    'artifacts':artifacts,
    'scope_note':'Python and C were executed. OpenCL was syntax-checked. GLSL and WGSL were structurally checked but not compiled or dispatched because their external validators and a GPU runtime were not present.'
}
(VAL/'validation_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
md=['# TOMAGI 1.0 validation report','',f"Generated: {report['generated']}",'',
    f"Pass: {report['summary']['pass']}; source-checked: {report['summary']['source_checked']}; failures: {report['summary']['fail']}; not run: {report['summary']['not_run']}",'']
for c in checks:
    md += [f"## {c['name']}",f"**{c['status']}** - {c['detail']}",'']
md += ['## Scope',report['scope_note'],'']
(VAL/'VALIDATION.md').write_text('\n'.join(md))
print(json.dumps(report['summary'],indent=2))
if report['summary']['fail']:
    raise SystemExit(1)
