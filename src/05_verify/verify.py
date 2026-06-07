"""
Verify and/or export CSV from a pkl file.

Usage:
  python verify.py --pkl path/to/worker.pkl                    # verify only
  python verify.py --pkl path/to/worker.pkl --csv out.csv      # verify + CSV
  python verify.py --pkl path/to/worker.pkl --csv out.csv --no-verify  # CSV only
"""
import os,sys,pickle,argparse,csv as csvmod
import networkx as nx

BASE=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA=os.path.join(BASE,"data")
DS=["FAFB","BANC","MCNS"]
EDGE_FILES={"FAFB":"fafb_783_edge_list.csv","BANC":"banc_626_edge_list.csv","MCNS":"mcns_0.9_edge_list.csv"}


def verify(bd):
    """Verify isomorphism (identical edges across 3), connectivity, induced subgraph."""
    print("Verifying N=%d ..."%bd["N"],flush=True)

    # 1. Isomorphism: slot-space edges identical across 3 datasets
    same=bd["E"]["FAFB"]==bd["E"]["BANC"]==bd["E"]["MCNS"]
    print("  Edges identical across datasets: %s"%same,flush=True)

    # 2. Connectivity
    sg=nx.DiGraph()
    sg.add_nodes_from(range(bd["N"]))
    sg.add_edges_from(bd["E"]["FAFB"])
    n_cc=nx.number_connected_components(sg.to_undirected())
    conn=n_cc==1
    print("  Connected: %s (%d components)"%(conn,n_cc),flush=True)

    # 3. Induced subgraph: no real edge between selected cells is missing from E
    s2c=bd["slot2cell"]
    induced_ok=True
    for ds in DS:
        print("  Checking induced subgraph %s ..."%ds,end=" ",flush=True)
        real=set()
        with open(os.path.join(DATA,EDGE_FILES[ds])) as fh:
            rd=csvmod.reader(fh); next(rd)
            for row in rd:
                real.add((row[0].strip(),row[1].strip()))
        c2s={str(c):s for s,c in s2c[ds].items()}
        cells=set(c2s.keys())
        extra=0
        for ca in cells:
            for cb in cells:
                if ca!=cb and (ca,cb) in real:
                    sa,sb=c2s[ca],c2s[cb]
                    if (sa,sb) not in bd["E"][ds]:
                        extra+=1
        if extra>0:
            print("%d extra induced edges — FAIL"%extra,flush=True)
            induced_ok=False
        else:
            print("OK",flush=True)

    ok=same and conn and induced_ok
    print("\nRESULT: %s"%("PASS" if ok else "FAIL"),flush=True)
    return ok


def write_csv(bd,csv_path):
    """Write the deliverable CSV (3 columns x N rows)."""
    s2c=bd["slot2cell"]
    with open(csv_path,"w",newline="") as fh:
        w=csvmod.writer(fh)
        w.writerow(["FAFB","BANC","MCNS"])
        for s in sorted(s2c["FAFB"].keys()):
            w.writerow([s2c["FAFB"][s],s2c["BANC"][s],s2c["MCNS"][s]])
    print("CSV written: %s (%d rows)"%(csv_path,bd["N"]),flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--pkl",required=True,help="Path to circuit pkl file")
    ap.add_argument("--csv",default=None,help="Output CSV path (optional)")
    ap.add_argument("--no-verify",action="store_true",help="Skip verification, CSV only")
    a=ap.parse_args()

    bd=pickle.load(open(a.pkl,"rb"))
    print("Loaded: N=%d score=%s"%(bd["N"],bd.get("score","n/a")),flush=True)

    if not a.no_verify:
        ok=verify(bd)
        if a.csv:
            if ok:
                write_csv(bd,a.csv)
            else:
                print("Verification failed — CSV not written",flush=True)
                sys.exit(1)
    elif a.csv:
        write_csv(bd,a.csv)
    else:
        print("Nothing to do (--no-verify without --csv)",flush=True)
