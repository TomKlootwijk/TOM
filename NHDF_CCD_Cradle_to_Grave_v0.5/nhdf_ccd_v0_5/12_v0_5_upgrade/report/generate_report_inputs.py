from __future__ import annotations
import json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'report'
s=json.loads((ROOT/'validation/validation_summary.json').read_text())

def fmt(x, digits=3):
    if x is None: return 'n/a'
    if isinstance(x,int): return f'{x:,}'
    if abs(x)>=1000: return f'{x:,.0f}'
    if x==0: return '0'
    if abs(x)<1e-3: return f'{x:.3e}'
    return f'{x:.{digits}f}'

def esc(x):
    return str(x).replace('\\','\\textbackslash{}').replace('&','\\&').replace('%','\\%').replace('$','\\$').replace('#','\\#').replace('_','\\_').replace('{','\\{').replace('}','\\}')

log=(ROOT/'validation/run_all.log').read_text(errors='replace')
m=re.search(r'Ran\s+(\d+)\s+tests',log)
tests=int(m.group(1)) if m else 0
files=[p for p in ROOT.rglob('*') if p.is_file()]
py_lines=sum(len(p.read_text(errors='ignore').splitlines()) for p in files if p.suffix=='.py')
cpp_lines=sum(len(p.read_text(errors='ignore').splitlines()) for p in files if p.suffix in {'.cpp','.hpp','.cu'})

vf=s['synthetic']['vf']; ee=s['synthetic']['ee']; ext=s['external_corpus']
macros={
 'ReleaseDate':'2026-09-01',
 'PythonTests':tests,
 'ReleaseFiles':len(files),
 'PythonLines':py_lines,
 'NativeLines':cpp_lines,
 'SyntheticVFQueries':fmt(vf['queries']),
 'SyntheticEEQueries':fmt(ee['queries']),
 'SyntheticTotalQueries':fmt(vf['queries']+ee['queries']),
 'SyntheticVFErrors':fmt(vf['errors']),
 'SyntheticEEErrors':fmt(ee['errors']),
 'SyntheticVFEndpointMisses':fmt(vf['endpoint_missed_truth_hits']),
 'SyntheticEEEndpointMisses':fmt(ee['endpoint_missed_truth_hits']),
 'SyntheticVFMaxTOI':fmt(vf['max_toi_abs_error']),
 'SyntheticEEMaxTOI':fmt(ee['max_toi_abs_error']),
 'SyntheticVFThroughput':fmt(vf['queries_per_second']),
 'SyntheticEEThroughput':fmt(ee['queries_per_second']),
 'ExternalVFQueries':fmt(ext['vertex_face']['corpus']['queries']),
 'ExternalEEQueries':fmt(ext['edge_edge']['corpus']['queries']),
 'ExternalVFTotalPositive':fmt(ext['vertex_face']['corpus']['positive']),
 'ExternalVFAccuracy':('n/a' if ext['vertex_face']['evaluation']['conclusive_accuracy'] is None else f"{100*ext['vertex_face']['evaluation']['conclusive_accuracy']:.2f}\\%"),
 'ExternalEEAccuracy':('n/a' if ext['edge_edge']['evaluation']['conclusive_accuracy'] is None else f"{100*ext['edge_edge']['evaluation']['conclusive_accuracy']:.2f}\\%"),
 'ExternalVFInconclusive':fmt(ext['vertex_face']['evaluation']['inconclusive']),
 'ExternalEEInconclusive':fmt(ext['edge_edge']['evaluation']['inconclusive']),
 'RigidSamples':fmt(s['rigid_bound_audit']['samples']),
 'RigidViolations':fmt(s['rigid_bound_audit']['violations']),
 'RigidMinSlack':fmt(s['rigid_bound_audit']['minimum_slack']),
 'ResponseSamples':fmt(s['response_audit']['samples']),
 'ResponseMomentumError':fmt(s['response_audit']['max_momentum_error']),
 'ResponseEnergyFailures':fmt(s['response_audit']['energy_gain_failures']),
 'ResponseClosingFailures':fmt(s['response_audit']['post_impulse_closing_failures']),
 'EventContacts':fmt(s['event_grouping']['contacts']),
 'EventGroups':fmt(s['event_grouping']['events']),
 'EventThroughput':fmt(s['event_grouping']['contacts_per_second']),
 'PythonVersion':esc(s['environment']['python'].split()[0]),
 'NumpyVersion':esc(s['environment']['numpy']),
 'PlatformString':esc(s['environment']['platform']),
}
lines=['% Auto-generated from validation/validation_summary.json']
for k,v in macros.items():
    lines.append(f'\\newcommand{{\\{k}}}{{{v}}}')
(REPORT/'generated_values.tex').write_text('\n'.join(lines)+'\n')

# external outcome rows
rows=[]
for label,key in [('Vertex--face','vertex_face'),('Edge--edge','edge_edge')]:
    e=ext[key]['evaluation']
    acc = 'n/a' if e['conclusive_accuracy'] is None else f"{100*e['conclusive_accuracy']:.2f}\\%"
    rows.append(f"{label} & {e['total']:,} & {e['true_positive']:,} & {e['true_negative']:,} & {e['false_positive']:,} & {e['false_negative']:,} & {e['inconclusive']:,} & {acc} \\\")
(REPORT/'external_results_rows.tex').write_text('\n'.join(rows)+'\n')

# status rows
status_keys=sorted(set(ext['vertex_face']['evaluation']['status_counts'])|set(ext['edge_edge']['evaluation']['status_counts']))
rows=[]
for st in status_keys:
    rows.append(f"\\texttt{{{esc(st)}}} & {ext['vertex_face']['evaluation']['status_counts'].get(st,0):,} & {ext['edge_edge']['evaluation']['status_counts'].get(st,0):,} \\\\")
(REPORT/'external_status_rows.tex').write_text('\n'.join(rows)+'\n')

# file inventory by extension
groups={}
for p in files:
    rel=p.relative_to(ROOT)
    suffix=p.suffix.lower() or '[none]'
    groups.setdefault(suffix,[]).append(rel)
rows=[]
for suffix,ps in sorted(groups.items(),key=lambda kv:(-len(kv[1]),kv[0])):
    rows.append(f"\\texttt{{{esc(suffix)}}} & {len(ps):,} \\\\")
(REPORT/'file_inventory_rows.tex').write_text('\n'.join(rows)+'\n')
