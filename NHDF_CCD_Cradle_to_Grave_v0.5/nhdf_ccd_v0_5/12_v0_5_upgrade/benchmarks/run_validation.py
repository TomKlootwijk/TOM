from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from nhdf_ccd_v05.batch import evaluate_queries
from nhdf_ccd_v05.ccd import edge_edge_ccd, vertex_face_ccd
from nhdf_ccd_v05.corpus import corpus_statistics, load_sample_queries
from nhdf_ccd_v05.events import group_contact_events
from nhdf_ccd_v05.geometry import point_triangle_distance2, segment_segment_distance2
from nhdf_ccd_v05.model import Certificate, LinearPoint, Status, Vec3
from nhdf_ccd_v05.response import BodyState, apply_frictionless_impulse
from nhdf_ccd_v05.rigid import RigidMotionBound, relative_speed_bound


def lp(p0, p1=None):
    if p1 is None:
        p1 = p0
    return LinearPoint(Vec3(*p0), Vec3(*p1))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def endpoint_vf(p, a, b, c, tol=1e-9):
    for t in (0.0, 1.0):
        r = point_triangle_distance2(p.at(t), a.at(t), b.at(t), c.at(t))
        if r.distance2 <= tol * tol:
            return True
    return False


def endpoint_ee(a0, a1, b0, b1, tol=1e-9):
    for t in (0.0, 1.0):
        r = segment_segment_distance2(a0.at(t), a1.at(t), b0.at(t), b1.at(t))
        if r.distance2 <= tol * tol:
            return True
    return False


def synthetic_benchmark(n_per_class=1000, seed=50042026):
    rng = random.Random(seed)
    rows = []
    stats = {
        "vf": {"queries": 0, "truth_hits": 0, "ccd_hits": 0, "ccd_misses": 0, "ccd_inconclusive": 0, "endpoint_hits": 0, "errors": 0, "time_seconds": 0.0},
        "ee": {"queries": 0, "truth_hits": 0, "ccd_hits": 0, "ccd_misses": 0, "ccd_inconclusive": 0, "endpoint_hits": 0, "errors": 0, "time_seconds": 0.0},
    }

    vf_cases = []
    for i in range(n_per_class):
        x = rng.uniform(0.05, 0.75)
        y = rng.uniform(0.05, max(0.051, 0.9 - x))
        t = rng.uniform(0.02, 0.98)
        z0 = rng.uniform(0.25, 5.0)
        z1 = -z0 * (1.0 - t) / t
        vf_cases.append((True, lp((x,y,z0),(x,y,z1)), lp((0,0,0)), lp((1,0,0)), lp((0,1,0)), t))
    for i in range(n_per_class):
        x = rng.uniform(1.2, 4.0)
        y = rng.uniform(1.2, 4.0)
        z0 = rng.uniform(0.25, 5.0)
        z1 = -rng.uniform(0.25, 5.0)
        vf_cases.append((False, lp((x,y,z0),(x,y,z1)), lp((0,0,0)), lp((1,0,0)), lp((0,1,0)), None))

    start = time.perf_counter()
    for idx, (truth, p,a,b,c,expected_t) in enumerate(vf_cases):
        cert = vertex_face_ccd(p,a,b,c,geom_tol=1e-8,time_tol=1e-10,pair_id=f"svf:{idx}")
        baseline = endpoint_vf(p,a,b,c)
        pred = cert.status in {Status.HIT, Status.INITIAL_OVERLAP}
        inc = not cert.conclusive
        err = None if expected_t is None or cert.toi_upper is None else abs(cert.toi_upper - expected_t)
        s = stats["vf"]
        s["queries"] += 1
        s["truth_hits"] += int(truth)
        s["ccd_hits"] += int(pred)
        s["ccd_misses"] += int(cert.status == Status.MISS)
        s["ccd_inconclusive"] += int(inc)
        s["endpoint_hits"] += int(baseline)
        s["errors"] += int(cert.conclusive and pred != truth)
        rows.append({"kind":"vertex-face","index":idx,"truth":int(truth),"status":cert.status.value,"endpoint":int(baseline),"toi_expected":expected_t,"toi_lower":cert.toi_lower,"toi_upper":cert.toi_upper,"toi_abs_error":err,"digest":cert.digest()})
    stats["vf"]["time_seconds"] = time.perf_counter() - start

    ee_cases = []
    for i in range(n_per_class):
        t = rng.uniform(0.02, 0.98)
        z0 = rng.uniform(0.25, 5.0)
        z1 = -z0 * (1.0 - t) / t
        shift = rng.uniform(-0.2, 0.2)
        ee_cases.append((True, lp((-1,shift,0)), lp((1,shift,0)), lp((0,-1,z0),(0,-1,z1)), lp((0,1,z0),(0,1,z1)), t))
    for i in range(n_per_class):
        x = rng.uniform(1.2, 4.0)
        z0 = rng.uniform(0.25, 5.0)
        z1 = -rng.uniform(0.25, 5.0)
        ee_cases.append((False, lp((-1,0,0)), lp((1,0,0)), lp((x,-1,z0),(x,-1,z1)), lp((x,1,z0),(x,1,z1)), None))

    start = time.perf_counter()
    for idx, (truth,a0,a1,b0,b1,expected_t) in enumerate(ee_cases):
        cert = edge_edge_ccd(a0,a1,b0,b1,geom_tol=1e-8,time_tol=1e-10,pair_id=f"see:{idx}")
        baseline = endpoint_ee(a0,a1,b0,b1)
        pred = cert.status in {Status.HIT, Status.INITIAL_OVERLAP}
        inc = not cert.conclusive
        err = None if expected_t is None or cert.toi_upper is None else abs(cert.toi_upper - expected_t)
        s = stats["ee"]
        s["queries"] += 1
        s["truth_hits"] += int(truth)
        s["ccd_hits"] += int(pred)
        s["ccd_misses"] += int(cert.status == Status.MISS)
        s["ccd_inconclusive"] += int(inc)
        s["endpoint_hits"] += int(baseline)
        s["errors"] += int(cert.conclusive and pred != truth)
        rows.append({"kind":"edge-edge","index":idx,"truth":int(truth),"status":cert.status.value,"endpoint":int(baseline),"toi_expected":expected_t,"toi_lower":cert.toi_lower,"toi_upper":cert.toi_upper,"toi_abs_error":err,"digest":cert.digest()})
    stats["ee"]["time_seconds"] = time.perf_counter() - start

    for key in ("vf","ee"):
        s = stats[key]
        s["queries_per_second"] = s["queries"] / s["time_seconds"] if s["time_seconds"] else None
        errors = [r["toi_abs_error"] for r in rows if r["kind"] == ("vertex-face" if key == "vf" else "edge-edge") and r["toi_abs_error"] is not None]
        s["max_toi_abs_error"] = max(errors) if errors else None
        s["mean_toi_abs_error"] = statistics.fmean(errors) if errors else None
        s["endpoint_missed_truth_hits"] = s["truth_hits"] - s["endpoint_hits"]
    return stats, rows


def event_benchmark(n=20000):
    certs=[]
    for i in range(n):
        center = (i // 4) * 1e-5
        certs.append(Certificate(Status.HIT,"fixture",pair_id=f"p{i:08d}",toi_lower=center,toi_upper=center+2e-9,method="fixture",termination_reason="fixture"))
    start=time.perf_counter()
    groups=group_contact_events(certs,merge_tolerance=1e-9)
    elapsed=time.perf_counter()-start
    return {"contacts":n,"events":len(groups),"time_seconds":elapsed,"contacts_per_second":n/elapsed if elapsed else None,"deterministic_first_pairs":list(groups[0].pair_ids[:4]) if groups else []}


def rigid_bound_audit(n=10000,seed=42005):
    rng=random.Random(seed)
    violations=0
    max_slack=0.0
    min_slack=math.inf
    for _ in range(n):
        va=Vec3(*(rng.uniform(-10,10) for _ in range(3)))
        vb=Vec3(*(rng.uniform(-10,10) for _ in range(3)))
        wa=Vec3(*(rng.uniform(-5,5) for _ in range(3)))
        wb=Vec3(*(rng.uniform(-5,5) for _ in range(3)))
        ra=Vec3(*(rng.uniform(-3,3) for _ in range(3)))
        rb=Vec3(*(rng.uniform(-3,3) for _ in range(3)))
        ba=RigidMotionBound(va,wa.norm(),ra.norm())
        bb=RigidMotionBound(vb,wb.norm(),rb.norm())
        bound=relative_speed_bound(ba,bb)
        actual=(va+wa.cross(ra) - vb-wb.cross(rb)).norm()
        slack=bound-actual
        min_slack=min(min_slack,slack)
        max_slack=max(max_slack,slack)
        if slack < -1e-11:
            violations += 1
    return {"samples":n,"violations":violations,"minimum_slack":min_slack,"maximum_slack":max_slack}


def response_audit(n=5000,seed=45002):
    rng=random.Random(seed)
    momentum_error=[]
    nonpenetration_failures=0
    energy_gain_failures=0
    for i in range(n):
        ma=rng.uniform(.1,10)
        mb=rng.uniform(.1,10)
        va=Vec3(rng.uniform(-5,5),rng.uniform(-1,1),rng.uniform(-1,1))
        vb=Vec3(rng.uniform(-5,5),rng.uniform(-1,1),rng.uniform(-1,1))
        nrm=Vec3(1,0,0)
        # Orient normal so the selected pair is closing.
        if (va-vb).dot(nrm) >= 0:
            nrm=Vec3(-1,0,0)
        a=BodyState("a",ma,Vec3(0,0,0),va)
        b=BodyState("b",mb,Vec3(1,0,0),vb)
        e=rng.uniform(0,1)
        p0=va*ma+vb*mb
        ke0=.5*ma*va.norm2()+.5*mb*vb.norm2()
        r=apply_frictionless_impulse(a,b,nrm,e)
        p1=r.body_a.velocity*ma+r.body_b.velocity*mb
        ke1=.5*ma*r.body_a.velocity.norm2()+.5*mb*r.body_b.velocity.norm2()
        momentum_error.append((p1-p0).norm())
        if r.applied and r.post_normal_relative_speed < -1e-10:
            nonpenetration_failures += 1
        if ke1 > ke0 + 1e-9:
            energy_gain_failures += 1
    return {"samples":n,"max_momentum_error":max(momentum_error),"mean_momentum_error":statistics.fmean(momentum_error),"post_impulse_closing_failures":nonpenetration_failures,"energy_gain_failures":energy_gain_failures}


def external_corpus():
    base=ROOT/"corpus/vendor/sample_queries/erleben-sliding-spike"
    vf_path=base/"vertex-face/data_0_0.csv"
    ee_path=base/"edge-edge/data_0_0.csv"
    vf=load_sample_queries(vf_path,"vertex-face")
    ee=load_sample_queries(ee_path,"edge-edge")
    start=time.perf_counter(); vf_summary,vf_records=evaluate_queries(vf,geom_tol=1e-7,time_tol=1e-9,max_intervals=100000); vf_time=time.perf_counter()-start
    start=time.perf_counter(); ee_summary,ee_records=evaluate_queries(ee,geom_tol=1e-7,time_tol=1e-9,max_intervals=100000); ee_time=time.perf_counter()-start
    return {
        "vertex_face":{"path":str(vf_path.relative_to(ROOT)),"sha256":sha256(vf_path),"corpus":corpus_statistics(vf),"evaluation":vf_summary.to_dict(),"time_seconds":vf_time},
        "edge_edge":{"path":str(ee_path.relative_to(ROOT)),"sha256":sha256(ee_path),"corpus":corpus_statistics(ee),"evaluation":ee_summary.to_dict(),"time_seconds":ee_time},
    }, vf_records, ee_records


def write_csv(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def make_figures(summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figdir=ROOT/"figures"; figdir.mkdir(exist_ok=True)

    syn=summary["synthetic"]
    labels=["Vertex–face","Edge–edge"]
    ccd=[syn["vf"]["ccd_hits"],syn["ee"]["ccd_hits"]]
    endpoint=[syn["vf"]["endpoint_hits"],syn["ee"]["endpoint_hits"]]
    truth=[syn["vf"]["truth_hits"],syn["ee"]["truth_hits"]]
    x=np.arange(len(labels)); width=.25
    fig,ax=plt.subplots(figsize=(8,4.8))
    ax.bar(x-width,truth,width,label="Ground-truth contacts")
    ax.bar(x,ccd,width,label="v0.5 CCD detected")
    ax.bar(x+width,endpoint,width,label="Endpoint-only detected")
    ax.set_ylabel("Contacts")
    ax.set_xticks(x,labels)
    ax.set_title("Constructed tunnelling corpus: continuous vs endpoint-only")
    ax.legend(loc="best")
    ax.grid(axis="y",alpha=.25)
    fig.tight_layout(); fig.savefig(figdir/"synthetic_detection.png",dpi=180); plt.close(fig)

    ext=summary["external_corpus"]
    names=["VF","EE"]
    tp=[ext["vertex_face"]["evaluation"]["true_positive"],ext["edge_edge"]["evaluation"]["true_positive"]]
    tn=[ext["vertex_face"]["evaluation"]["true_negative"],ext["edge_edge"]["evaluation"]["true_negative"]]
    fp=[ext["vertex_face"]["evaluation"]["false_positive"],ext["edge_edge"]["evaluation"]["false_positive"]]
    fn=[ext["vertex_face"]["evaluation"]["false_negative"],ext["edge_edge"]["evaluation"]["false_negative"]]
    inc=[ext["vertex_face"]["evaluation"]["inconclusive"],ext["edge_edge"]["evaluation"]["inconclusive"]]
    fig,ax=plt.subplots(figsize=(8,4.8))
    bottom=np.zeros(2)
    for vals,label in [(tp,"True positive"),(tn,"True negative"),(fp,"False positive"),(fn,"False negative"),(inc,"Inconclusive")]:
        ax.bar(names,vals,bottom=bottom,label=label)
        bottom += np.array(vals)
    ax.set_ylabel("Queries")
    ax.set_title("Vendored Sample-Queries evaluation outcome")
    ax.legend(loc="best")
    ax.grid(axis="y",alpha=.25)
    fig.tight_layout(); fig.savefig(figdir/"external_corpus_outcomes.png",dpi=180); plt.close(fig)

    throughput=[syn["vf"]["queries_per_second"],syn["ee"]["queries_per_second"],summary["event_grouping"]["contacts_per_second"]]
    fig,ax=plt.subplots(figsize=(8,4.8))
    ax.bar(["VF CCD","EE CCD","Event grouping"],throughput)
    ax.set_yscale("log")
    ax.set_ylabel("Operations per second (log scale)")
    ax.set_title("Reference Python throughput on recorded build host")
    ax.grid(axis="y",which="both",alpha=.25)
    fig.tight_layout(); fig.savefig(figdir/"reference_throughput.png",dpi=180); plt.close(fig)

    angles=np.linspace(0,4*math.pi,400)
    radius=1.0
    arc=np.minimum(2*radius,radius*angles)
    chord=2*radius*np.sin(np.minimum(angles,math.pi)/2)
    fig,ax=plt.subplots(figsize=(8,4.8))
    ax.plot(angles,arc,label="Bound min(2r, r|θ|)")
    ax.plot(angles,chord,label="Endpoint chord for |θ|≤π")
    ax.set_xlabel("Angular travel |θ| (rad)")
    ax.set_ylabel("Displacement / radius")
    ax.set_title("Rotation envelope used for swept broad-phase inflation")
    ax.legend(); ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(figdir/"rotational_margin.png",dpi=180); plt.close(fig)

    # deterministic event timeline diagram
    fig,ax=plt.subplots(figsize=(9,3.3))
    intervals=[(.10,.16,"A"),(.155,.21,"B"),(.205,.23,"C"),(.42,.44,"D")]
    for i,(lo,hi,name) in enumerate(intervals):
        ax.plot([lo,hi],[i,i],linewidth=7,solid_capstyle="butt")
        ax.text((lo+hi)/2,i+.15,name,ha="center")
    ax.axvspan(.10,.23,alpha=.12,label="Transitive event group 0")
    ax.axvspan(.42,.44,alpha=.12,label="Event group 1")
    ax.set_yticks([]); ax.set_xlim(0,0.5); ax.set_xlabel("Normalized time")
    ax.set_title("Interval-overlap event grouping")
    ax.legend(loc="upper right")
    fig.tight_layout(); fig.savefig(figdir/"event_grouping_timeline.png",dpi=180); plt.close(fig)


def main():
    (ROOT/"validation").mkdir(exist_ok=True)
    synthetic, synthetic_rows=synthetic_benchmark()
    external, vf_records, ee_records=external_corpus()
    summary={
        "release":"NHDF-CCD v0.5",
        "generated_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "synthetic":synthetic,
        "external_corpus":external,
        "event_grouping":event_benchmark(),
        "rigid_bound_audit":rigid_bound_audit(),
        "response_audit":response_audit(),
        "environment":{
            "python":sys.version,
            "platform":platform.platform(),
            "processor":platform.processor(),
            "numpy":np.__version__,
            "cpu_count":os.cpu_count(),
        },
    }
    write_csv(ROOT/"validation/synthetic_records.csv",synthetic_rows)
    write_csv(ROOT/"validation/external_vertex_face_records.csv",vf_records)
    write_csv(ROOT/"validation/external_edge_edge_records.csv",ee_records)
    (ROOT/"validation/validation_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (ROOT/"validation/environment.json").write_text(json.dumps(summary["environment"],indent=2,sort_keys=True)+"\n",encoding="utf-8")
    make_figures(summary)

    syn=summary["synthetic"]
    ext=summary["external_corpus"]
    lines=[
        "# NHDF-CCD v0.5 release validation log",
        "",
        f"Generated: `{summary['generated_utc']}`",
        "",
        "## Executed evidence",
        "",
        f"- Synthetic vertex–face queries: **{syn['vf']['queries']}**, conclusive errors: **{syn['vf']['errors']}**, endpoint-only missed truth hits: **{syn['vf']['endpoint_missed_truth_hits']}**, maximum TOI error: **{syn['vf']['max_toi_abs_error']:.3e}**.",
        f"- Synthetic edge–edge queries: **{syn['ee']['queries']}**, conclusive errors: **{syn['ee']['errors']}**, endpoint-only missed truth hits: **{syn['ee']['endpoint_missed_truth_hits']}**, maximum TOI error: **{syn['ee']['max_toi_abs_error']:.3e}**.",
        f"- External vertex–face file: **{ext['vertex_face']['corpus']['queries']}** queries, statuses `{ext['vertex_face']['evaluation']['status_counts']}`, conclusive accuracy `{ext['vertex_face']['evaluation']['conclusive_accuracy']}`.",
        f"- External edge–edge file: **{ext['edge_edge']['corpus']['queries']}** queries, statuses `{ext['edge_edge']['evaluation']['status_counts']}`, conclusive accuracy `{ext['edge_edge']['evaluation']['conclusive_accuracy']}`.",
        f"- Rigid-motion inequality audit: **{summary['rigid_bound_audit']['samples']}** samples, **{summary['rigid_bound_audit']['violations']}** observed violations.",
        f"- Response audit: **{summary['response_audit']['samples']}** samples, maximum momentum error **{summary['response_audit']['max_momentum_error']:.3e}**, energy-gain failures **{summary['response_audit']['energy_gain_failures']}**.",
        f"- Event grouping: **{summary['event_grouping']['contacts']}** contacts into **{summary['event_grouping']['events']}** deterministic interval groups.",
        "",
        "## Interpretation boundary",
        "",
        "Synthetic constructed cases validate the implemented algebraic roots and certificates for the tested distributions. The vendored external corpus is a harder adversarial check; any false result or inconclusive result remains visible in the CSV records and is not silently reclassified. The solver uses floating-point root finding and is not an exact-arithmetic replacement for a production robust predicate library.",
        "",
        "GPU, rotating triangle-mesh, deformable self-collision, frictional manifold solve, and production engine integration remain unvalidated in this release.",
    ]
    (ROOT/"validation/RELEASE_VALIDATION_LOG.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
