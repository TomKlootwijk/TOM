from __future__ import annotations
import csv, hashlib, json, os, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHIPPED_REGISTER_PATH=ROOT/'sources/source_register.json'
SHIPPED_CATALOG_PATH=ROOT/'sources/ugts_knowledge_catalog_211.json'


def optional_path(name: str) -> Path | None:
    value=os.environ.get(name)
    return Path(value).expanduser().resolve() if value else None


def select_catalog_path() -> Path:
    external=optional_path('TOMAGI_CATALOG_PATH')
    if external is not None:
        if external.is_file():
            print(f'Using external source catalog: {external}',file=sys.stderr)
            return external
        print(
            f'TOMAGI_CATALOG_PATH does not exist; using shipped condensed catalog: {external}',
            file=sys.stderr,
        )
    if not SHIPPED_CATALOG_PATH.is_file():
        raise FileNotFoundError(
            'shipped condensed catalog is missing: '
            f'{SHIPPED_CATALOG_PATH}. Restore the package input or set TOMAGI_CATALOG_PATH.'
        )
    print('Using shipped condensed source catalog; external catalog regeneration skipped.',file=sys.stderr)
    return SHIPPED_CATALOG_PATH


CATALOG_PATH=select_catalog_path()


def sha(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()

operators=[
("TOM.DEF","definition node","record -> address","A typed in-substrate definition d=(id,kind,A,B,parameters,dependencies,phase,provenance,hash).","canonical JSON + SHA-256","K36-01..06; SCLP literal integration"),
("TOM.REF","reference resolution","definition graph -> ordered graph","Resolve every definition_ref and dependency ID; order dependencies before dependents.","topological order","K36-03, K36-06"),
("TOM.SEQ","ordered composition","operators^n -> operator","Composition is serialized and non-commutative; execute the stored order without re-sorting.","cell successor order","K36-23, K36-31"),
("TOM.INDEX0","zero-based position","offset -> ordinal","ordinal = offset + 1; the stored timeline coordinate remains the zero-based offset.","integer add","Ben Burger 1D timeline"),
("TOM.LOGPOLAR","log-polar chart","(x,y,r0) -> (rho,theta)","rho=ln(r/r0), theta=atan2(y,x); runtime consumes quantized rho/theta already compiled.","host compiler; integer hot path","SCLP 5; M049,M111"),
("TOM.KEY.C","contiguous 64-bit key","rho20 x theta18 x X14 x phi12 -> K","K=(rho<<44)|(theta<<26)|(X<<12)|phi.","two u32 words","SCLP 12"),
("TOM.KEY.M","Morton 64-bit key","rho20 x theta18 x X14 x phi12 -> KM","Interleave MSB round-robin: rho19,theta17,X13,phi11,... until all 64 bits are consumed.","CPU/compiler codec","SCLP 12"),
("TOM.FETCH","LUT cell lookup","K -> Cell or undefined","Resolve a canonical key in the sorted cell table; compiled graph mode may use direct successor indices.","binary search or direct index","1bit-PDF LUT; M111,M112"),
("TOM.SDF0","literal zero field","defined key -> 0","Z_D(K)=0 for every K in the finite domain D of definable cells; Z_D(K)=bottom otherwise.","occupancy/definition bit","1bit-PDF pp.16-18; SCLP SDF-zero"),
("TOM.PARITY","one-bit reduction","u32 -> bit","P(w)=popcount(w) mod 2.","integer popcount","1bit parity; M025"),
("TOM.JIT1","one-bit jitter","seed x K x X -> {-a,+a}","j=P(mix32(seed xor K_hi xor rotl(K_lo,13) xor X xor aux)); sigma=2j-1; selected state field += sigma*a.","opcode 2","SCLP deterministic jitter; 1bit-PDF"),
("TOM.DELTA1","first discrete difference","q_n,q_(n-1) -> v_n","Delta q_n=q_n-q_(n-1).","integer difference","kinematic calculus"),
("TOM.DELTA2","second discrete difference","v_n,v_(n-1) -> a_n","Delta^2 q_n=v_n-v_(n-1); Delta^2 phi is the angular acceleration coordinate.","cell args","delta-delta lower-case phi"),
("TOM.KIN2","second-order update","state x acceleration-cell -> state","v_(n+1)=v_n+a_cell; q_(n+1)=q_n+v_(n+1).","opcode 3","kinematic calculus packed into LUT"),
("TOM.PHI","lower-case phi hinge","phi x delta -> phi","phi is periodic in Z/(2^12 Z); capital Phi is reserved for the golden ratio and is not the runtime phase.","opcode 4","SCLP symbol contract; lower-case phi source"),
("TOM.TIME","timeline phase","X x delta -> X,winding","X is a 14-bit modular tick; wraps contribute to lineage while the tick remains periodic.","opcode 5","SCLP time/phase/winding; 0-index timeline"),
("TOM.CONE","analytic cone relation","packed chart x cone parameters -> signed relation","r=max(rho_min-rho,rho-rho_max,|cyclic(theta-theta0)|-alpha_q); inside iff r<=0.","opcode 7","cone support, side-view pyramid"),
("TOM.SWEEP","swept cone family","cone x path -> relation","F_sweep(x)=inf_u d_C(x-s(u)); a compiled profile may tabulate the path as KIN2 cells.","derived macro","SCLP sweep; analytic sweeping cone"),
("TOM.CIRCLE","circle/radial shell","rho x center,width -> signed relation","A circle is a radial shell in the packed chart and an axial projection of a cone.","SPHERE profile / projection tag","source circle"),
("TOM.SPHERE","spherical support","rho,phi x center,width -> signed relation","Packed shell residual is max(|rho-rho0|-dr, |cyclic(phi-phi0)|-dphi); Euclidean helper is ||x-c||-R.","opcode 8","SCLP sphere relation"),
("TOM.OVERLAP","lens intersection","A,B -> A intersect B","Shared domain is exact conjunction/intersection; it may be used as a join key or connector locus.","derived predicate","Ben Burger slight overlap; M041,M107"),
("TOM.KLEIN","reflective Klein wrap","state -> state","On an odd radial wrap: rho'=rho mod N_rho, theta'=N_theta/2-theta, phi'=-phi, orientation'=orientation xor 1; optional sheet flip.","opcode 9","SCLP reflective Klein profile"),
("TOM.MOBIUS","half-turn bundle","state -> state","On an odd wrap: theta'=theta+N_theta/2, phi'=-phi, orientation'=orientation xor 1.","KLEIN flag profile","SCLP source half-turn; UGTS Mobius"),
("TOM.RADIX","radix branch","K x bit-index -> bit","Select one canonical key bit; repeated selections form a radix-trie path.","opcode 10","SCLP prefix refinement; binary tree"),
("TOM.HINGE","typed hinge","branch x state x map -> state","H=(pivot/state,map0,map1,invariant); runtime map0 is identity and map1 is the cell's declared delta plus optional orientation/sheet flip.","opcode 11","UGTS 3.6 hinge calculus"),
("TOM.LSYS","binary L-system step","branch x state -> state","Apply chirality-signed turn and dyadic velocity scaling, corresponding to F(T)->F(T/2)[+/-phi F(T/2)].","opcode 12","SCLP bounded binary L-system"),
("TOM.BRANCH","binary successor","bit x cell -> cell","i_(n+1)=next_i[bit].","automatic successor selection","1bit/BST/L-system chain"),
("TOM.TRANSITION","state patch","state x cell -> state","Execute exactly one opcode, normalize periodic fields, select successor, and update lineage.","CPU/GPU step","UGTS transition operator"),
("TOM.PROJECT","symbolic projection","state x tag -> tag","Emit a side-view pyramid, circle, sphere, action, class, or other downstream token without making projection the substrate.","opcode 13","projection operators Pi"),
("TOM.EMIT","deterministic output","state x payload -> state","Set the output token and emitted bit; optional halt is a program semantic, not a safety mode.","opcode 14","query output"),
("TOM.LINEAGE","replay lineage","state x cell x key -> u32","ell'=mix32(ell xor payload xor aux xor K_hi xor rotl(K_lo,7) xor branch xor cell_index).","automatic","UGTS lineage/persistence"),
("TOM.TRACE","explanation trace","execution -> records","Return ordered cell IDs/opcodes, branches, keys, residuals, outputs and lineage.","Python/C CLI","K36 deterministic trace"),
("TOM.ACTIVE","active-bit projection","integer -> set(bit positions)","A(n)={k | bit_k(n)=1}; the original numeric value is retained.","knowledge helper","19/binary source; M006,M008"),
("TOM.POPCOUNT","active-bit cardinality","bit set -> integer","Return the number of active positions in a finite binary word.","knowledge helper / integer popcount","19/binary source; M006,M008"),
("TOM.EQ","typed equality predicate","A x A -> bit","Return 1 exactly when two values of the same declared type are equal; the result is a branch bit, not an identity rewrite.","knowledge helper / branch predicate","UGTS feature-count comparison"),
("TOM.PASCAL2","Pascal parity","n,k -> bit","C(n,k) mod 2 defines a deterministic triangular occupancy pattern.","knowledge helper","Pascal/Sierpinski source"),
("TOM.PULSE","pulse geometry","count -> point/segment/m-gon","m declared pulses map to one point, a segment, a triangle for m=3, or a regular m-gon.","knowledge helper","UGTS 3.6 pulse geometry"),
("TOM.RULE","compiled rule","facts x predicates -> cell graph","Translate exact predicates into RADIX/CONE/SPHERE/HINGE branches and EMIT leaves.","compiler pattern","deterministic AI substitute"),
("TOM.QUERY","deterministic inference","program x state x ticks -> output,trace","Run the finite operator graph for the requested number of ticks or until an EMIT/HALT cell.","runtime entry point","query-first substrate"),
("TOM.ABI.STATE64","hot state record","16 words -> state","64-byte state: four coordinates, four velocities, orientation/sheet/branch/cell, lineage/output/residual/status.","C/WGSL/GLSL/OpenCL","GPU-native source ABI"),
("TOM.ABI.CELL48","LUT cell record","12 words -> instruction cell","48-byte cell: key, opcode/flags, four signed args, two successors, payload, aux.","C/WGSL/GLSL/OpenCL","SDF0 kinematic LUT realization"),
("TOM.BACKEND.CPU","portable CPU evaluator","TMG program -> state","Dependency-free Python oracle and C99 evaluator implement identical integer semantics.","tested","GPU-native CPU oracle"),
("TOM.BACKEND.GPU","portable GPU step","state[] x cell[] -> state[]","One invocation executes one TOMAGI transition using only 32-bit integer storage and bit operations.","WGSL, GLSL 450, OpenCL C","GPU-native source package"),
]

op_records=[]
for i,(oid,name,typ,definition,impl,source) in enumerate(operators,1):
    rec={"ordinal":i,"id":oid,"name":name,"signature":typ,"definition":definition,"implementation":impl,"source_basis":source}
    raw=json.dumps(rec,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    rec['content_hash']='sha256:'+hashlib.sha256(raw).hexdigest()
    op_records.append(rec)
(ROOT/'spec/operator_catalog.json').write_text(json.dumps({"schema":"TOMAGI-OPERATOR-CATALOG-1.0","count":len(op_records),"operators":op_records},indent=2,ensure_ascii=False)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/operator_catalog.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=op_records[0].keys());w.writeheader();w.writerows(op_records)

symbols=[
("D","finite domain of definable LUT keys","set of 64-bit keys"),
("d","content-addressed definition node","typed record"),
("q_n","TOMAGI state at tick n","State64"),
("rho","log-radius coordinate","20-bit periodic integer; decoded range profile [-20,0]"),
("theta","polar angle","18-bit periodic integer"),
("X","zero-based modular timeline tick","14-bit periodic integer"),
("phi","lower-case phase/hoop/hinge coordinate","12-bit periodic integer"),
("Phi","capital golden ratio","optional constant; never aliases runtime phi"),
("Delta q","first discrete difference","velocity"),
("Delta^2 q","second discrete difference","acceleration stored in a cell"),
("Delta^2 phi","change-of-change of lower-case phi","cell arg3 under KIN2"),
("K=(K_hi,K_lo)","contiguous 64-bit log-polar key","two u32 words"),
("LUT_Z","finite sorted table of SDF0 cells","Cell48[]"),
("Z_D","literal SDF0 zero-field","0 on D, bottom outside D"),
("P","one-bit parity reduction","popcount mod 2"),
("j","deterministic parity/jitter bit","0 or 1"),
("sigma","signed jitter selector","2j-1 in {-1,+1}"),
("T_c","cone slant length","real-valued compile-time geometry parameter"),
("alpha","cone half-angle","compile-time or quantized angular width"),
("C","cone relation/support","signed relation"),
("S","sphere/shell relation/support","signed relation"),
("W_K","Klein or half-turn wrap map","state transform"),
("b","branch bit","0 or 1"),
("i","compiled cell index","u32"),
("ell","lineage checksum","u32"),
("y","output token","u32"),
("Pi","projection/tag operator","symbolic downstream output"),
("bottom","undefined/non-member","not a numeric SDF value"),
]
sym_records=[{"symbol":a,"meaning":b,"type":c} for a,b,c in symbols]
(ROOT/'spec/symbol_table.json').write_text(json.dumps({"schema":"TOMAGI-SYMBOL-TABLE-1.0","count":len(sym_records),"symbols":sym_records},indent=2,ensure_ascii=False)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/symbol_table.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=sym_records[0].keys());w.writeheader();w.writerows(sym_records)

precedence={
"schema":"TOMAGI-PRECEDENCE-1.0",
"functional_macro":"Pi(Cone(LSYS(Branch(Klein(phi(KIN2(JIT1(LUT[SDF0](K)))))))))",
"right_to_left_execution":["TOM.SDF0","TOM.JIT1","TOM.KIN2","TOM.PHI","TOM.KLEIN","TOM.BRANCH","TOM.LSYS","TOM.CONE","TOM.PROJECT"],
"literal_cell_execution":["TOM.SDF0","TOM.JIT1","TOM.KIN2","TOM.PHI","TOM.KLEIN","TOM.HINGE","TOM.LSYS","TOM.CONE","TOM.PROJECT","TOM.EMIT"],
"serialized_order":[
{"phase":0,"name":"resolve","operators":["TOM.DEF","TOM.REF","TOM.SEQ"]},
{"phase":1,"name":"encode-and-fetch","operators":["TOM.INDEX0","TOM.LOGPOLAR","TOM.KEY.C","TOM.FETCH"]},
{"phase":2,"name":"literal-core","operators":["TOM.SDF0","TOM.PARITY","TOM.JIT1"]},
{"phase":3,"name":"kinematic-change-of-change","operators":["TOM.DELTA1","TOM.DELTA2","TOM.KIN2","TOM.PHI","TOM.TIME"]},
{"phase":4,"name":"topology","operators":["TOM.KLEIN","TOM.MOBIUS"]},
{"phase":5,"name":"branch-routing-and-hinges","operators":["TOM.RADIX","TOM.BRANCH","TOM.HINGE","TOM.TRANSITION"]},
{"phase":6,"name":"grammar","operators":["TOM.LSYS"]},
{"phase":7,"name":"relations","operators":["TOM.CONE","TOM.SWEEP","TOM.CIRCLE","TOM.SPHERE","TOM.OVERLAP"]},
{"phase":8,"name":"output-and-replay","operators":["TOM.PROJECT","TOM.EMIT","TOM.LINEAGE","TOM.TRACE"]}
],
"rule":"Functional notation composes right-to-left. Binary cell files execute one stored cell left-to-right per tick. Branch is realized by next0/next1 hinge routing, Pi by PROJECT, and EMIT terminates the serialized example. The stored sequence is authoritative."
}
(ROOT/'spec/precedence.json').write_text(json.dumps(precedence,indent=2)+"\n",encoding='utf-8',newline='\n')

schema={
"$schema":"https://json-schema.org/draft/2020-12/schema",
"$id":"urn:tomagi:1.0:schema",
"title":"TOMAGI 1.0 literal program",
"type":"object",
"required":["tomagi_version","entry"],
"anyOf":[
    {"required":["cells"]},
    {"required":["definitions"],"properties":{"definitions":{"minItems":1}}},
],
"properties":{
"$schema":{"type":"string"},"tomagi_version":{"const":"1.0.0"},"title":{"type":"string"},
"seed":{"$ref":"#/$defs/int"},"default_ticks":{"type":"integer","minimum":0},"flags":{"$ref":"#/$defs/int"},"entry":{"type":"string"},
"initial_state":{"$ref":"#/$defs/state"},"definitions":{"type":"array","items":{"$ref":"#/$defs/definition"}},
"cells":{"type":"array","minItems":1,"items":{"$ref":"#/$defs/cell"}}
},
"additionalProperties":True,
"$defs":{
"int":{"oneOf":[{"type":"integer"},{"type":"string","pattern":"^(0x[0-9A-Fa-f]+|[-+]?[0-9]+)$"}]},
"state":{"type":"object","additionalProperties":{"$ref":"#/$defs/int"}},
"key":{"oneOf":[{"type":"string","pattern":"^0x[0-9A-Fa-f]{1,16}$"},{"type":"object","properties":{"rho":{"$ref":"#/$defs/int"},"theta":{"$ref":"#/$defs/int"},"tick":{"$ref":"#/$defs/int"},"phi":{"$ref":"#/$defs/int"}},"additionalProperties":False}]},
"definition":{
    "type":"object",
    "required":["id","kind","domain","codomain","dependencies","parameters","content_hash"],
    "properties":{
        "id":{"type":"string"},"kind":{"type":"string"},"domain":{},"codomain":{},
        "evaluation_phase":{"type":"integer"},
        "dependencies":{"type":"array","items":{"type":"string"}},
        "parameters":{},"provenance":{},
        "content_hash":{"type":"string","pattern":"^sha256:[0-9a-f]{64}$"},
    },
    "additionalProperties":True,
    "allOf":[
        {
            "if":{"properties":{"kind":{"const":"literal_utf8"}},"required":["kind"]},
            "then":{
                "properties":{
                    "parameters":{"type":"object","required":["text"],"properties":{"text":{"type":"string"}}},
                    "dependencies":{"maxItems":0},
                }
            },
        },
        {
            "if":{"properties":{"kind":{"const":"literal_hex"}},"required":["kind"]},
            "then":{
                "properties":{
                    "parameters":{"type":"object","required":["hex"],"properties":{"hex":{"type":"string","pattern":"^(?:[0-9A-Fa-f]{2})*$"}}},
                    "dependencies":{"maxItems":0},
                }
            },
        },
        {
            "if":{"properties":{"kind":{"enum":["concat","repeat","authenticated_trace","select_records","project_fields","format_records"]}},"required":["kind"]},
            "then":{
                "properties":{
                    "parameters":{"type":"object","required":["dependency_hashes"],"properties":{"dependency_hashes":{"type":"array","items":{"type":"string","pattern":"^sha256:[0-9a-f]{64}$"}}}},
                }
            },
        },
        {
            "if":{"properties":{"kind":{"const":"repeat"}},"required":["kind"]},
            "then":{
                "properties":{
                    "parameters":{"required":["count"],"properties":{"count":{"type":"integer","minimum":0}}},
                    "dependencies":{"minItems":1,"maxItems":1},
                }
            },
        },
    ],
},
"cell":{"type":"object","required":["id","key"],"properties":{"id":{"type":"string"},"key":{"$ref":"#/$defs/key"},"definition_ref":{"type":"string"},"op":{"oneOf":[{"type":"string","enum":["NOP","SET","JIT1","KIN2","PHI","TIME","SDF0","CONE","SPHERE","KLEIN","RADIX","HINGE","LSYS","PROJECT","EMIT","HALT"]},{"type":"integer","minimum":0,"maximum":15}]},"flags":{"$ref":"#/$defs/int"},"args":{"type":"array","minItems":4,"maxItems":4,"items":{"$ref":"#/$defs/int"}},"next":{"type":"array","minItems":2,"maxItems":2,"items":{"type":"string"}},"payload":{"$ref":"#/$defs/int"},"aux":{"$ref":"#/$defs/int"}},"oneOf":[{"required":["definition_ref"]},{"required":["op","args","next"],"not":{"required":["definition_ref"]}}],"additionalProperties":False}
}}
schema["$defs"]["definition"]["allOf"].extend([
    {
        "if":{"properties":{"kind":{"const":"authenticated_trace"}},"required":["kind"]},
        "then":{"properties":{
            "parameters":{"type":"object","required":["trace_path","trace_sha256","program_path","program_sha256","source_path","source_sha256","source_definition_hashes","ticks","dependency_hashes"],"properties":{
                "trace_path":{"type":"string","minLength":1},
                "trace_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"},
                "program_path":{"type":"string","minLength":1},
                "program_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"},
                "source_path":{"type":"string","minLength":1},
                "source_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"},
                "source_definition_hashes":{"type":"array","minItems":1,"items":{"type":"string","pattern":"^sha256:[0-9a-f]{64}$"}},
                "ticks":{"type":"integer","minimum":0},
            }},
            "dependencies":{"minItems":1},
        }},
    },
    {
        "if":{"properties":{"kind":{"const":"select_records"}},"required":["kind"]},
        "then":{"properties":{
            "parameters":{"type":"object","properties":{
                "predicates":{"type":"array","items":{"type":"object","required":["field","operator","value"],"properties":{
                    "field":{"type":"string"},
                    "operator":{"enum":["eq","ne","lt","le","gt","ge"]},
                    "value":{"type":"integer"},
                }}},
                "start":{"type":"integer","minimum":0},
                "stop":{"type":["integer","null"],"minimum":0},
                "stride":{"type":"integer","minimum":1},
            }},
            "dependencies":{"minItems":1,"maxItems":1},
        }},
    },
    {
        "if":{"properties":{"kind":{"const":"project_fields"}},"required":["kind"]},
        "then":{"properties":{
            "parameters":{"type":"object","required":["fields"],"properties":{
                "fields":{"type":"array","minItems":1,"items":{"type":"object","required":["name","source"],"properties":{
                    "name":{"type":"string","pattern":"^[A-Za-z_][A-Za-z0-9_]*$"},
                    "source":{"type":"string"},
                    "numerator":{"type":"integer"},
                    "denominator":{"type":"integer","minimum":1},
                    "offset":{"type":"integer"},
                    "rounding":{"enum":["floor","trunc"]},
                }}},
            }},
            "dependencies":{"minItems":1,"maxItems":1},
        }},
    },
    {
        "if":{"properties":{"kind":{"const":"format_records"}},"required":["kind"]},
        "then":{"properties":{
            "parameters":{"type":"object","required":["record_template"],"properties":{
                "encoding":{"const":"utf-8"},
                "prefix":{"type":"string"},
                "record_template":{"type":"string"},
                "separator":{"type":"string"},
                "suffix":{"type":"string"},
                "index_start":{"type":"integer"},
                "materialization_profile":{"const":"tomagi-emit-bytes-be-v1"},
            }},
            "dependencies":{"minItems":1,"maxItems":1},
        }},
    },
])
(ROOT/'spec/tomagi.schema.json').write_text(json.dumps(schema,indent=2)+"\n",encoding='utf-8',newline='\n')

# Source register. The package-local register is the normal reproducible input.
# Original PDFs/ZIPs may optionally be supplied to refresh their hashes, but
# their absence must not make specification generation depend on a build host.
source_files=[
    ("SRC-A","1bit parity / lower-case phi / log-polar LUT / cone / Klein / L-system dialogue","1bit-parity-bit-lower-case-phi-jitter-log-encoded-polar-LUT-analytic-sweeping-cone-T-a-side-view-of-the-pyramid-a-circle-a-sphere-the-apex-binary-.pdf","Literal SDF0-in-LUT chain and precedence."),
    ("SRC-B","UGTS-KC 3.6.2 SCLP","UGTS_KC_3_6_2_SCLP_Tom_Klootwijk.pdf","Cone, log-polar kinematics, jitter, phi, Klein wrap, L-system, 64-bit keys."),
    ("SRC-C","UGTS-KC 3.6 literal referential substrate","UGTS_KC_3_6_Tom_Klootwijk.pdf","Definition records, hinges, operation order, active-bit and pulse examples."),
    ("SRC-D","21 Ben Burgers Strikes Back","21BenBurgersStrikesBackTelNetNiet.pdf","Zero-based timeline, split-phi fold, overlap lens and connector interpretation."),
    ("SRC-E","19 / binary threshold / Dutch phonetic dialogue","waarom heeft 19 drie lettergrepen en in binaire waarom het kantelpunt tussen 1 en 2 cijfers geometrisch.pdf","Active bits, pulse triangle, log-polar and Klein motifs."),
    ("SRC-F","Chronological Synthesis of the Spherical Substrate Line","Chronological Synthesis of the Spherical Substrate Line.pdf","Query-first relation, transition and lineage synthesis."),
    ("SRC-G","UGTS spatial distill and GSP4 package","ugts_spatial_distill_v0.1.0 (2).zip","211-mechanism catalog, CPU oracle, GPU ABI/shader sources and deterministic event authority."),
    ("SRC-H","TOMAGI literal seed genome","TOM_seed_genome_2026-09-01.txt","Authoritative TOM1 seed literal and root provenance for executable content-addressed definition genomes."),
]


def shipped_register() -> list[dict]:
    if not SHIPPED_REGISTER_PATH.is_file():
        raise FileNotFoundError(
            'shipped source register is missing: '
            f'{SHIPPED_REGISTER_PATH}. Restore it or set TOMAGI_SOURCE_ROOT to the original inputs.'
        )
    data=json.loads(SHIPPED_REGISTER_PATH.read_text(encoding='utf-8'))
    rows=data.get('sources',[])
    expected=[sid for sid,_,_,_ in source_files]
    if [row.get('id') for row in rows] != expected:
        raise ValueError('shipped source register does not contain the expected ordered SRC-A..SRC-H rows')
    return rows


source_root=optional_path('TOMAGI_SOURCE_ROOT')
if source_root is None:
    print('Using shipped source register; external source hash regeneration skipped.',file=sys.stderr)
    reg=shipped_register()
else:
    missing=[name for _,_,name,_ in source_files if not (source_root/name).is_file()]
    if missing:
        print(
            'TOMAGI_SOURCE_ROOT is incomplete; preserving the shipped source register. '
            f'Missing: {", ".join(missing)}',
            file=sys.stderr,
        )
        reg=shipped_register()
    else:
        print(f'Refreshing source hashes from TOMAGI_SOURCE_ROOT: {source_root}',file=sys.stderr)
        reg=[
            {"id":sid,"title":title,"file":name,"sha256":sha(source_root/name),"role":role}
            for sid,title,name,role in source_files
        ]
(ROOT/'sources/source_register.json').write_text(json.dumps({"schema":"TOMAGI-SOURCE-REGISTER-1.0","sources":reg},indent=2)+"\n",encoding='utf-8',newline='\n')

# Crosswalk of all 211 catalog mechanisms plus the 50 SCLP and 36 UGTS 3.6 definitions.
def map_mech(m):
    text=(m.get('name','')+' '+m.get('normalized_technical_definition','')+' '+m.get('domain','')).lower()
    out=[]
    def add(*ids):
        for x in ids:
            if x not in out: out.append(x)
    if any(k in text for k in ['definition','content-address','schema','typed state','finite grammar']): add('TOM.DEF','TOM.REF')
    if any(k in text for k in ['radix','binary','bit shift','left-shift','prefix','morton','packed fixed-width','active-bit','popcount']): add('TOM.RADIX','TOM.KEY.C')
    if 'active-bit' in text or 'hamming' in text or 'binary 19' in text: add('TOM.ACTIVE')
    if 'pascal' in text or 'sierpi' in text: add('TOM.PASCAL2')
    if 'pulse' in text or 'phonetic' in text: add('TOM.PULSE')
    if 'zero-based' in text: add('TOM.INDEX0')
    if 'jitter' in text or 'seeded stochastic' in text: add('TOM.JIT1')
    if 'parity' in text or 'one-bit' in text: add('TOM.PARITY')
    if 'log-polar' in text or 'log radius' in text or 'log-radius' in text or 'spherical chart' in text: add('TOM.LOGPOLAR')
    if 'cone' in text: add('TOM.CONE')
    if 'sweep' in text: add('TOM.SWEEP')
    if 'sphere' in text or 'spherical' in text: add('TOM.SPHERE')
    if 'sdf zero' in text or 'zero as event boundary' in text or 'implicit field' in text: add('TOM.SDF0')
    if 'overlap' in text or 'intersection' in text or 'lens' in text: add('TOM.OVERLAP')
    if 'klein' in text: add('TOM.KLEIN')
    if 'möbius' in text or 'mobius' in text: add('TOM.MOBIUS')
    if any(k in text for k in ['hinge','orientation','chirality','gluing','portal','sheet','lemniscate']): add('TOM.HINGE')
    if 'l-system' in text or 'grammar' in text: add('TOM.LSYS')
    if any(k in text for k in ['kinematic','velocity','acceleration','delta-t','torque']): add('TOM.KIN2')
    if 'time' in text or 'phase' in text or 'winding' in text: add('TOM.TIME','TOM.PHI')
    if any(k in text for k in ['branch','routing','route','hourglass','trident']): add('TOM.BRANCH')
    if any(k in text for k in ['event','transition','guard','root solve','commit']): add('TOM.TRANSITION')
    if any(k in text for k in ['lineage','persistence','novelty','replay','identity']): add('TOM.LINEAGE')
    if any(k in text for k in ['query','state_at','next_event','reachable']): add('TOM.QUERY')
    if 'projection' in m.get('domain','').lower() or any(k in text for k in ['render','screen','chromatic','cmyk','coverage']): add('TOM.PROJECT')
    if 'gpu-native' in m.get('domain','').lower() or 'performance/cache' in m.get('domain','').lower(): add('TOM.BACKEND.GPU')
    if 'cpu reference' in text: add('TOM.BACKEND.CPU')
    if 'audit' in m.get('domain','').lower() or 'risk' in m.get('domain','').lower(): add('TOM.TRACE')
    if 'physical hardware' in m.get('domain','').lower(): add('TOM.PROJECT')
    if not out: add('TOM.RULE')
    return ';'.join(out)

cross=[]
cat=json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
mechanisms=cat.get('mechanisms',[])
if len(mechanisms) != 211:
    raise ValueError(f'knowledge catalog must contain 211 mechanisms, found {len(mechanisms)}')
for m in mechanisms:
    cross.append({"source":"SRC-G:knowledge_catalog_1.1","source_id":m['mechanism_id'],"source_name":m['name'],"source_status":m.get('status',''),"tomagi_mapping":map_mech(m),"role":"condensed source mechanism"})

sclp=[
('sclp362.profile.packed-swept-cone-v1','packed SCLP profile','TOM.QUERY;TOM.CONE;TOM.LOGPOLAR'),('sclp362.type.symbol-separation-v1','overloaded-symbol separation','TOM.PHI;TOM.TIME'),('sclp362.type.lowercase-phi-circle-v1','lower-case phi as S1 coordinate','TOM.PHI'),('sclp362.type.delta-family-v1','typed delta family','TOM.DELTA1;TOM.DELTA2'),('sclp362.type.evidence-boundary-v1','source/normalization boundary','TOM.TRACE'),('sclp362.geometry.cone-slant-angle-v1','cone from slant length and half-angle','TOM.CONE'),('sclp362.geometry.finite-cone-sdf-v1','exact finite-cone signed distance','TOM.CONE'),('sclp362.geometry.cone-relation-class-v1','three-state cone relation','TOM.CONE'),('sclp362.geometry.sphere-sdf-v1','sphere relation','TOM.SPHERE'),('sclp362.geometry.paired-sphere-support-v1','two-sphere support pair','TOM.SPHERE;TOM.OVERLAP'),('sclp362.sweep.translation-family-v1','rigid translational cone family','TOM.SWEEP'),('sclp362.sweep.lipschitz-interval-v1','certified sweep interval','TOM.SWEEP'),('sclp362.sweep.zero-tangent-projector-v1','zero-surface tangent projection','TOM.SDF0;TOM.PROJECT'),('sclp362.logpolar.chart-v1','log-polar chart','TOM.LOGPOLAR'),('sclp362.logpolar.core-v1','explicit origin core','TOM.LOGPOLAR'),('sclp362.logpolar.metric-v1','conformal metric tensor','TOM.LOGPOLAR'),('sclp362.logpolar.exact-radial-step-v1','exact local radial increment','TOM.LOGPOLAR'),('sclp362.logpolar.jacobian-v1','log-polar Jacobian','TOM.LOGPOLAR;TOM.KIN2'),('sclp362.logpolar.velocity-v1','velocity transform','TOM.DELTA1;TOM.KIN2'),('sclp362.logpolar.acceleration-v1','change-of-change transform','TOM.DELTA2;TOM.KIN2'),('sclp362.logpolar.gradient-v1','gradient covector transform','TOM.LOGPOLAR'),('sclp362.jitter.deterministic-bit-v1','deterministic one-bit jitter','TOM.JIT1'),('sclp362.jitter.interval-guard-v1','jitter interval certificate','TOM.JIT1'),('sclp362.time.phase-clock-v1','linear-time phase clock','TOM.TIME'),('sclp362.time.winding-lineage-v1','winding lineage','TOM.TIME;TOM.LINEAGE'),('sclp362.topology.source-half-turn-v0','source half-turn bundle twist','TOM.MOBIUS'),('sclp362.topology.klein-reflection-v1','reflective Klein radial gluing','TOM.KLEIN'),('sclp362.topology.tangent-chirality-v1','tangent chirality map','TOM.KLEIN;TOM.HINGE'),('sclp362.topology.wrap-event-v1','topological wrap event','TOM.KLEIN;TOM.TRANSITION'),('sclp362.hinge.state-v1','hinge state','TOM.PHI;TOM.HINGE'),('sclp362.hinge.torque-model-v1','optional torque model','TOM.KIN2'),('sclp362.constraint.row-release-v1','missing-shackle row deletion','TOM.HINGE'),('sclp362.constraint.nullity-gain-v1','freedom-gain certificate','TOM.HINGE'),('sclp362.branch.binary-guard-v1','binary guard branch','TOM.BRANCH'),('sclp362.branch.no-chaos-inference-v1','deterministic binary branch','TOM.BRANCH;TOM.TRACE'),('sclp362.grammar.bounded-binary-lsystem-v1','bounded binary parametric L-system','TOM.LSYS'),('sclp362.grammar.chirality-automorphism-v1','chirality turn automorphism','TOM.LSYS;TOM.HINGE'),('sclp362.packing.quantize-20-18-14-12-v1','20/18/14/12 quantizer','TOM.KEY.C'),('sclp362.packing.contiguous-key-v1','contiguous field key','TOM.KEY.C'),('sclp362.packing.morton-key-v1','MSB round-robin Morton key','TOM.KEY.M'),('sclp362.packing.layout-separation-v1','key-layout separation','TOM.KEY.C;TOM.KEY.M'),('sclp362.index.prefix-refinement-v1','radix prefix refinement','TOM.RADIX'),('sclp362.index.radix-trie-v1','radix-2 trie','TOM.RADIX'),('sclp362.index.one-bit-payload-v1','one-bit payload','TOM.PARITY;TOM.BRANCH'),('sclp362.index.sparse-presence-accounting-v1','sparse presence accounting','TOM.FETCH'),('sclp362.metrics.cacheline-eight-keys-v1','eight raw keys per cache line','TOM.BACKEND.GPU'),('sclp362.metrics.nominal-width-audit-v1','nominal width audit','TOM.TRACE'),('sclp362.metrics.finite-capacity-v1','finite 2^64 key capacity','TOM.KEY.C'),('sclp362.query.direct-lookup-bound-v1','direct lookup','TOM.FETCH;TOM.QUERY'),('sclp362.query.ugts-handoff-v1','UGTS handoff','TOM.TRANSITION;TOM.LINEAGE')]
for sid,name,mapping in sclp: cross.append({"source":"SRC-B:SCLP-3.6.2","source_id":sid,"source_name":name,"source_status":"source catalog","tomagi_mapping":mapping,"role":"condensed source operator"})

k36_names=[
('K36-01','Literal definition node','TOM.DEF'),('K36-02','Content-addressed definition','TOM.DEF'),('K36-03','Explicit dependency edge','TOM.REF'),('K36-04','Versioned namespace','TOM.DEF'),('K36-05','Definition-instance separation','TOM.DEF'),('K36-06','Acyclic resolution rule','TOM.REF'),('K36-07','Typed implicit-field sign','TOM.SDF0'),('K36-08','Exact-SDF capability flag','TOM.SDF0'),('K36-09','Parametric curve and sweep','TOM.SWEEP'),('K36-10','Pulse polygon embedding','TOM.PULSE'),('K36-11','Radix shell chart','TOM.RADIX;TOM.LOGPOLAR'),('K36-12','Log-polar core chart','TOM.LOGPOLAR'),('K36-13','Explicit quotient/gluing map','TOM.KLEIN;TOM.MOBIUS'),('K36-14','Sheet-aware co-location','TOM.HINGE'),('K36-15','Orientation transport','TOM.HINGE;TOM.KLEIN'),('K36-16','Port and branch routing','TOM.BRANCH'),('K36-17','Split-merge lineage','TOM.LINEAGE'),('K36-18','Guarded topology change','TOM.TRANSITION'),('K36-19','Generic hinge tuple','TOM.HINGE'),('K36-20','Continuous planar hinge','TOM.HINGE'),('K36-21','Discrete parity hinge','TOM.PARITY;TOM.HINGE'),('K36-22','Connector hinge','TOM.HINGE;TOM.OVERLAP'),('K36-23','Non-commutative hinge chain','TOM.SEQ;TOM.HINGE'),('K36-24','Invariant subspace contract','TOM.HINGE'),('K36-25','Bounded Dutch number profile','TOM.RULE'),('K36-26','Syllable-pulse operator','TOM.PULSE'),('K36-27','Teen suffix hinge','TOM.HINGE'),('K36-28','En connector hinge','TOM.HINGE'),('K36-29','Spoken-place permutation','TOM.HINGE'),('K36-30','Feature-count comparison','TOM.ACTIVE;TOM.PULSE;TOM.RULE'),('K36-31','Phase-ordered evaluator','TOM.SEQ;TOM.QUERY'),('K36-32','Support-compatibility-guard discipline','TOM.CONE;TOM.QUERY'),('K36-33','Deterministic trace','TOM.TRACE'),('K36-34','Evidence disposition','TOM.TRACE'),('K36-35','Unknown-reference and cycle rejection','TOM.REF'),('K36-36','Package verification contract','TOM.TRACE')]
for sid,name,mapping in k36_names: cross.append({"source":"SRC-C:UGTS-3.6","source_id":sid,"source_name":name,"source_status":"source catalog","tomagi_mapping":mapping,"role":"condensed source operator"})

# Direct motifs from the remaining project documents. These rows make the
# document-level synthesis explicit rather than relying only on the upstream
# 211-entry catalog.
direct_motifs = [
    ("SRC-A:literal-chain", "A01", "SDF0 packed inside the log-polar LUT", "TOM.SDF0;TOM.FETCH;TOM.KEY.C"),
    ("SRC-A:literal-chain", "A02", "one-bit parity as the first branch-producing operator", "TOM.PARITY;TOM.JIT1;TOM.BRANCH"),
    ("SRC-A:literal-chain", "A03", "kinematic calculus stored in the LUT", "TOM.DELTA1;TOM.DELTA2;TOM.KIN2"),
    ("SRC-A:literal-chain", "A04", "analytic cone sweep followed by pyramid/circle/sphere projection", "TOM.CONE;TOM.SWEEP;TOM.PROJECT"),
    ("SRC-A:literal-chain", "A05", "binary L-system routing after parity and before projection", "TOM.LSYS;TOM.BRANCH;TOM.PROJECT"),
    ("SRC-A:literal-chain", "A06", "strict operator precedence of the chained prompt", "TOM.SEQ;TOM.QUERY"),
    ("SRC-D:ben-burger", "D01", "zero-based offset versus one-based ordinal", "TOM.INDEX0"),
    ("SRC-D:ben-burger", "D02", "split lower-case phi / double-D fold around a straight hinge", "TOM.PHI;TOM.HINGE"),
    ("SRC-D:ben-burger", "D03", "slight overlap interpreted as shared lens domain", "TOM.OVERLAP"),
    ("SRC-D:ben-burger", "D04", "one-dimensional timeline as an address sequence", "TOM.TIME;TOM.INDEX0"),
    ("SRC-E:19-dialogue", "E01", "radix digit thresholds at powers of the base", "TOM.RADIX"),
    ("SRC-E:19-dialogue", "E02", "19 equals binary 10011 with active positions 0,1,4", "TOM.ACTIVE"),
    ("SRC-E:19-dialogue", "E03", "three declared Dutch segments map to three pulses", "TOM.PULSE"),
    ("SRC-E:19-dialogue", "E04", "three pulses projected as a triangle while numeric identity remains 19", "TOM.PULSE;TOM.PROJECT"),
    ("SRC-E:19-dialogue", "E05", "log-encoded polar LUT with one-bit jitter and kinematic change-of-change", "TOM.LOGPOLAR;TOM.JIT1;TOM.KIN2"),
    ("SRC-E:19-dialogue", "E06", "Klein non-orientable wrap as chirality transport", "TOM.KLEIN;TOM.HINGE"),
    ("SRC-F:chronological-synthesis", "F01", "finite grammar generates a directly queryable relation state", "TOM.DEF;TOM.LSYS;TOM.QUERY"),
    ("SRC-F:chronological-synthesis", "F02", "local spherical or radial-angular supports organize relevance", "TOM.SPHERE;TOM.CONE;TOM.LOGPOLAR"),
    ("SRC-F:chronological-synthesis", "F03", "compatibility and relation crossing select the next transition", "TOM.RULE;TOM.TRANSITION"),
    ("SRC-F:chronological-synthesis", "F04", "identity persists by lineage rather than instantaneous coordinates", "TOM.LINEAGE"),
    ("SRC-F:chronological-synthesis", "F05", "projection is downstream and non-authoritative", "TOM.PROJECT"),
    ("SRC-F:chronological-synthesis", "F06", "state-at-time and next-event are primary query forms", "TOM.QUERY;TOM.TRACE"),
    ("SRC-H:seed-genome", "H01", "TOM1 seed literal is the root provenance value", "TOM.DEF;TOM.LINEAGE"),
    ("SRC-H:seed-genome", "H02", "arbitrary literal definitions are packed as a content-addressed dependency graph", "TOM.DEF;TOM.REF;TOM.SEQ"),
    ("SRC-H:seed-genome", "H03", "formal definition output lowers to deterministic emitted bytes", "TOM.DEF;TOM.EMIT;TOM.TRACE"),
]
for source, sid, name, mapping in direct_motifs:
    cross.append({"source":source,"source_id":sid,"source_name":name,"source_status":"direct document motif","tomagi_mapping":mapping,"role":"explicit document crosswalk"})

(ROOT/'spec/source_crosswalk.json').write_text(json.dumps({"schema":"TOMAGI-SOURCE-CROSSWALK-1.0","count":len(cross),"rows":cross},indent=2,ensure_ascii=False)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/source_crosswalk.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cross[0].keys());w.writeheader();w.writerows(cross)

# Keep an explicitly supplied external 211-entry catalog as a traceable input,
# while avoiding a pointless rewrite when the shipped catalog was selected.
if CATALOG_PATH != SHIPPED_CATALOG_PATH:
    (ROOT/'sources/ugts_knowledge_catalog_211.json').write_bytes(CATALOG_PATH.read_bytes())

print(json.dumps({"operators":len(op_records),"symbols":len(sym_records),"crosswalk":len(cross),"sources":len(reg)},indent=2))

# Exact fixed-width ABI tables.
opcode_rows = [
    {"code":0,"name":"NOP","effect":"No state mutation beyond lineage and successor selection."},
    {"code":1,"name":"SET","effect":"Set one State64 field selected by flags[3:0] to arg0."},
    {"code":2,"name":"JIT1","effect":"Derive a deterministic parity bit and add +/-arg0 to the selected field."},
    {"code":3,"name":"KIN2","effect":"Apply integer second-order update v'=v+args; q'=q+v'."},
    {"code":4,"name":"PHI","effect":"Advance lower-case phi modulo 2^12 and expose wrap/half-circle branch."},
    {"code":5,"name":"TIME","effect":"Advance zero-based modular tick modulo 2^14 and fold winding into lineage."},
    {"code":6,"name":"SDF0","effect":"Return literal zero relation for the current defined LUT cell."},
    {"code":7,"name":"CONE","effect":"Evaluate a quantized log-polar cone/support relation."},
    {"code":8,"name":"SPHERE","effect":"Evaluate a quantized radial/phi shell relation."},
    {"code":9,"name":"KLEIN","effect":"Apply reflective Klein or source half-turn radial wrap."},
    {"code":10,"name":"RADIX","effect":"Select one bit of the canonical 64-bit key."},
    {"code":11,"name":"HINGE","effect":"Apply map1 deltas and optional orientation/sheet flips when branch=1."},
    {"code":12,"name":"LSYS","effect":"Apply chirality-signed lower-case-phi turn and dyadic velocity scaling."},
    {"code":13,"name":"PROJECT","effect":"Set a symbolic downstream output token without halting."},
    {"code":14,"name":"EMIT","effect":"Set output token and emitted status; flag bit 0 may terminate the program."},
    {"code":15,"name":"HALT","effect":"Terminate the current state execution."},
]
(ROOT/'spec/opcode_table.json').write_text(json.dumps({"schema":"TOMAGI-OPCODES-1.0","opcodes":opcode_rows},indent=2)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/opcode_table.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=opcode_rows[0].keys()); w.writeheader(); w.writerows(opcode_rows)

state_names=['rho','theta','tick','phi','vrho','vtheta','vtick','vphi','orientation','sheet','branch','cell','lineage','output','residual','status']
state_types=['i32','i32','i32','i32','i32','i32','i32','i32','u32','u32','u32','u32','u32','u32','i32','u32']
state_notes=[
    'log-radius coordinate; canonical key uses modulo 2^20','polar angle; modulo 2^18','zero-based timeline tick; modulo 2^14','lower-case phase/hinge angle; modulo 2^12',
    'first difference of rho','first difference of theta','first difference of tick','first difference of phi',
    'orientation/chirality bit','sheet index','current branch bit','current cell index','deterministic replay checksum','symbolic output token','last signed relation residual','status bit field']
state_rows=[{'word':i,'byte_offset':i*4,'name':n,'type':t,'meaning':m} for i,(n,t,m) in enumerate(zip(state_names,state_types,state_notes))]
(ROOT/'spec/state64_layout.json').write_text(json.dumps({"schema":"TOMAGI-STATE64-1.0","size_bytes":64,"fields":state_rows},indent=2)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/state64_layout.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=state_rows[0].keys()); w.writeheader(); w.writerows(state_rows)

cell_names=['key_hi','key_lo','opcode','flags','arg0','arg1','arg2','arg3','next0','next1','payload','aux']
cell_types=['u32','u32','u32','u32','i32','i32','i32','i32','u32','u32','u32','u32']
cell_notes=['canonical key bits 63..32','canonical key bits 31..0','opcode 0..15','generic and opcode-specific flags','operator argument 0','operator argument 1','operator argument 2','operator argument 3','successor for branch 0','successor for branch 1','literal/output/provenance token','literal/hash salt/operator auxiliary']
cell_rows=[{'word':i,'byte_offset':i*4,'name':n,'type':t,'meaning':m} for i,(n,t,m) in enumerate(zip(cell_names,cell_types,cell_notes))]
(ROOT/'spec/cell48_layout.json').write_text(json.dumps({"schema":"TOMAGI-CELL48-1.0","size_bytes":48,"fields":cell_rows},indent=2)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/cell48_layout.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cell_rows[0].keys()); w.writeheader(); w.writerows(cell_rows)

status_rows=[
 {'bit':0,'mask':'0x00000001','name':'HALT','meaning':'execution has terminated'},
 {'bit':1,'mask':'0x00000002','name':'ZERO','meaning':'literal SDF0 relation was evaluated'},
 {'bit':2,'mask':'0x00000004','name':'WRAP','meaning':'odd topological radial wrap occurred'},
 {'bit':3,'mask':'0x00000008','name':'EMIT','meaning':'an output token was emitted'},
 {'bit':4,'mask':'0x00000010','name':'CONE','meaning':'last cone relation admitted the state'},
 {'bit':5,'mask':'0x00000020','name':'SPHERE','meaning':'last sphere relation admitted the state'},
 {'bit':6,'mask':'0x00000040','name':'REKEY_MISS','meaning':'address-derived lookup missed and explicit successor was used'},
 {'bit':7,'mask':'0x00000080','name':'PHI_WRAP','meaning':'lower-case phi crossed one or more modular turns'},
]
(ROOT/'spec/status_flags.json').write_text(json.dumps({"schema":"TOMAGI-STATUS-1.0","flags":status_rows},indent=2)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/status_flags.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=status_rows[0].keys()); w.writeheader(); w.writerows(status_rows)

# Morton schedule: output bit 63 first, round-robin over available MSB positions.
positions={'rho':19,'theta':17,'tick':13,'phi':11}
schedule=[]; out_bit=63
while any(v>=0 for v in positions.values()):
    for field in ('rho','theta','tick','phi'):
        source_bit=positions[field]
        if source_bit>=0:
            schedule.append({'ordinal':63-out_bit,'output_bit':out_bit,'field':field,'source_bit':source_bit})
            positions[field]-=1; out_bit-=1
(ROOT/'spec/morton_schedule_64.json').write_text(json.dumps({"schema":"TOMAGI-MORTON-SCHEDULE-1.0","count":len(schedule),"schedule":schedule},indent=2)+"\n",encoding='utf-8',newline='\n')
with (ROOT/'spec/morton_schedule_64.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=schedule[0].keys()); w.writeheader(); w.writerows(schedule)

key_layout={
 'schema':'TOMAGI-KEY-LAYOUT-1.0','total_bits':64,
 'fields':[
  {'name':'rho','bits':20,'contiguous_range':'63:44','states':2**20,'profile_decode':'[-20,0]'},
  {'name':'theta','bits':18,'contiguous_range':'43:26','states':2**18,'profile_decode':'[0,2*pi)'},
  {'name':'tick','bits':14,'contiguous_range':'25:12','states':2**14,'profile_decode':'zero-based modular ticks'},
  {'name':'phi','bits':12,'contiguous_range':'11:0','states':2**12,'profile_decode':'[0,2*pi)'},
 ],
 'contiguous_formula':'K=(q_rho<<44)|(q_theta<<26)|(q_tick<<12)|q_phi',
 'capacity':2**64,
 'reference_tuple':[949111,0,1920,227],
 'reference_contiguous':'0xe7b77000007800e3','reference_morton':'0x88823bb88099128b'
}
(ROOT/'spec/key_layout.json').write_text(json.dumps(key_layout,indent=2)+"\n",encoding='utf-8',newline='\n')
