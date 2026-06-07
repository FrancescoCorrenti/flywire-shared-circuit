"""
Takes N worker pkl files, rebuilds Circuits, merges everything into the best one.

Usage:
  python merge.py --template cand/all_types.csv --pkl-dir runs_all_types
"""
import os,sys,time,pickle,argparse,random,csv as csvmod,glob
import networkx as nx
from collections import Counter,defaultdict
import pandas as pd

BASE=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TG=os.path.join(BASE,"type_graphs")
DATA=os.path.join(BASE,"data")
sys.path.insert(0,os.path.join(BASE,"src","03_grow"))
from circuit import Circuit,DS,build_graphs
from grow import (merge_circuits,saturate_all,csp_saturate_all,
                        extend_frontier_batch,build_type_index,find_bridge_cells,
                        score,print_status,verify_pkl,TYPE_ADJ,TYPE_EDGES)


def rebuild_circuit(data,G):
    C=Circuit(G)
    C.slot2cell={ds:dict(data["slot2cell"][ds]) for ds in DS}
    C.cell2slot={ds:{c:s for s,c in C.slot2cell[ds].items()} for ds in DS}
    C.E={ds:set(data["E"][ds]) for ds in DS}
    C.slot_type={}
    for s,c in C.slot2cell["FAFB"].items():
        C.slot_type[s]=G["FAFB"].nodes[c]["type"]
    C.nslot=len(C.slot_type)
    return C


def mega_merge(template_rel,pkl_dir,base_worker=None):
    path=template_rel if os.path.isabs(template_rel) else os.path.join(TG,template_rel)

    print("Loading graphs...",flush=True)
    _,tset,_,G=build_graphs(path)
    typ_of={d:{c:G[d].nodes[c]["type"] for c in G[d]} for d in DS}
    tpl=pd.read_csv(path)
    zone_of=dict(zip(tpl.type,tpl.zone))
    type_idx=build_type_index(G)
    print("Graphs loaded.",flush=True)

    pkl_path=os.path.join(TG,pkl_dir)
    files=sorted(glob.glob(os.path.join(pkl_path,"worker_*.pkl")))
    files=[f for f in files if "mega" not in os.path.basename(f)]
    workers=[]
    for f in files:
        d=pickle.load(open(f,"rb"))
        wid=int(os.path.basename(f).replace("worker_","").replace(".pkl",""))
        workers.append((wid,d))
        print("  w%d: N=%d score=%s"%(wid,d["N"],d.get("score","n/a")),flush=True)

    if not workers: print("No pkl files found"); return

    if base_worker is not None:
        base_idx=next((i for i,(wid,_) in enumerate(workers) if wid==base_worker),None)
        if base_idx is None: print("Worker %d not found"%base_worker); return
    else:
        base_idx=max(range(len(workers)),key=lambda i:workers[i][1]["N"])

    base_wid,base_d=workers[base_idx]
    main=rebuild_circuit(base_d,G)
    print("\nBase: worker %d, N=%d"%(base_wid,main.nslot),flush=True)
    print_status("base",main,G)

    deadline=time.time()+86400
    others=[(wid,d) for i,(wid,d) in enumerate(workers) if i!=base_idx]
    others.sort(key=lambda x:-x[1]["N"])

    for wid,wd in others:
        other=rebuild_circuit(wd,G)
        n0=main.nslot
        stall=0
        while stall<3:
            nn0=main.nslot
            br=find_bridge_cells(main,other,G,type_idx,deadline)
            added=merge_circuits(main,other,G)
            ext=extend_frontier_batch(main,G,typ_of,zone_of,deadline,diverse=True)
            saturate_all(main,G,deadline,type_idx)
            nn1=main.nslot
            if nn1>nn0: stall=0
            else: stall+=1
        n1=main.nslot
        delta=n1-n0
        if delta>0:
            print("  +w%d: +%d -> N=%d"%(wid,delta,n1),flush=True)
        else:
            print("  +w%d: 0 -> N=%d"%(wid,n1),flush=True)

    print("\nFinal extend+saturate...",flush=True)
    stall=0
    while stall<8:
        n0=main.nslot; t0=len(set(main.slot_type.values()))
        saturate_all(main,G,deadline,type_idx)
        csp_saturate_all(main,G,deadline,type_idx)
        extend_frontier_batch(main,G,typ_of,zone_of,deadline,diverse=True)
        n1=main.nslot; t1=len(set(main.slot_type.values()))
        print("  N=%d (+%d) types=%d (+%d)"%(n1,n1-n0,t1,t1-t0),flush=True)
        if n1>n0 or t1>t0: stall=0
        else: stall+=1

    sc=score(main,G)
    print_status("MEGA-MERGE DONE",main,G)
    print("score=%s"%str(sc),flush=True)

    bd={"name":"mega_merge","template":template_rel,"worker":99,
        "slot2cell":main.slot2cell,"E":main.E,"N":main.nslot,"score":sc,
        "slot_type":dict(main.slot_type)}
    out_pkl=os.path.join(pkl_path,"worker_099_mega.pkl")
    pickle.dump(bd,open(out_pkl,"wb"))
    print("Saved: %s"%out_pkl,flush=True)

    print("\nVerifying...",flush=True)
    same,conn,induced_ok=verify_pkl(bd)
    print("edges_identical=%s connected=%s induced=%s"%(same,conn,induced_ok),flush=True)

    if same and conn and induced_ok:
        csv_path=os.path.join(BASE,"submission_mega.csv")
        with open(csv_path,"w",newline="") as fh:
            w=csvmod.writer(fh)
            w.writerow(["FAFB","BANC","MCNS"])
            for s in sorted(main.slot2cell["FAFB"].keys()):
                w.writerow([main.slot2cell["FAFB"][s],main.slot2cell["BANC"][s],main.slot2cell["MCNS"][s]])
        print("\nCSV WRITTEN: %s (%d rows)"%(csv_path,main.nslot),flush=True)
    else:
        print("\nVERIFICATION FAILED",flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--template",required=True)
    ap.add_argument("--pkl-dir",required=True)
    ap.add_argument("--base",type=int,default=None)
    a=ap.parse_args()
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(line_buffering=True)
    mega_merge(a.template,a.pkl_dir,a.base)
