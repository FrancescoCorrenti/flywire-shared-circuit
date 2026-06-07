"""
Genera un URL Neuroglancer con tutti i neuroni FAFB del circuito.
Usa fafbseg.flywire.encode_url per evitare il limite URL di Codex.

Uso:
  python codex_url.py --csv path/to/submission.csv
"""
import argparse, csv

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    a = ap.parse_args()

    # Load FAFB IDs
    ids = []
    with open(a.csv) as f:
        rd = csv.DictReader(f)
        for r in rd:
            ids.append(int(r["FAFB"].strip()))
    print(f"Loaded {len(ids)} FAFB root IDs")

    from fafbseg import flywire
    flywire.set_default_dataset("public")

    url = flywire.encode_url(ids)
    print(f"\nNeuroglancer URL ({len(url)} chars):\n")
    print(url)

    # Also save to file
    out = a.csv.replace(".csv", "_neuroglancer_url.txt")
    with open(out, "w") as f:
        f.write(url)
    print(f"\nSaved to {out}")

if __name__ == "__main__":
    main()
