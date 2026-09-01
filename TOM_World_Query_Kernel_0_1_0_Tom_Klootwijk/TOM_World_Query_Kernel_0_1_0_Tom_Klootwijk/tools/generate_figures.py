from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch, Circle, Arc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#0b2d3d"
TEAL = "#149c9a"
GOLD = "#d9a31a"
PURPLE = "#7356a8"
RED = "#c8584f"
GREEN = "#3e8f6a"
BLUE = "#3977a8"
LIGHT = "#f3f7f8"
GRAY = "#56646b"


def save(fig, name: str, dpi: int = 220) -> None:
    fig.savefig(OUT / name, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def box(ax, xy, wh, text, fc=LIGHT, ec=NAVY, fs=10, lw=1.6, radius=0.025):
    x, y = xy; w, h = wh
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.012,rounding_size={radius}",
                       facecolor=fc, edgecolor=ec, linewidth=lw)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs, color=NAVY,
            linespacing=1.2)
    return p


def arrow(ax, p0, p1, color=GRAY, lw=1.6, mutation=12, style="-|>"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=mutation,
                                 linewidth=lw, color=color, connectionstyle="arc3"))


def core_pipeline():
    fig, ax = plt.subplots(figsize=(13.2, 4.8))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.02, 0.94, "TOMAGI 1.0 literal execution chain", fontsize=20, fontweight="bold", color=NAVY)
    ax.text(0.02, 0.875, "One stored Cell48 executes per tick; the 1-bit result selects the next cell.", fontsize=10.5, color=GRAY)
    labels = [
        ("State64\ninput", TEAL),
        ("20/18/14/12\nkey", GOLD),
        ("LUT[SDF0]\ndefined cell = 0", PURPLE),
        ("JIT1\nparity bit", RED),
        ("KIN2\n$\\Delta^2 q$", BLUE),
        ("$\\phi$ / Klein /\nhinge", GREEN),
        ("cone / sphere\nrelation", GOLD),
        ("radix / L-system\nbranch", PURPLE),
        ("EMIT +\nlineage", TEAL),
    ]
    x0, gap = 0.018, 0.008
    w = (0.964 - gap*(len(labels)-1)) / len(labels)
    y, h = 0.46, 0.25
    for i, (lab, color) in enumerate(labels):
        x = x0 + i*(w+gap)
        box(ax, (x,y), (w,h), lab, fc="white", ec=color, fs=9.3, lw=2.0, radius=0.016)
        if i < len(labels)-1:
            arrow(ax, (x+w+0.001, y+h/2), (x+w+gap-0.001, y+h/2), color=NAVY, lw=1.5, mutation=10)
    ax.plot([0.355,0.355,0.22,0.22],[0.46,0.30,0.30,0.46], color=RED, lw=1.4)
    arrow(ax, (0.22,0.30), (0.22,0.45), color=RED, lw=1.4, mutation=10)
    ax.text(0.287,0.245,"parity is a deterministic route/perturbation primitive,\nnot an error-correction or safe-mode layer",ha="center",va="top",fontsize=9.5,color=RED)
    ax.text(0.02,0.07,"Functional condensation:  $\\Pi(\\mathrm{Cone}(\\mathrm{LSYS}(\\mathrm{Branch}(\\mathrm{Klein}(\\phi(\\mathrm{KIN2}(\\mathrm{JIT1}(\\mathrm{LUT}[\\mathrm{SDF0}](K))))))))))$",
            fontsize=11.5, color=NAVY)
    save(fig, "01_core_pipeline.png")


def key_layout():
    fig, ax = plt.subplots(figsize=(12.5, 4.5))
    ax.set_xlim(0, 64); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(0, 9.25, "Canonical 64-bit log-polar key", fontsize=20, fontweight="bold", color=NAVY)
    fields = [
        ("$q_\\rho$", 20, TEAL, "bits 63:44\n$2^{20}$ states"),
        ("$q_\\theta$", 18, GOLD, "bits 43:26\n$2^{18}$ states"),
        ("$q_X$", 14, PURPLE, "bits 25:12\n$2^{14}$ states"),
        ("$q_\\phi$", 12, RED, "bits 11:0\n$2^{12}$ states"),
    ]
    x=0
    for name,width,color,desc in fields:
        ax.add_patch(Rectangle((x,4.7),width,2.2,facecolor=color,edgecolor="white",linewidth=2))
        ax.text(x+width/2,6.15,name,ha="center",va="center",fontsize=17,color="white",fontweight="bold")
        ax.text(x+width/2,5.18,desc,ha="center",va="center",fontsize=9.4,color="white")
        x+=width
    ax.text(0,4.2,"bit 63",ha="left",va="top",fontsize=9,color=GRAY)
    ax.text(64,4.2,"bit 0",ha="right",va="top",fontsize=9,color=GRAY)
    ax.text(0,3.05,r"$K=(q_\rho\ll44)\;|\;(q_\theta\ll26)\;|\;(q_X\ll12)\;|\;q_\phi$",fontsize=16,color=NAVY)
    ax.text(0,1.95,"Reference tuple (949111, 0, 1920, 227)",fontsize=10.5,color=GRAY)
    ax.text(0,1.15,"contiguous  0xe7b77000007800e3",fontsize=11.5,color=NAVY,family="monospace")
    ax.text(34,1.15,"Morton  0x88823bb88099128b",fontsize=11.5,color=NAVY,family="monospace")
    ax.text(0,0.35,"Both layouts are exact, invertible encodings of the same quantized tuple; they are not the same bit order.",fontsize=10,color=GRAY)
    save(fig, "02_key_layout.png")


def abi_layout():
    fig, ax = plt.subplots(figsize=(12.8, 7.0))
    ax.set_xlim(0, 16); ax.set_ylim(0, 12); ax.axis("off")
    ax.text(0,11.35,"Backend-neutral integer ABI",fontsize=20,fontweight="bold",color=NAVY)
    ax.text(0,10.8,"The same byte records feed Python, C99, GLSL, WGSL and OpenCL implementations.",fontsize=10.5,color=GRAY)
    state = json.loads((ROOT/"spec/state64_layout.json").read_text())["fields"]
    cell = json.loads((ROOT/"spec/cell48_layout.json").read_text())["fields"]
    ax.text(0,9.95,"State64 - 16 x 32-bit words",fontsize=13,fontweight="bold",color=TEAL)
    for i,f in enumerate(state):
        col=i%8; row=i//8
        x=col*2; y=8.0-row*1.6
        ax.add_patch(Rectangle((x,y),1.9,1.2,facecolor="white",edgecolor=TEAL,linewidth=1.5))
        ax.text(x+0.95,y+0.74,f["name"],ha="center",va="center",fontsize=8.8,color=NAVY,fontweight="bold")
        ax.text(x+0.95,y+0.28,f'w{i} / {f["type"]}',ha="center",va="center",fontsize=7.5,color=GRAY)
    ax.text(0,5.05,"Cell48 - 12 x 32-bit words",fontsize=13,fontweight="bold",color=PURPLE)
    for i,f in enumerate(cell):
        col=i%6; row=i//6
        x=col*(16/6); y=3.1-row*1.6
        ax.add_patch(Rectangle((x,y),16/6-0.12,1.2,facecolor="white",edgecolor=PURPLE,linewidth=1.5))
        ax.text(x+(16/6-0.12)/2,y+0.74,f["name"],ha="center",va="center",fontsize=8.8,color=NAVY,fontweight="bold")
        ax.text(x+(16/6-0.12)/2,y+0.28,f'w{i} / {f["type"]}',ha="center",va="center",fontsize=7.5,color=GRAY)
    ax.text(0,0.22,"State64 is hot mutable state. Cell48 is immutable LUT instruction/data. Every arithmetic step is defined modulo 2^32, with explicit periodic normalization for theta, X and phi.",fontsize=9.5,color=GRAY)
    save(fig, "03_abi_layout.png")


def logpolar():
    fig, ax = plt.subplots(figsize=(7.2,7.2))
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-1.15,1.15); ax.set_ylim(-1.15,1.15)
    ax.text(-1.12,1.08,"Log-polar chart and multiplicative shells",fontsize=16,fontweight="bold",color=NAVY)
    rhos=np.linspace(-2.4,0,7)
    for rho in rhos:
        r=np.exp(rho)
        ax.add_patch(Circle((0,0),r,fill=False,edgecolor=TEAL,linewidth=1.1,alpha=.85))
        ax.text(r/np.sqrt(2),r/np.sqrt(2),f"$\\rho={rho:.1f}$",fontsize=7.5,color=GRAY)
    for k in range(16):
        a=2*np.pi*k/16
        ax.plot([0,np.cos(a)],[0,np.sin(a)],color=GOLD,linewidth=.7,alpha=.75)
    ax.add_patch(Circle((0,0),.055,facecolor=RED,edgecolor=RED))
    ax.text(.075,-.04,"explicit core",fontsize=8.5,color=RED)
    ax.text(-1.08,-1.05,r"$\rho=\ln(r/r_0),\quad \theta=\operatorname{atan2}(y,x),\quad r=r_0e^\rho$",fontsize=13,color=NAVY)
    save(fig,"04_logpolar_chart.png")


def sdf0_lut():
    fig, ax = plt.subplots(figsize=(10.8,5.6))
    ax.set_xlim(-1,13); ax.set_ylim(-1,8); ax.axis("off")
    ax.text(-.7,7.35,"Literal SDF0 inside the LUT",fontsize=20,fontweight="bold",color=NAVY)
    ax.text(-.7,6.78,"Defined addresses are the zero-level set; non-members are undefined, not positive or negative distance.",fontsize=10.5,color=GRAY)
    defined={(1,1),(2,1),(3,1),(3,2),(3,3),(4,3),(5,3),(6,3),(6,4),(7,4),(8,4),(9,4)}
    for y in range(5):
        for x in range(10):
            d=(x,y) in defined
            ax.add_patch(Rectangle((x, y),.88,.88,facecolor=("#e2f2ef" if d else "#f6f6f6"),edgecolor=(TEAL if d else "#d4dade"),linewidth=1.2))
            ax.text(x+.44,y+.44,"0" if d else r"$\bot$",ha="center",va="center",fontsize=12,color=(NAVY if d else "#a2aaad"))
    path=sorted(defined,key=lambda p:(p[0],p[1]))
    for a,b in zip(path,path[1:]):
        arrow(ax,(a[0]+.44,a[1]+.44),(b[0]+.44,b[1]+.44),color=PURPLE,lw=1.2,mutation=8)
    box(ax,(10.5,3.55),(2.0,1.25),"Cell48\nopcode + args\nnext0 / next1",fc="white",ec=PURPLE,fs=9.5)
    arrow(ax,(9.9,4.0),(10.48,4.0),color=PURPLE)
    ax.text(10.5,2.65,r"$Z_D(K)=0\quad(K\in D)$",fontsize=13,color=NAVY)
    ax.text(10.5,2.15,r"$Z_D(K)=\bot\quad(K\notin D)$",fontsize=13,color=NAVY)
    ax.text(-.7,-.45,"SDF0 is not a corrective boundary in TOMAGI. It is the literal membership/value relation from which the cell's operator is evaluated.",fontsize=9.8,color=RED)
    save(fig,"05_sdf0_lut.png")


def klein():
    fig, ax = plt.subplots(figsize=(10.5,5.7))
    ax.set_xlim(0,10); ax.set_ylim(0,6); ax.axis("off")
    ax.text(.25,5.45,"Reflective Klein radial wrap",fontsize=20,fontweight="bold",color=NAVY)
    ax.add_patch(Rectangle((1.2,1.2),7.2,3.4,facecolor="#f8fbfb",edgecolor=NAVY,linewidth=2))
    ax.plot([1.2,1.2],[1.2,4.6],color=RED,lw=5,alpha=.7)
    ax.plot([8.4,8.4],[1.2,4.6],color=TEAL,lw=5,alpha=.7)
    # opposing orientation arrows
    arrow(ax,(1.45,4.2),(1.45,1.55),color=RED,lw=2.2,mutation=14)
    arrow(ax,(8.15,1.55),(8.15,4.2),color=TEAL,lw=2.2,mutation=14)
    for y in [1.75,2.55,3.35,4.15]:
        arrow(ax,(2.0,y),(7.6,5.7-y),color=PURPLE,lw=1.2,mutation=10)
    ax.text(4.8,4.95,r"odd wrap: $\theta' = N_\theta/2-\theta$",ha="center",fontsize=12,color=PURPLE)
    ax.text(4.8,.72,r"$\rho'=\rho\,\mathrm{mod}\,N_\rho,\quad \phi'=-\phi,\quad o'=o\oplus1$",ha="center",fontsize=12,color=NAVY)
    ax.text(1.2,.28,"Source half-turn profile remains separately selectable: theta' = theta + Ntheta/2.",fontsize=9.5,color=GRAY)
    save(fig,"06_klein_wrap.png")


def backends():
    fig, ax = plt.subplots(figsize=(11.8,6.2))
    ax.set_xlim(0,12); ax.set_ylim(0,7); ax.axis("off")
    ax.text(.2,6.45,"One binary program, multiple deterministic backends",fontsize=20,fontweight="bold",color=NAVY)
    box(ax,(.35,3.0),(2.25,1.25),"literal JSON\n+ content hashes",fc="white",ec=GOLD,fs=11)
    arrow(ax,(2.62,3.62),(3.35,3.62),color=NAVY)
    box(ax,(3.38,3.0),(2.05,1.25),"compiler\n.tmg",fc="white",ec=PURPLE,fs=11)
    xs=[6.25,8.65,10.85]
    names=[("Python oracle",TEAL),("C99 CPU",BLUE),("GPU kernel",RED)]
    for (name,color),x in zip(names,xs):
        arrow(ax,(5.45,3.62),(x-.15,3.62),color=NAVY)
        box(ax,(x,2.95),(1.8,1.35),name,fc="white",ec=color,fs=10.2)
        arrow(ax,(x+.9,2.92),(x+.9,1.9),color=color)
        box(ax,(x,1.0),(1.8,.85),"same State64\ntransition",fc=LIGHT,ec=color,fs=9.2)
    ax.text(.4,1.1,"Required equality:\nbyte-identical initial state + cells + seed + tick count\n$\\Rightarrow$ identical final 16-word state and lineage",fontsize=11.2,color=NAVY,linespacing=1.5)
    ax.text(.4,.32,"The supplied validation executes Python and C against the same .tmg file. GLSL, WGSL and OpenCL sources implement the same ABI and opcode equations.",fontsize=9.5,color=GRAY)
    save(fig,"07_backend_equivalence.png")


def nineteen():
    fig, ax = plt.subplots(figsize=(11.8,5.8))
    ax.set_xlim(0,12); ax.set_ylim(0,7); ax.axis("off")
    ax.text(.2,6.42,"Source-derived 19 feature pipeline",fontsize=20,fontweight="bold",color=NAVY)
    bits=[1,0,0,1,1]; weights=[16,8,4,2,1]
    for i,(b,w) in enumerate(zip(bits,weights)):
        x=.55+i*1.15
        ax.add_patch(Circle((x,4.7),.42,facecolor=(RED if b else "white"),edgecolor=(RED if b else GRAY),linewidth=1.5))
        ax.text(x,4.7,str(b),ha="center",va="center",fontsize=14,color=("white" if b else GRAY),fontweight="bold")
        ax.text(x,4.05,str(w),ha="center",fontsize=8.5,color=GRAY)
    ax.text(.55,3.55,"19 = 10011; active positions = {4,1,0}; popcount = 3",fontsize=11,color=NAVY)
    box(ax,(6.55,4.18),(2.1,1.05),"ne | gen | tien\n3 declared pulses",fc="white",ec=TEAL,fs=10.5)
    arrow(ax,(5.6,4.7),(6.5,4.7),color=NAVY)
    tri=np.array([[9.9,5.25],[9.0,3.45],[10.8,3.45]])
    ax.fill(tri[:,0],tri[:,1],facecolor="#e7f3f1",edgecolor=TEAL,linewidth=2)
    for x,y in tri: ax.add_patch(Circle((x,y),.12,facecolor=RED,edgecolor=RED))
    arrow(ax,(8.7,4.7),(9.25,4.7),color=NAVY)
    ax.text(9.9,2.95,"chosen 3-pulse projection: triangle",ha="center",fontsize=10,color=NAVY)
    ax.text(.45,1.65,"Typed result",fontsize=12,fontweight="bold",color=PURPLE)
    ax.text(.45,.95,"numeric value remains 19; binary word remains 10011; Dutch segmentation and triangle are separate, linked representations.",fontsize=10.5,color=GRAY)
    ax.text(.45,.35,"The feature-count equality is executable metadata, not an arithmetic rewrite.",fontsize=10.5,color=RED)
    save(fig,"08_nineteen_pipeline.png")


def trace_figure():
    result=json.loads((ROOT/"examples/polar_loop.expected.json").read_text())
    trace=result["trace"]
    fig, ax=plt.subplots(figsize=(12.8,5.2))
    ax.set_xlim(-.4,len(trace)-.6); ax.set_ylim(-1.8,2.5); ax.axis("off")
    ax.text(-.35,2.13,"Executable polar-loop trace",fontsize=20,fontweight="bold",color=NAVY)
    names=['SDF0','JIT1','KIN2','KLEIN','HINGE','LSYS','CONE','EMIT']
    colors=[PURPLE,RED,BLUE,GREEN,GOLD,TEAL,PURPLE,RED]
    for i,(r,name,color) in enumerate(zip(trace,names,colors)):
        ax.add_patch(Circle((i,.55),.34,facecolor="white",edgecolor=color,linewidth=2))
        ax.text(i,.55,str(i),ha="center",va="center",fontsize=9,color=NAVY,fontweight="bold")
        ax.text(i,.03,name,ha="center",va="top",fontsize=8.8,color=NAVY,rotation=35)
        ax.text(i,1.25,f"b={r['branch']}\ncell={r['cell_after']}",ha="center",va="bottom",fontsize=7.8,color=GRAY)
        if i<len(trace)-1: arrow(ax,(i+.36,.55),(i+1-.36,.55),color=NAVY,lw=1.4,mutation=10)
    s=result['state']
    ax.text(-.3,-1.18,f"Final token 0x{s['output']:08x} = PYRA | rho={s['rho']} theta={s['theta']} X={s['tick']} phi={s['phi']} | orientation={s['orientation']} sheet={s['sheet']}",fontsize=10.5,color=NAVY,family='monospace')
    ax.text(-.3,-1.62,f"lineage={s['lineage']}  status=0x{s['status']:08x}  Python/C conformance: exact",fontsize=9.8,color=GRAY,family='monospace')
    save(fig,"09_polar_loop_trace.png")


def inference():
    fig, ax=plt.subplots(figsize=(11.8,5.8))
    ax.set_xlim(0,12); ax.set_ylim(0,7); ax.axis('off')
    ax.text(.2,6.35,"Deterministic substitution for learned inference",fontsize=20,fontweight='bold',color=NAVY)
    items=[('facts / literals',GOLD),('typed relations',TEAL),('rule compiler',PURPLE),('Cell48 LUT',RED),('State64 execution',BLUE),('token + trace',GREEN)]
    x=.25
    for i,(name,color) in enumerate(items):
        box(ax,(x,3.45),(1.6,1.15),name,fc='white',ec=color,fs=10)
        if i<len(items)-1: arrow(ax,(x+1.62,4.02),(x+1.88,4.02),color=NAVY,mutation=9)
        x+=1.9
    ax.text(.35,2.45,"TOMAGI replaces a learned predictor when the domain can be compiled into finite literals, relations, branch rules and output tokens.",fontsize=11,color=NAVY)
    ax.text(.35,1.75,"There are no weights, sampling temperatures, embeddings, confidence scores or hidden stochastic state in the 1.0 execution core.",fontsize=10.5,color=RED)
    ax.text(.35,.9,"Same program bytes + same input state + same tick count  ->  same output and replay lineage on every conforming backend.",fontsize=11,color=PURPLE,fontweight='bold')
    save(fig,"10_deterministic_inference.png")


if __name__ == '__main__':
    core_pipeline(); key_layout(); abi_layout(); logpolar(); sdf0_lut(); klein(); backends(); nineteen(); trace_figure(); inference()
    print(f"generated {len(list(OUT.glob('*.png')))} figures in {OUT}")
