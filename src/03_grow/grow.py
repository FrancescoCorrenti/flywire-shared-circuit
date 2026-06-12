"""
Zonal cell growth pipeline with parallelism.
Usage: python grow.py --template cand/all_types.csv --n-seeds 3 -j 8
"""
import os,sys,time,pickle,argparse,random,csv as csvmod
import networkx as nx
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
BASE=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TG=os.path.join(BASE,"type_graphs")
DATA=os.path.join(BASE,"data")
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from circuit import Circuit,DS,build_graphs
from signatures import external_signature,edge_pairs_for_types

_tg=pickle.load(open(os.path.join(TG,"_type_graph.pkl"),"rb"))
TYPE_EDGES=_tg["conserved"]
TYPE_ADJ=defaultdict(set)
for a,b in TYPE_EDGES:
    TYPE_ADJ[a].add(b); TYPE_ADJ[b].add(a)

EDGE_FILES={"FAFB":"fafb_783_edge_list.csv","BANC":"banc_626_edge_list.csv","MCNS":"mcns_0.9_edge_list.csv"}

def circuit_stats(C,G):
    """Count types and zones. Zones come from FAFB cells (not template type labels)."""
    types=Counter(C.slot_type[s] for s in C.slot_type)
    zones=Counter(G["FAFB"].nodes[C.slot2cell["FAFB"][s]]["zone"] for s in C.slot_type)
    return types,zones

def score(C,G):
    types,zones=circuit_stats(C,G)
    nz=sum(1 for z in zones if z and str(z)!="nan")
    tm2=types.get("Tm2",0)/max(C.nslot,1)
    return (nz,len(types),C.nslot,-tm2)

def print_status(tag,C,G):
    types,zones=circuit_stats(C,G)
    nz=sum(1 for z in zones if z and str(z)!="nan")
    print("  [%s] N=%d types=%d zones=%d %s"%(tag,C.nslot,len(types),nz,dict(zones)),flush=True)

def build_type_index(G):
    """Precompute {ds: {type: [cell_ids]}} to avoid full graph scans."""
    idx={d:defaultdict(list) for d in DS}
    for d in DS:
        g=G[d]
        for c in g:
            idx[d][g.nodes[c]["type"]].append(c)
    return idx

def batch_type_round(C,G,typ,type_idx):
    added=0
    by_sig={d:defaultdict(list) for d in DS}
    for d in DS:
        c2s=C.cell2slot[d]; g=G[d]
        for c in type_idx[d].get(typ,[]):
            if c in c2s: continue
            sig=external_signature(g,c,c2s)
            if not sig: continue
            by_sig[d][sig].append(c)
    for sig in set(by_sig["FAFB"])&set(by_sig["BANC"])&set(by_sig["MCNS"]):
        fa,fb,fm=by_sig["FAFB"][sig],by_sig["BANC"][sig],by_sig["MCNS"][sig]
        k=min(len(fa),len(fb),len(fm))
        ib=list(range(k)); im=list(range(k))
        random.shuffle(ib); random.shuffle(im)
        for i in range(k):
            tr={"FAFB":fa[i],"BANC":fb[ib[i]],"MCNS":fm[im[i]]}
            if C.try_add_triple(tr,typ,True): added+=1
    return added

def saturate_all(C,G,deadline,type_idx=None):
    total=0
    while time.time()<deadline:
        types=sorted(set(C.slot_type.values()))
        rd=0
        for typ in types:
            if time.time()>=deadline: break
            rd+=batch_type_round(C,G,typ,type_idx)
        total+=rd
        if rd==0: break
    return total

def extend_frontier_batch(C,G,typ_of,zone_of,deadline,diverse=False,only_zone=None,require_connected=True):
    """Add all possible types in a single pass."""
    adj,types=C.frontier_candidates(typ_of)
    if not types: return 0
    if only_zone:
        types=[t for t in types if zone_of.get(t)==only_zone]
        if not types: return 0
    in_circuit=set(C.slot_type.values())
    _,zones=circuit_stats(C,G)
    def prio(typ):
        new_type=typ not in in_circuit
        z=zone_of.get(typ,"?")
        zfill=zones.get(z,0)/max(C.nslot,1)
        type_conn=len(TYPE_ADJ.get(typ,set()) & in_circuit)
        if diverse:
            return (0 if new_type else 1, zfill, -type_conn, -len(adj["FAFB"].get(typ,[])))
        return (0 if new_type else 1, zfill, -type_conn, Counter(C.slot_type.values()).get(typ,0))
    ordered=sorted(types,key=prio)
    added=0
    for typ in ordered:
        if time.time()>=deadline: break
        fa=adj["FAFB"].get(typ,[]); fb=adj["BANC"].get(typ,[]); fm=adj["MCNS"].get(typ,[])
        if not fa or not fb or not fm: continue
        fa=list(fa); fb=list(fb); fm=list(fm)
        random.shuffle(fa); random.shuffle(fb); random.shuffle(fm)
        found=False
        for cf in fa[:30]:
            for cb in fb[:30]:
                for cm in fm[:30]:
                    if C.try_add_triple({"FAFB":cf,"BANC":cb,"MCNS":cm},typ,require_connected):
                        added+=1; found=True; break
                if found: break
            if found: break
    return added

def csp_saturate_type(C,G,typ,type_idx):
    added=0
    by_sig={d:defaultdict(list) for d in DS}
    for d in DS:
        g=G[d]; c2s=C.cell2slot[d]
        for c in type_idx[d].get(typ,[]):
            if c in c2s: continue
            sig=external_signature(g,c,c2s)
            if not sig: continue
            by_sig[d][sig].append(c)
    common_sigs=set(by_sig["FAFB"])&set(by_sig["BANC"])&set(by_sig["MCNS"])
    for sig in common_sigs:
        fa=by_sig["FAFB"][sig]; fb=by_sig["BANC"][sig]; fm=by_sig["MCNS"][sig]
        used_f=set(); used_b=set(); used_m=set()
        random.shuffle(fa); random.shuffle(fb); random.shuffle(fm)
        for cf in fa:
            if cf in used_f or cf in C.cell2slot["FAFB"]: continue
            for cb in fb:
                if cb in used_b or cb in C.cell2slot["BANC"]: continue
                for cm in fm:
                    if cm in used_m or cm in C.cell2slot["MCNS"]: continue
                    if C.try_add_triple({"FAFB":cf,"BANC":cb,"MCNS":cm},typ,True):
                        used_f.add(cf); used_b.add(cb); used_m.add(cm)
                        added+=1; break
                if cf in used_f: break
    return added

def csp_saturate_all(C,G,deadline,type_idx=None):
    total=0
    while time.time()<deadline:
        types=sorted(set(C.slot_type.values()))
        rd=0
        for typ in types:
            if time.time()>=deadline: break
            rd+=csp_saturate_type(C,G,typ,type_idx)
        total+=rd
        if rd==0: break
    return total

def merge_circuits(C1,C2,G):
    """Merge C2 into C1, maintaining connectivity."""
    added=0
    c1_types=set(C1.slot_type.values())
    slots=sorted(C2.slot_type.keys())
    def bridge_score(s):
        typ=C2.slot_type[s]
        conn=len(TYPE_ADJ.get(typ,set()) & c1_types)
        return -conn
    slots.sort(key=bridge_score)
    for s in slots:
        typ=C2.slot_type[s]
        tr={d:C2.slot2cell[d][s] for d in DS}
        if any(tr[d] in C1.cell2slot[d] for d in DS): continue
        if C1.try_add_triple(tr,typ,True):
            added+=1
            c1_types.add(typ)
    return added

def precompute_all_seeds(G,tset,zone_of):
    cnt={d:defaultdict(lambda:defaultdict(int)) for d in DS}
    print("  Precomputing seeds (scanning edges)...",flush=True)
    for d in DS:
        g=G[d]
        for u,v in g.edges():
            ta,tb=g.nodes[u]["type"],g.nodes[v]["type"]
            if ta in tset and tb in tset:
                za=zone_of.get(ta); zb=zone_of.get(tb)
                if za and za==zb and str(za)!="nan":
                    cnt[d][za][(ta,tb)]+=1
    all_seeds={}
    for z in set().union(*(cnt[d].keys() for d in DS)):
        common=set(cnt["FAFB"][z])&set(cnt["BANC"][z])&set(cnt["MCNS"][z])
        scored=[]
        for p in common:
            ta,tb=p
            degree=len(TYPE_ADJ.get(ta,set()))+len(TYPE_ADJ.get(tb,set()))
            mc=min(cnt[d][z][p] for d in DS)
            scored.append((p,degree,mc))
        scored.sort(key=lambda r:(-r[1],-r[2]))
        all_seeds[z]=[(p,mc) for p,_,mc in scored]
    print("  Seeds precomputed: %s"%{z:len(s) for z,s in all_seeds.items()},flush=True)
    return all_seeds

def find_seeds_zone(all_seeds,zone,top_n=10):
    candidates=all_seeds.get(zone,[])
    if not candidates: return []
    pool=[(i,p) for i,(p,_) in enumerate(candidates[:200])]
    out=[]; used_types=Counter()
    for _ in range(top_n):
        if not pool: break
        best_idx=min(range(len(pool)),
                     key=lambda j:(used_types[pool[j][1][0]]+used_types[pool[j][1][1]], pool[j][0]))
        rank,pair=pool.pop(best_idx)
        out.append(pair)
        used_types[pair[0]]+=1; used_types[pair[1]]+=1
    return out

# --- Worker globals ---
_W={}

def _worker_init(path,log_dir):
    import pandas as pd
    _,tset,_,G=build_graphs(path)
    typ_of={d:{c:G[d].nodes[c]["type"] for c in G[d]} for d in DS}
    tpl=pd.read_csv(path)
    zone_of=dict(zip(tpl.type,tpl.zone))
    type_idx=build_type_index(G)
    _W["G"]=G; _W["tset"]=tset; _W["typ_of"]=typ_of
    _W["zone_of"]=zone_of; _W["type_idx"]=type_idx
    _W["log_dir"]=log_dir

def _worker_job(args):
    zone,ta,tb,rand_seed=args
    random.seed(rand_seed)
    G,tset,typ_of,zone_of,type_idx=_W["G"],_W["tset"],_W["typ_of"],_W["zone_of"],_W["type_idx"]
    log_path=os.path.join(_W["log_dir"],"%s_%s_%s.log"%(zone,ta,tb))
    old_stdout=sys.stdout
    sys.stdout=open(log_path,"w",buffering=1)
    only=None if zone=="FREE" else zone
    try:
        print("Job: zone=%s seed=%s->%s rand=%d pid=%d"%(zone,ta,tb,rand_seed,os.getpid()),flush=True)
        C=grow_one_seed(G,tset,typ_of,zone_of,ta,tb,time.time()+86400,
                        diverse=False,type_idx=type_idx,only_zone=only)
        if C is None:
            print("RESULT: FAILED",flush=True)
            sys.stdout.close(); sys.stdout=old_stdout
            return None
        print("RESULT: N=%d types=%d"%(C.nslot,len(set(C.slot_type.values()))),flush=True)
    finally:
        if sys.stdout!=old_stdout:
            sys.stdout.close(); sys.stdout=old_stdout
    return {"zone":zone,"ta":ta,"tb":tb,"N":C.nslot,
            "slot2cell":dict(C.slot2cell),"E":{d:set(C.E[d]) for d in DS},
            "slot_type":dict(C.slot_type),"cell2slot":{d:dict(C.cell2slot[d]) for d in DS}}

def _rebuild_circuit(data,G):
    C=Circuit(G)
    C.slot2cell={d:dict(data["slot2cell"][d]) for d in DS}
    C.cell2slot={d:dict(data["cell2slot"][d]) for d in DS}
    C.E={d:set(data["E"][d]) for d in DS}
    C.slot_type=dict(data["slot_type"])
    C.nslot=len(C.slot_type)
    return C

def grow_one_seed(G,tset,typ_of,zone_of,type_a,type_b,deadline,
                  extend_bias=0.25,max_stall=5,diverse=False,type_idx=None,only_zone=None):
    pairs=edge_pairs_for_types(G,type_a,type_b,100)
    if not all(pairs[d] for d in DS): return None
    fa=pairs["FAFB"]; fb=pairs["BANC"]; fm=pairs["MCNS"]
    random.shuffle(fa); random.shuffle(fb); random.shuffle(fm)
    C=None
    for uf,vf in fa[:50]:
        for ub,vb in fb[:50]:
            for um,vm in fm[:50]:
                trial=Circuit(G)
                if not trial.try_add_triple({"FAFB":uf,"BANC":ub,"MCNS":um},type_a,False): continue
                if not trial.try_add_triple({"FAFB":vf,"BANC":vb,"MCNS":vm},type_b,True): continue
                C=trial; break
            if C: break
        if C: break
    if C is None: return None
    stall=0; cycle=0
    while time.time()<deadline and stall<max_stall:
        cycle+=1
        n0=C.nslot; t0=len(set(C.slot_type.values()))
        sa=saturate_all(C,G,deadline,type_idx)
        print("      cycle %d saturate: +%d -> N=%d"%(cycle,sa,C.nslot),flush=True)
        ca=csp_saturate_all(C,G,deadline,type_idx)
        print("      cycle %d csp_sat: +%d -> N=%d"%(cycle,ca,C.nslot),flush=True)
        ext=extend_frontier_batch(C,G,typ_of,zone_of,deadline,diverse,only_zone=only_zone)
        print("      cycle %d extend: +%d types"%(cycle,ext),flush=True)
        n1=C.nslot; t1=len(set(C.slot_type.values()))
        print("      cycle %d: N=%d (+%d) types=%d (+%d)%s"%(
            cycle,n1,n1-n0,t1,t1-t0," STALL" if n1==n0 and t1==t0 else ""),flush=True)
        if n1>n0 or t1>t0: stall=0
        else: stall+=1
    return C

def grow_zone(G,tset,typ_of,zone_of,zone,deadline,all_seeds=None,n_seeds=5,type_idx=None):
    seeds=find_seeds_zone(all_seeds,zone,n_seeds)
    if not seeds:
        print("    zone %s: no seeds"%zone,flush=True)
        return None
    print("    zone %s: %d seeds, growing..."%(zone,len(seeds)),flush=True)
    circuits=[]
    for i,(ta,tb) in enumerate(seeds):
        if time.time()>=deadline: break
        C=grow_one_seed(G,tset,typ_of,zone_of,ta,tb,deadline,diverse=False,type_idx=type_idx,only_zone=zone)
        if C is None:
            print("    zone %s seed %d/%d %s->%s: FAILED"%(zone,i+1,len(seeds),ta,tb),flush=True)
            continue
        print("    zone %s seed %d/%d %s->%s: N=%d"%(zone,i+1,len(seeds),ta,tb,C.nslot),flush=True)
        circuits.append(C)
    if not circuits: return None
    circuits.sort(key=lambda c:-c.nslot)
    main=circuits[0]
    for other in circuits[1:]:
        if time.time()>=deadline: break
        n0=main.nslot
        merge_circuits(main,other,G)
        saturate_all(main,G,deadline,type_idx)
        n1=main.nslot
        if n1>n0:
            print("    zone %s intra-merge: +%d -> N=%d"%(zone,n1-n0,n1),flush=True)
    return main

def find_bridge_cells(main,other,G,type_idx,deadline):
    main_types=set(main.slot_type.values())
    other_types=set(other.slot_type.values())
    bridge_types=[]
    for typ in TYPE_ADJ:
        if typ in main_types: continue
        adj=TYPE_ADJ[typ]
        to_main=adj & main_types
        to_other=adj & other_types
        if to_main and to_other:
            bridge_types.append((typ,len(to_main)+len(to_other)))
    bridge_types.sort(key=lambda x:-x[1])
    added=0
    for typ,_ in bridge_types[:50]:
        if time.time()>=deadline: break
        cands={d:[] for d in DS}
        for d in DS:
            g=G[d]; c2s=main.cell2slot[d]
            for c in type_idx[d].get(typ,[]):
                if c in c2s: continue
                has_adj=False
                for nb in list(g.successors(c))+list(g.predecessors(c)):
                    if nb in c2s: has_adj=True; break
                if has_adj: cands[d].append(c)
        if not cands["FAFB"] or not cands["BANC"] or not cands["MCNS"]: continue
        random.shuffle(cands["FAFB"]); random.shuffle(cands["BANC"]); random.shuffle(cands["MCNS"])
        found=False
        for cf in cands["FAFB"][:20]:
            for cb in cands["BANC"][:20]:
                for cm in cands["MCNS"][:20]:
                    if main.try_add_triple({"FAFB":cf,"BANC":cb,"MCNS":cm},typ,True):
                        added+=1; found=True; break
                if found: break
            if found: break
    return added

def merge_zone_circuits(zone_circuits,G,typ_of,zone_of,deadline,type_idx=None):
    if not zone_circuits: return None
    items=sorted(zone_circuits.items(),key=lambda kv:-kv[1].nslot)
    main_zone,main=items[0]
    print("  Base: zone %s, N=%d"%(main_zone,main.nslot),flush=True)
    others=items[1:]
    def merge_prio(kv):
        zone,circ=kv
        main_types=set(main.slot_type.values())
        circ_types=set(circ.slot_type.values())
        cross=sum(1 for t in circ_types for mt in main_types if (t,mt) in TYPE_EDGES or (mt,t) in TYPE_EDGES)
        return -cross
    others.sort(key=merge_prio)
    for zone,circ in others:
        if time.time()>=deadline: break
        stall=0; max_stall=3
        while time.time()<deadline and stall<max_stall:
            n0=main.nslot
            br=find_bridge_cells(main,circ,G,type_idx,deadline)
            if br>0:
                print("  Bridge cells zone %s: +%d -> N=%d"%(zone,br,main.nslot),flush=True)
            added=merge_circuits(main,circ,G)
            if added>0:
                print("  Direct merge zone %s: +%d -> N=%d"%(zone,added,main.nslot),flush=True)
            ext=extend_frontier_batch(main,G,typ_of,zone_of,deadline,diverse=True,require_connected=True)
            if ext>0:
                print("  Extend zone %s: +%d types -> N=%d"%(zone,ext,main.nslot),flush=True)
            saturate_all(main,G,deadline,type_idx)
            n1=main.nslot
            if n1>n0:
                print("  Merge round zone %s: N=%d (+%d)"%(zone,n1,n1-n0),flush=True)
                stall=0
            else:
                stall+=1
    return main

def verify_pkl(bd):
    same=bd["E"]["FAFB"]==bd["E"]["BANC"]==bd["E"]["MCNS"]
    sg=nx.DiGraph(); sg.add_nodes_from(range(bd["N"])); sg.add_edges_from(bd["E"]["FAFB"])
    conn=nx.number_connected_components(sg.to_undirected())==1
    s2c=bd["slot2cell"]
    induced_ok=True
    for ds in DS:
        real=set()
        with open(os.path.join(DATA,EDGE_FILES[ds])) as fh:
            rd=csvmod.reader(fh); next(rd)
            for row in rd: real.add((row[0].strip(),row[1].strip()))
        c2s={str(c):s for s,c in s2c[ds].items()}
        cells=set(c2s.keys())
        extra=0
        for ca in cells:
            for cb in cells:
                if ca!=cb and (ca,cb) in real:
                    sa,sb=c2s[ca],c2s[cb]
                    if (sa,sb) not in bd["E"][ds]: extra+=1
        if extra>0:
            print("  %s: %d extra induced edges"%(ds,extra),flush=True)
            induced_ok=False
        else:
            print("  %s: induced OK"%(ds),flush=True)
    return same,conn,induced_ok

def run(template_rel,n_seeds=3,n_jobs=8,worker_id=0,free=False):
    name=os.path.splitext(os.path.basename(template_rel))[0]
    path=template_rel if os.path.isabs(template_rel) else os.path.join(TG,template_rel)
    import pandas as pd

    print("Loading graphs in main process...",flush=True)
    _,tset,_,G=build_graphs(path)
    typ_of={d:{c:G[d].nodes[c]["type"] for c in G[d]} for d in DS}
    tpl=pd.read_csv(path)
    zone_of=dict(zip(tpl.type,tpl.zone))
    type_idx=build_type_index(G)
    zones_in_template=Counter(zone_of[t] for t in tset if t in zone_of)
    zones=sorted([z for z in zones_in_template if z and str(z)!="nan"],
                 key=lambda z:-zones_in_template[z])
    print("%d types, %d zones: %s"%(len(tset),len(zones),
          {z:zones_in_template[z] for z in zones}),flush=True)
    out_dir=os.path.join(TG,"runs_%s"%name)
    os.makedirs(out_dir,exist_ok=True)

    seeds_cache=os.path.join(out_dir,"_seeds_cache.pkl")
    if os.path.exists(seeds_cache):
        all_seeds=pickle.load(open(seeds_cache,"rb"))
        print("  Seeds loaded from cache",flush=True)
    else:
        all_seeds=precompute_all_seeds(G,tset,zone_of)
        pickle.dump(all_seeds,open(seeds_cache,"wb"))

    log_dir=os.path.join(out_dir,"logs")
    os.makedirs(log_dir,exist_ok=True)

    jobs=[]
    seed_counter=worker_id*10000
    if free:
        strong_zones=[z for z in zones if len(all_seeds.get(z,[]))>=50]
        print("  Free mode: seeds from strong zones: %s"%strong_zones,flush=True)
        zone_iters={}
        for z in strong_zones:
            seeds_z=find_seeds_zone(all_seeds,z,n_seeds)
            zone_iters[z]=iter(seeds_z)
        active_zones=list(strong_zones)
        while len(jobs)<n_seeds and active_zones:
            next_zones=[]
            for z in active_zones:
                if len(jobs)>=n_seeds: break
                try:
                    ta,tb=next(zone_iters[z])
                    jobs.append(("FREE",ta,tb,seed_counter))
                    seed_counter+=1
                    next_zones.append(z)
                except StopIteration:
                    pass
            active_zones=next_zones
    else:
        for zone in zones:
            zone_seeds=find_seeds_zone(all_seeds,zone,n_seeds)
            for ta,tb in zone_seeds:
                jobs.append((zone,ta,tb,seed_counter))
                seed_counter+=1

    mode_str="FREE (no zone filter)" if free else "%d zone x %d seeds"%(len(zones),n_seeds)
    print("\nPhase 1: %d jobs (%s), %d parallel workers"%(
        len(jobs),mode_str,n_jobs),flush=True)
    print("  Logs in: %s"%log_dir,flush=True)

    results=[]
    done_count=0
    if n_jobs>1:
        with ProcessPoolExecutor(max_workers=n_jobs,
                                 initializer=_worker_init,initargs=(path,log_dir)) as pool:
            futures={pool.submit(_worker_job,j):j for j in jobs}
            for fut in as_completed(futures):
                done_count+=1
                r=fut.result()
                j=futures[fut]
                if r is not None:
                    results.append(r)
                    print("  [%d/%d] zone %-20s %s->%s : N=%d"%(
                        done_count,len(jobs),r["zone"],r["ta"],r["tb"],r["N"]),flush=True)
                else:
                    print("  [%d/%d] zone %-20s %s->%s : FAILED"%(
                        done_count,len(jobs),j[0],j[1],j[2]),flush=True)
    else:
        _worker_init(path,log_dir)
        for j in jobs:
            done_count+=1
            r=_worker_job(j)
            if r is not None:
                results.append(r)
                print("  [%d/%d] zone %-20s %s->%s : N=%d"%(
                    done_count,len(jobs),r["zone"],r["ta"],r["tb"],r["N"]),flush=True)
            else:
                print("  [%d/%d] zone %-20s %s->%s : FAILED"%(
                    done_count,len(jobs),j[0],j[1],j[2]),flush=True)

    print("\nPhase 1 done: %d circuits from %d jobs"%(len(results),len(jobs)),flush=True)
    if not results:
        print("No circuits grown!",flush=True)
        return

    deadline=time.time()+86400

    if free:
        results.sort(key=lambda r:-r["N"])
        circuits=[_rebuild_circuit(r,G) for r in results]
        for i,r in enumerate(results):
            print("  circuit %d: N=%d (%s->%s)"%(i,r["N"],r["ta"],r["tb"]),flush=True)
        best=circuits[0]
        print("\nPhase 2: merge %d free circuits"%(len(circuits)),flush=True)
        print("  Base: N=%d"%(best.nslot),flush=True)
        for other in circuits[1:]:
            n0=best.nslot
            merge_circuits(best,other,G)
            sa=saturate_all(best,G,deadline,type_idx)
            n1=best.nslot
            if n1>n0:
                print("  merge: +%d -> N=%d"%(n1-n0,n1),flush=True)
        print_status("after merge",best,G)
    else:
        from collections import defaultdict as dd
        by_zone=dd(list)
        for r in results:
            by_zone[r["zone"]].append(r)
        zone_circuits={}
        for zone in zones:
            zr=by_zone.get(zone,[])
            if not zr: continue
            zr.sort(key=lambda r:-r["N"])
            circuits=[_rebuild_circuit(r,G) for r in zr]
            main=circuits[0]
            for other in circuits[1:]:
                n0=main.nslot
                merge_circuits(main,other,G)
                saturate_all(main,G,deadline,type_idx)
                n1=main.nslot
                if n1>n0:
                    print("  zone %s intra-merge: +%d -> N=%d"%(zone,n1-n0,n1),flush=True)
            zone_circuits[zone]=main
            print_status("zone %s"%zone,main,G)
        print("\nPhase 2: merge %d circuits"%(len(zone_circuits)),flush=True)
        best=merge_zone_circuits(zone_circuits,G,typ_of,zone_of,deadline,type_idx=type_idx)

    if best:
        print("\nPhase 3: final extend+saturate (stall-based)",flush=True)
        stall=0; max_stall=5; cycle=0
        while stall<max_stall:
            cycle+=1
            n0=best.nslot; t0=len(set(best.slot_type.values()))
            sa=saturate_all(best,G,deadline,type_idx)
            ca=csp_saturate_all(best,G,deadline,type_idx)
            ext=extend_frontier_batch(best,G,typ_of,zone_of,deadline,diverse=True)
            n1=best.nslot; t1=len(set(best.slot_type.values()))
            print("  cycle %d: sat+%d csp+%d ext+%d -> N=%d (+%d) types=%d (+%d)%s"%(
                cycle,sa,ca,ext,n1,n1-n0,t1,t1-t0," STALL" if n1==n0 and t1==t0 else ""),flush=True)
            if n1>n0 or t1>t0: stall=0
            else: stall+=1
        sc=score(best,G)
        print_status("done",best,G)
        print("  score=%s"%str(sc),flush=True)
        bd={"name":name,"template":template_rel,"worker":worker_id,
            "slot2cell":best.slot2cell,"E":best.E,"N":best.nslot,"score":sc}
        rpath=os.path.join(out_dir,"worker_%03d.pkl"%worker_id)
        pickle.dump(bd,open(rpath,"wb"))
        print("  saved %s"%rpath,flush=True)
        s2c_z=Counter()
        for s,c in best.slot2cell["FAFB"].items():
            s2c_z[G["FAFB"].nodes.get(c,{}).get("zone","?")]+=1
        print("  zones: %s"%dict(s2c_z),flush=True)
        print("\nVerifying...",flush=True)
        same,conn,induced_ok=verify_pkl(bd)
        print("  edges_identical=%s connected=%s induced=%s"%(same,conn,induced_ok),flush=True)
        if same and conn and induced_ok:
            csv_path=os.path.join(BASE,"submission_worker_%03d.csv"%worker_id)
            s2c=bd["slot2cell"]
            with open(csv_path,"w",newline="") as fh:
                w=csvmod.writer(fh)
                w.writerow(["FAFB","BANC","MCNS"])
                for s in sorted(s2c["FAFB"].keys()):
                    w.writerow([s2c["FAFB"][s],s2c["BANC"][s],s2c["MCNS"][s]])
            print("\nCSV WRITTEN: %s (%d rows)"%(csv_path,bd["N"]),flush=True)
        else:
            print("\nVERIFICATION FAILED - no CSV written",flush=True)

if __name__=="__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    ap=argparse.ArgumentParser()
    ap.add_argument("--template",required=True)
    ap.add_argument("--n-seeds",type=int,default=3)
    ap.add_argument("-j","--jobs",type=int,default=8,help="Parallel processes per worker")
    ap.add_argument("--worker-id",type=int,default=0)
    ap.add_argument("--free",action="store_true",help="Free growth without zone filter")
    a=ap.parse_args()
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(line_buffering=True)
    run(a.template,n_seeds=a.n_seeds,n_jobs=a.jobs,worker_id=a.worker_id,free=a.free)
