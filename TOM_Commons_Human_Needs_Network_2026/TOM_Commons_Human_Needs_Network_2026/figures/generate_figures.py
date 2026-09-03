from pathlib import Path
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Wedge, FancyArrowPatch
from matplotlib.path import Path as MplPath
import numpy as np

OUT = Path(__file__).resolve().parent
NAVY = '#103847'
TEAL = '#149B9B'
GOLD = '#BE8A00'
PURPLE = '#6E3E86'
RED = '#B3413B'
GREEN = '#3D7334'
BLUE = '#356D9C'
LIGHT = '#EDF5F6'
INK = '#17252B'
GRAY = '#64747A'
PALE = '#F7FAFA'

plt.rcParams.update({'font.family':'DejaVu Sans','figure.facecolor':'white','axes.facecolor':'white'})

def save(fig, name):
    fig.savefig(OUT/name, dpi=220, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)

# 1 cover constellation
fig, ax = plt.subplots(figsize=(13.5, 8.3))
fig.patch.set_facecolor(NAVY); ax.set_facecolor(NAVY); ax.set_xlim(-7.3,7.3); ax.set_ylim(-4.4,4.4); ax.axis('off')
ax.add_patch(Circle((0,0),1.55,facecolor=TEAL,edgecolor='white',lw=2.5))
ax.text(0,.25,'TOM',ha='center',va='center',fontsize=34,fontweight='bold',color='white')
ax.text(0,-.32,'COMMONS',ha='center',va='center',fontsize=21,fontweight='bold',color='white')
ax.text(0,-.78,'human-needs network',ha='center',fontsize=11,color='white')
items=[('KNOWLEDGE',-5.1,2.7,GOLD),('COMMUNICATION',0,3.35,PURPLE),('HEALTH',5.1,2.7,RED),('CIVIC LIFE',6.0,-.25,BLUE),('MANUFACTURING',4.2,-3.0,GREEN),('WORK + MARKET',-4.2,-3.0,GOLD),('HOME + MOBILITY',-6.0,-.25,TEAL),('LEARNING + CULTURE',0,-3.65,PURPLE)]
for label,x,y,c in items:
    ax.add_patch(FancyBboxPatch((x-1.25,y-.42),2.5,.84,boxstyle='round,pad=.12,rounding_size=.18',facecolor='white',edgecolor=c,lw=2))
    ax.text(x,y,label,ha='center',va='center',fontsize=10,fontweight='bold',color=c)
    ax.add_patch(FancyArrowPatch((0,0),(x*.72,y*.72),arrowstyle='-',lw=1.5,color='white',alpha=.75,connectionstyle='arc3,rad=.08'))
ax.text(0,4.03,'A PROTOCOL, NOT A PLATFORM MONOPOLY',ha='center',fontsize=18,fontweight='bold',color='white')
ax.text(0,-4.18,'Search -> evidence -> decision -> service -> fabrication -> lineage',ha='center',fontsize=13,color='#CDE8E8')
save(fig,'cover_constellation.png')

# 2 platform to protocol
fig, ax = plt.subplots(figsize=(13.5,7.6)); ax.set_xlim(0,14); ax.set_ylim(0,8); ax.axis('off')
ax.text(2.5,7.55,'PLATFORM-ERA STACK',ha='center',fontsize=18,fontweight='bold',color=RED)
ax.text(11.1,7.55,'TOM COMMONS FEDERATION',ha='center',fontsize=18,fontweight='bold',color=TEAL)
left=[('One account',6.6),('One ranking authority',5.5),('Central data lake',4.4),('Ad auction',3.3),('Opaque AI synthesis',2.2),('Vendor-shaped action',1.1)]
for label,y in left:
    ax.add_patch(FancyBboxPatch((.8,y-.32),3.4,.64,boxstyle='round,pad=.08',facecolor='#FFF1F0',edgecolor=RED,lw=1.5))
    ax.text(2.5,y,label,ha='center',va='center',fontsize=10,color=INK)
right=[('Portable identity + credentials',6.6),('Selectable public ranking packs',5.5),('Personal / community data vaults',4.4),('Separated disclosed sponsorship',3.3),('AI as cited proposal',2.2),('Permissioned action + lineage',1.1)]
for label,y in right:
    ax.add_patch(FancyBboxPatch((9.0,y-.32),4.2,.64,boxstyle='round,pad=.08',facecolor='#ECFAF8',edgecolor=TEAL,lw=1.5))
    ax.text(11.1,y,label,ha='center',va='center',fontsize=10,color=INK)
ax.add_patch(FancyArrowPatch((4.6,4),(8.55,4),arrowstyle='-|>',mutation_scale=20,lw=3,color=GOLD))
ax.text(6.58,4.45,'migration by open adapters',ha='center',fontsize=11,fontweight='bold',color=GOLD)
ax.text(6.58,3.63,'not a forced overnight replacement',ha='center',fontsize=9,color=GRAY)
ax.text(7,0.25,'The unit of change is a service protocol and evidence contract, not a new corporate brand.',ha='center',fontsize=12,fontweight='bold',color=NAVY)
save(fig,'platform_to_protocol.png')

# 3 human needs genome wheel
fig, ax = plt.subplots(figsize=(10.5,10.5)); ax.set_aspect('equal'); ax.axis('off'); ax.set_xlim(-5.6,5.6); ax.set_ylim(-5.6,5.6)
rings=[(0,1.25,TEAL,'PERSON'),(1.25,2.45,GOLD,'HOUSEHOLD'),(2.45,3.7,PURPLE,'COMMUNITY'),(3.7,5.0,NAVY,'PLANET + FRONTIER')]
for inner,outer,c,label in rings:
    ax.add_patch(Wedge((0,0),outer,0,360,width=outer-inner,facecolor=c,alpha=.13,edgecolor=c,lw=1.5))
    ax.text(0,outer-.18,label,ha='center',va='top',fontsize=9,fontweight='bold',color=c)
core=[('identity',0,0.62),('agency',0,-.18),('dignity',0,-.72)]
for text,x,y in core: ax.text(x,y,text.upper(),ha='center',va='center',fontsize=12 if text=='agency' else 9,fontweight='bold',color=NAVY)
items=[
('air + water',0),('food',25),('shelter',50),('health',75),('safety',100),('privacy',125),('communication',150),('family',175),('mobility',200),('learning',225),('work',250),('money',275),('culture',300),('civic voice',325)]
for label,deg in items:
    rad=math.radians(90-deg); r=3.12; x=r*math.cos(rad); y=r*math.sin(rad)
    ax.text(x,y,label,ha='center',va='center',fontsize=8.8,color=INK,bbox=dict(boxstyle='round,pad=.25',fc='white',ec=TEAL,lw=.8))
outer=[('science',15),('infrastructure',65),('environment',115),('justice',165),('manufacturing',215),('biological futures',265),('space',315)]
for label,deg in outer:
    rad=math.radians(90-deg); r=4.45; x=r*math.cos(rad); y=r*math.sin(rad)
    ax.text(x,y,label.upper(),ha='center',va='center',fontsize=8.5,fontweight='bold',color=NAVY)
ax.text(0,-5.3,'TOM-HUMAN-NEEDS is a versioned domain pack over the frozen kernel - not a new kernel.',ha='center',fontsize=10,color=RED)
save(fig,'human_needs_genome.png')

# 4 query flow
fig, ax = plt.subplots(figsize=(14,7)); ax.set_xlim(0,15); ax.set_ylim(0,7.2); ax.axis('off')
labels=[('NEED',.8,5.0,GOLD),('CONSENT + CONTEXT',2.7,5.0,TEAL),('SUPPORT',5.1,5.0,PURPLE),('COMPATIBILITY',7.1,5.0,PURPLE),('EVIDENCE GRAPH',9.45,5.0,BLUE),('RANKING PACK',11.75,5.0,GOLD),('ANSWER BUNDLE',13.9,5.0,TEAL)]
for i,(lab,x,y,c) in enumerate(labels):
    w=1.45 if i not in (1,4,6) else 1.85
    ax.add_patch(FancyBboxPatch((x-w/2,y-.45),w,.9,boxstyle='round,pad=.08',facecolor='white',edgecolor=c,lw=2))
    ax.text(x,y,lab,ha='center',va='center',fontsize=8.5,fontweight='bold',color=c)
    if i<len(labels)-1:
        nx=labels[i+1][1]; ax.add_patch(FancyArrowPatch((x+w/2,y),(nx-(1.85 if i+1 in (1,4,6) else 1.45)/2,y),arrowstyle='-|>',mutation_scale=13,lw=1.5,color=GRAY))
ax.add_patch(FancyBboxPatch((4.1,2.3),6.8,1.35,boxstyle='round,pad=.12',facecolor=LIGHT,edgecolor=NAVY,lw=1.7))
ax.text(7.5,3.25,'AI PROPOSAL LAYER',ha='center',fontsize=12,fontweight='bold',color=NAVY)
ax.text(7.5,2.77,'summarise, translate, compare, simulate, draft - never silently promote',ha='center',fontsize=10,color=INK)
ax.add_patch(FancyArrowPatch((9.45,4.53),(8.7,3.68),arrowstyle='-|>',mutation_scale=15,lw=1.5,color=NAVY))
ax.add_patch(FancyArrowPatch((10.3,3.0),(13.25,4.55),arrowstyle='-|>',mutation_scale=15,lw=1.5,color=NAVY))
ax.add_patch(FancyBboxPatch((3.25,.45),8.5,.9,boxstyle='round,pad=.1',facecolor='#F6F0FA',edgecolor=PURPLE,lw=1.6))
ax.text(7.5,.9,'ACTION -> PERMISSION -> EVENT -> TRANSITION -> LINEAGE',ha='center',va='center',fontsize=11,fontweight='bold',color=PURPLE)
ax.add_patch(FancyArrowPatch((13.9,4.55),(11.6,1.4),arrowstyle='-|>',mutation_scale=16,lw=1.7,color=PURPLE,connectionstyle='arc3,rad=-.15'))
ax.text(7.5,6.65,'A query ends in a proof-carrying answer or an explicitly governed action - not an opaque click.',ha='center',fontsize=14,fontweight='bold',color=NAVY)
save(fig,'query_flow.png')

# 5 federation topology
fig, ax = plt.subplots(figsize=(13.5,8)); ax.set_xlim(0,14); ax.set_ylim(0,8.2); ax.axis('off')
ax.text(7,7.75,'FEDERATED HUMAN-NEEDS INFRASTRUCTURE',ha='center',fontsize=19,fontweight='bold',color=NAVY)
# central public commons
ax.add_patch(FancyBboxPatch((5.1,3.35),3.8,1.5,boxstyle='round,pad=.15',facecolor=LIGHT,edgecolor=TEAL,lw=2.5))
ax.text(7,4.35,'PUBLIC COMMONS',ha='center',fontsize=14,fontweight='bold',color=TEAL)
ax.text(7,3.86,'open indexes, schemas, maps, research,\nrights floor, public service definitions',ha='center',fontsize=9.5,color=INK)
nodes=[('PERSONAL VAULTS',1.7,6.25,TEAL),('COMMUNITY NODES',7,6.25,PURPLE),('PUBLIC INSTITUTIONS',12.3,6.25,BLUE),('SERVICE PROVIDERS',1.7,1.65,GOLD),('MANUFACTURING + LABS',7,1.65,GREEN),('INDEPENDENT AUDITORS',12.3,1.65,RED)]
for lab,x,y,c in nodes:
    ax.add_patch(FancyBboxPatch((x-1.45,y-.55),2.9,1.1,boxstyle='round,pad=.1',facecolor='white',edgecolor=c,lw=2))
    ax.text(x,y,lab,ha='center',va='center',fontsize=9.3,fontweight='bold',color=c)
    ax.add_patch(FancyArrowPatch((7,4.1),(x,y),arrowstyle='<->',mutation_scale=11,lw=1.2,color=GRAY,connectionstyle='arc3,rad=.08'))
ax.text(7,.43,'Federation and read-only replication are compatible with the design; the current repaired kernel does not itself supply cross-host consensus.',ha='center',fontsize=9.5,color=RED)
save(fig,'federation_topology.png')

# 6 service constellation
fig, ax = plt.subplots(figsize=(14,8.5)); ax.set_xlim(0,14); ax.set_ylim(0,9); ax.axis('off')
ax.text(7,8.55,'TOM COMMONS SERVICE CONSTELLATION',ha='center',fontsize=19,fontweight='bold',color=NAVY)
cols=[1.65,4.3,7,9.7,12.35]
rows=[6.7,4.45,2.2]
services=[
('QUERY','search + evidence',GOLD),('LINK','mail + chat + meetings',PURPLE),('WORKSPACE','docs + files + calendar',BLUE),('ATLAS','maps + mobility + place',TEAL),('MEDIA','video + news + culture',RED),
('LEARN','education + research',PURPLE),('MARKET','work + trade + payments',GOLD),('CIVIC','rights + public services',BLUE),('HEALTH','care + wellbeing',RED),('HOME','family + household',TEAL),
('COMPUTE','cloud + developer tools',BLUE),('FOUNDRY','physical manufacturing',GREEN),('BIOFOUNDRY','biological research',GREEN),('HABITAT','infrastructure + climate',TEAL),('FRONTIER','space + future systems',PURPLE)]
for idx,(name,sub,c) in enumerate(services):
    x=cols[idx%5]; y=rows[idx//5]
    ax.add_patch(FancyBboxPatch((x-1.13,y-.66),2.26,1.32,boxstyle='round,pad=.1',facecolor='white',edgecolor=c,lw=2))
    ax.text(x,y+.16,name,ha='center',va='center',fontsize=11,fontweight='bold',color=c)
    ax.text(x,y-.28,sub,ha='center',va='center',fontsize=7.8,color=INK)
ax.text(7,.52,'Shared identity, data vaults, evidence, permissions, accessibility, translation, lineage and open standards run through every module.',ha='center',fontsize=10.5,fontweight='bold',color=NAVY)
save(fig,'service_constellation.png')

# 7 manufacturing bridge
fig, ax = plt.subplots(figsize=(14,7.5)); ax.set_xlim(0,14); ax.set_ylim(0,7.7); ax.axis('off')
ax.text(7,7.25,'FROM HUMAN NEED TO DIGITAL, PHYSICAL OR BIOLOGICAL OUTCOME',ha='center',fontsize=18,fontweight='bold',color=NAVY)
stages=[('NEED',.9,GOLD),('DISCOVERY',2.45,TEAL),('DEFINITION',4.15,PURPLE),('SIMULATION',5.85,BLUE),('EVIDENCE',7.5,BLUE),('PROMOTION',9.15,GOLD),('FABRICATION',10.9,GREEN),('INSPECTION',12.55,RED),('LINEAGE',13.65,PURPLE)]
for i,(lab,x,c) in enumerate(stages):
    ax.add_patch(Circle((x,4.5),.48,facecolor='white',edgecolor=c,lw=2.3))
    ax.text(x,4.5,str(i+1),ha='center',va='center',fontsize=11,fontweight='bold',color=c)
    ax.text(x,3.72,lab,ha='center',fontsize=8.5,fontweight='bold',color=c,rotation=0)
    if i<len(stages)-1:
        ax.add_patch(FancyArrowPatch((x+.5,4.5),(stages[i+1][1]-.5,4.5),arrowstyle='-|>',mutation_scale=12,lw=1.4,color=GRAY))
outputs=[('DIGITAL\nsoftware, media, models',3.1,1.45,BLUE),('PHYSICAL\nparts, homes, machines',7,1.45,GREEN),('BIOLOGICAL\ntissues, organs, living systems',10.9,1.45,RED)]
for lab,x,y,c in outputs:
    ax.add_patch(FancyBboxPatch((x-1.35,y-.55),2.7,1.1,boxstyle='round,pad=.1',facecolor='white',edgecolor=c,lw=2))
    ax.text(x,y,lab,ha='center',va='center',fontsize=9.2,fontweight='bold',color=c)
    ax.add_patch(FancyArrowPatch((9.15,4.0),(x,2.05),arrowstyle='-|>',mutation_scale=13,lw=1.2,color=c,connectionstyle='arc3,rad=0'))
ax.text(7,6.35,'TOM governs identity, evidence and acceptance. External physics, machines and biology determine whether the phenotype works.',ha='center',fontsize=11.5,color=INK)
save(fig,'manufacturing_bridge.png')

# 8 governance model
fig, ax = plt.subplots(figsize=(13.5,8)); ax.set_xlim(0,14); ax.set_ylim(0,8.2); ax.axis('off')
ax.text(7,7.72,'GOVERNANCE AND ECONOMIC CONSTITUTION',ha='center',fontsize=19,fontweight='bold',color=NAVY)
ax.add_patch(Circle((7,4.15),1.35,facecolor=LIGHT,edgecolor=NAVY,lw=2.4))
ax.text(7,4.35,'HUMAN\nAGENCY',ha='center',va='center',fontsize=16,fontweight='bold',color=NAVY)
ax.text(7,3.55,'portable rights + appeal',ha='center',fontsize=8.5,color=INK)
items=[('RIGHTS FLOOR','privacy, access, due process',7,6.5,TEAL),('MEMBER GOVERNANCE','people + communities',3.1,5.75,PURPLE),('PUBLIC STEWARDSHIP','libraries, schools, cities',2.4,2.55,BLUE),('OPEN MARKET','competing service providers',7,1.05,GOLD),('INDEPENDENT AUDIT','security, bias, finance',11.6,2.55,RED),('FORKABILITY','exit without losing data',10.9,5.75,GREEN)]
for title,sub,x,y,c in items:
    ax.add_patch(FancyBboxPatch((x-1.5,y-.52),3,1.04,boxstyle='round,pad=.1',facecolor='white',edgecolor=c,lw=2))
    ax.text(x,y+.15,title,ha='center',va='center',fontsize=9.5,fontweight='bold',color=c)
    ax.text(x,y-.22,sub,ha='center',va='center',fontsize=7.9,color=INK)
    ax.add_patch(FancyArrowPatch((7,4.15),(x,y),arrowstyle='<->',mutation_scale=11,lw=1.1,color=GRAY,connectionstyle='arc3,rad=.1'))
ax.text(7,.25,'Public goods + member fees + metered compute + service contracts + visibly separated sponsorship; no hidden attention auction.',ha='center',fontsize=10,color=NAVY,fontweight='bold')
save(fig,'governance_economics.png')

# 9 roadmap timeline
fig, ax = plt.subplots(figsize=(14,8)); ax.set_xlim(0,14); ax.set_ylim(0,8); ax.axis('off')
ax.text(7,7.55,'TRANSITION ROADMAP: REPLACE FUNCTIONS, NOT PEOPLE',ha='center',fontsize=19,fontweight='bold',color=NAVY)
ax.plot([1,13],[4.2,4.2],color=NAVY,lw=3)
phases=[('0-6 months','local evidence search\n+ personal vault',1.3,TEAL),('6-18 months','communications + workspace\n+ open maps',3.55,PURPLE),('18-36 months','community federation\n+ market + civic pilots',5.8,BLUE),('3-5 years','public utility nodes\n+ manufacturing bridges',8.05,GOLD),('5-10 years','regional commons\n+ health/research integration',10.35,GREEN),('10+ years','frontier foundries\n+ habitat and biological programmes',12.65,RED)]
for i,(when,desc,x,c) in enumerate(phases):
    ax.add_patch(Circle((x,4.2),.24,facecolor=c,edgecolor='white',lw=1.5,zorder=3))
    if i%2==0:
        y=5.2; va='bottom'; line_y=4.45
    else:
        y=3.2; va='top'; line_y=3.95
    ax.plot([x,x],[line_y,y-(.1 if va=='bottom' else -.1)],color=c,lw=1.4)
    ax.text(x,y,when,ha='center',va=va,fontsize=11,fontweight='bold',color=c)
    ax.text(x,y+(.5 if va=='bottom' else -.5),desc,ha='center',va=va,fontsize=8.7,color=INK)
ax.text(7,.55,'Every phase must preserve portability, user data exit, explicit ranking, independent audit and the frozen TOM kernel boundary.',ha='center',fontsize=10.5,fontweight='bold',color=NAVY)
save(fig,'roadmap_timeline.png')

# 10 personal journey
fig, ax = plt.subplots(figsize=(14,7.6)); ax.set_xlim(0,14); ax.set_ylim(0,7.8); ax.axis('off')
ax.text(7,7.35,'ONE LIFE, ONE PORTABLE CONTEXT, MANY INDEPENDENT SERVICES',ha='center',fontsize=18,fontweight='bold',color=NAVY)
ax.add_patch(FancyBboxPatch((.65,3.0),2.2,1.45,boxstyle='round,pad=.15',facecolor=LIGHT,edgecolor=TEAL,lw=2))
ax.text(1.75,3.95,'PERSONAL VAULT',ha='center',fontsize=12,fontweight='bold',color=TEAL)
ax.text(1.75,3.48,'identity, preferences,\nrecords, permissions',ha='center',fontsize=9,color=INK)
journeys=[('Find reliable care',4.2,5.6,RED),('Learn a new skill',7.0,5.6,PURPLE),('Start a small business',9.8,5.6,GOLD),('Move or travel',4.2,2.0,TEAL),('Join a civic decision',7.0,2.0,BLUE),('Make or repair a product',9.8,2.0,GREEN),('Research a frontier idea',12.35,3.8,PURPLE)]
for lab,x,y,c in journeys:
    ax.add_patch(FancyBboxPatch((x-1.05,y-.45),2.1,.9,boxstyle='round,pad=.1',facecolor='white',edgecolor=c,lw=1.8))
    ax.text(x,y,lab,ha='center',va='center',fontsize=8.8,fontweight='bold',color=c)
    ax.add_patch(FancyArrowPatch((2.85,3.72),(x-1.08,y),arrowstyle='-|>',mutation_scale=11,lw=1.1,color=GRAY,connectionstyle='arc3,rad=.08'))
ax.text(7,.55,'The person can change providers without abandoning identity, history or rights - the relationship graph belongs to the person and the commons.',ha='center',fontsize=10.5,fontweight='bold',color=NAVY)
save(fig,'portable_life_context.png')

print('generated figures in', OUT)
