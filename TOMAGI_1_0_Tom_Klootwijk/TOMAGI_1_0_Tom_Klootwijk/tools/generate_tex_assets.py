from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report/generated'; OUT.mkdir(parents=True,exist_ok=True)

def esc(x: object) -> str:
    s=str(x)
    repl={
        '\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_',
        '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}',
        '→':r'$\rightarrow$','×':r'$\times$','∈':r'$\in$','≤':r'$\leq$','≥':r'$\geq$',
        'ρ':r'$\rho$','θ':r'$\theta$','φ':r'$\phi$','Φ':r'$\Phi$','Δ':r'$\Delta$','π':r'$\pi$','⊥':r'$\bot$','ℓ':r'$\ell$'
    }
    return ''.join(repl.get(ch,ch) for ch in s)

def table_esc(x: object) -> str:
    """Escape a cell while admitting line breaks in dense formal expressions."""
    return (esc(x)
            .replace(',', r',\allowbreak{}')
            .replace('/', r'/\allowbreak{}')
            .replace(';', r';\allowbreak{}'))

def longtable(path, headers, rows, widths, caption, label, font='\\scriptsize'):
    spec='@{}' + ''.join(f'L{{{w}}}' for w in widths) + '@{}'
    lines=['\\begingroup', font, r'\setlength{\tabcolsep}{3pt}',
           f'\\begin{{longtable}}{{{spec}}}',f'\\caption{{{esc(caption)}}}\\label{{{label}}}\\\\',
           '\\toprule',' & '.join(r'\textbf{'+esc(h)+'}' for h in headers)+r' \\', '\\midrule','\\endfirsthead',
           f'\\multicolumn{{{len(headers)}}}{{l}}{{\\small\\itshape {esc(caption)} -- continued}}\\\\','\\toprule',
           ' & '.join(r'\textbf{'+esc(h)+'}' for h in headers)+r' \\', '\\midrule','\\endhead',
           '\\midrule',f'\\multicolumn{{{len(headers)}}}{{r}}{{\\small continued on next page}}\\\\','\\endfoot','\\bottomrule','\\endlastfoot']
    for row in rows:
        lines.append(' & '.join(table_esc(v) for v in row)+r' \\')
    lines += ['\\end{longtable}','\\normalsize','\\endgroup','']
    path.write_bytes('\n'.join(lines).encode('utf-8'))

ops=json.loads((ROOT/'spec/operator_catalog.json').read_text())['operators']
longtable(OUT/'operator_catalog.tex',['ID','Operator','Signature','Literal definition'],
          [(o['id'],o['name'],o['signature'],o['definition']) for o in ops],
          ['0.18\\textwidth','0.17\\textwidth','0.20\\textwidth','0.39\\textwidth'],
          f'TOMAGI 1.0 complete {len(ops)}-operator catalog','tab:operators')

syms=json.loads((ROOT/'spec/symbol_table.json').read_text())['symbols']
longtable(OUT/'symbol_table.tex',['Symbol','Typed meaning','Representation'],
          [(s['symbol'],s['meaning'],s['type']) for s in syms],
          ['0.16\\textwidth','0.39\\textwidth','0.39\\textwidth'],
          'TOMAGI 1.0 symbol contract','tab:symbols','\\small')

opcodes=json.loads((ROOT/'spec/opcode_table.json').read_text())['opcodes']
longtable(OUT/'opcode_table.tex',['Code','Name','State effect'],
          [(o['code'],o['name'],o['effect']) for o in opcodes],
          ['0.08\\textwidth','0.16\\textwidth','0.69\\textwidth'],
          'The sixteen portable Cell48 opcodes','tab:opcodes','\\small')

state=json.loads((ROOT/'spec/state64_layout.json').read_text())['fields']
longtable(OUT/'state_layout.tex',['Word','Byte','Field','Type','Meaning'],
          [(f['word'],f['byte_offset'],f['name'],f['type'],f['meaning']) for f in state],
          ['0.07\\textwidth','0.07\\textwidth','0.13\\textwidth','0.09\\textwidth','0.56\\textwidth'],
          'State64 ABI','tab:state64','\\small')

cell=json.loads((ROOT/'spec/cell48_layout.json').read_text())['fields']
longtable(OUT/'cell_layout.tex',['Word','Byte','Field','Type','Meaning'],
          [(f['word'],f['byte_offset'],f['name'],f['type'],f['meaning']) for f in cell],
          ['0.07\\textwidth','0.07\\textwidth','0.13\\textwidth','0.09\\textwidth','0.56\\textwidth'],
          'Cell48 ABI','tab:cell48','\\small')

reg=json.loads((ROOT/'sources/source_register.json').read_text())['sources']
longtable(OUT/'source_register.tex',['ID','Source','SHA-256','Role'],
          [(r['id'],r['title'],r['sha256'][:16]+'...'+r['sha256'][-8:],r['role']) for r in reg],
          ['0.06\\textwidth','0.25\\textwidth','0.30\\textwidth','0.31\\textwidth'],
          'Project source register','tab:sources','\\scriptsize')

cross=json.loads((ROOT/'spec/source_crosswalk.json').read_text())['rows']
counts=Counter(r['source'].split(':',1)[0] for r in cross)
lines=['\\begin{tabular}{@{}lr@{}}','\\toprule','\\textbf{Source} & \\textbf{Crosswalk rows}\\\\','\\midrule']
for k in sorted(counts): lines.append(f'{esc(k)} & {counts[k]}\\\\')
lines += ['\\midrule',f'\\textbf{{Total}} & \\textbf{{{len(cross)}}}\\\\','\\bottomrule','\\end{tabular}']
(OUT/'crosswalk_summary.tex').write_bytes('\n'.join(lines).encode('utf-8'))

# Put all 64 exact Morton rows on one readable page as two parallel 32-row blocks.
sched=json.loads((ROOT/'spec/morton_schedule_64.json').read_text())['schedule']
left,right=sched[:32],sched[32:]
lines=[r'\begin{table}[H]',r'\centering',
       r'\caption{Exact 64-row MSB round-robin Morton schedule}\label{tab:morton}',
       r'\footnotesize',r'\setlength{\tabcolsep}{5pt}',r'\renewcommand{\arraystretch}{0.88}',
       r'\begin{tabular}{@{}rrr@{\hspace{1.2cm}}rrr@{}}',r'\toprule',
       r'\multicolumn{3}{c}{Output bits 63--32} & \multicolumn{3}{c}{Output bits 31--0} \\',
       r'\cmidrule(r){1-3}\cmidrule(l){4-6}',
       r'\textbf{Out} & \textbf{Field} & \textbf{Src} & \textbf{Out} & \textbf{Field} & \textbf{Src} \\',
       r'\midrule']
for a,b in zip(left,right):
    lines.append(f"{a['output_bit']} & {esc(a['field'])} & {a['source_bit']} & {b['output_bit']} & {esc(b['field'])} & {b['source_bit']}" + r' \\')
lines += [r'\bottomrule',r'\end{tabular}',r'\end{table}','']
(OUT/'morton_schedule.tex').write_bytes('\n'.join(lines).encode('utf-8'))

print({'operators':len(ops),'symbols':len(syms),'opcodes':len(opcodes),'crosswalk':len(cross)})
