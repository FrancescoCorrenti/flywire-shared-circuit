# Largest Shared Neural Circuit — FlyWire Qualification Challenge

Find the largest connected directed induced subgraph that is mutually isomorphic across three *Drosophila* connectome datasets (FAFB, BANC, Male CNS).

**Result: N = 4485 neurons, 5450 edges, 8 brain zones.**

## Requirements

- Python 3.10+
- pandas, networkx, numpy
- pyarrow (for `.feather` files)

```bash
pip install pandas networkx numpy pyarrow
```

Optional (for visualization):
```bash
pip install navis fafbseg matplotlib
```

## Input Data

The pipeline expects the following directory structure:

```
data/
├── fafb_783_edge_list.csv          # FAFB edge list (src,tgt)
├── banc_626_edge_list.csv          # BANC edge list (src,tgt)
├── mcns_0.9_edge_list.csv          # Male CNS edge list (src,tgt)
├── FAFB/
│   ├── classification.csv.gz       # super_class, side (from Codex)
│   └── consolidated_cell_types.csv.gz  # primary_type (from Codex)
├── BANC/
│   └── codex_annotations_flat_table.tab  # cell_type, super_class, side (from Codex)
└── MCNS/
    └── body-annotations-male-cns-v0.9-minconf-0.5.feather  # type, superclass, somaSide (from Neuprint)
```

**Edge lists** are the sole source of edges (provided by the challenge). Annotation files are used only to assign cell type and brain zone labels to neurons.

### Edge list format

Each edge list is a two-column CSV with header `pre,post` (or equivalent). Each row is a directed synaptic connection between two neuron IDs.

### Annotation formats

- **FAFB**: two gzipped CSVs from FlyWire Codex. `classification.csv.gz` provides `root_id, super_class, side`. `consolidated_cell_types.csv.gz` provides `root_id, primary_type`.
- **BANC**: tab-separated flat table from Codex with columns `pt_root_id, cell_type, super_class, side`.
- **MCNS**: Apache Feather file from Neuprint (Janelia) with columns `bodyId, flywireType, type, superclass, somaSide`.

## Pipeline

Run all steps from the project root directory.

### Step 1 — Build neuron tables

```bash
python src/01_dataset/build_dataset.py
```

Outputs `type_graphs/nodes_{FAFB,BANC,MCNS}.csv`: unified neuron → (zone, type, side) tables.

### Step 2 — Build conserved type graph

```bash
python src/02_type_graph/build_type_graph.py
python src/02_type_graph/build_multiplicity.py
```

Outputs `type_graphs/type_graph_inter.csv` and `type_graphs/type_graph_intra.csv`: directed type→type edges conserved across all three datasets, with cell-level multiplicity counts.

### Step 3 — Grow cell-level circuit

```bash
python src/03_grow/grow.py --template cand/all_types.csv --n-seeds 3 --n-workers 8 --worker-id 0 --free
```

Grows a circuit from diversified seeds using greedy expansion with isomorphism-preserving `try_add_triple`. Runs parallel workers, each producing a `.pkl` file in `type_graphs/runs_all_types/`.

**Key parameters:**
- `--template`: CSV listing conserved types (columns: `type, zone`)
- `--n-seeds`: number of seed edges per worker
- `--n-workers`: parallel processes per worker instance
- `--worker-id`: unique ID for this run (determines output filename)
- `--free`: unconstrained zone growth (recommended)

### Step 4 — Mega-merge workers

```bash
python src/04_merge/merge.py --template cand/all_types.csv --pkl-dir runs_all_types
```

Takes all `worker_*.pkl` files, uses the best as base, and iteratively merges others via bridge-cell search + direct merge + extend + saturate. Outputs `worker_099_mega.pkl` and `submission_mega.csv`.

### Step 5 — Verify and export

```bash
# Verify from pkl
python src/05_verify/verify.py --pkl type_graphs/runs_all_types/worker_099_mega.pkl

# Verify from CSV (independent, no project imports)
python src/05_verify/verify_csv.py --csv submission_mega.csv

# Export CSV from pkl
python src/05_verify/verify.py --pkl type_graphs/runs_all_types/worker_099_mega.pkl --csv submission.csv
```

Verification checks:
1. **No duplicates**: each neuron appears at most once per dataset
2. **Isomorphism**: induced edge sets in slot-space are identical across all three datasets
3. **Connectivity**: the slot graph is a single connected component
4. **Induced subgraph**: no real edge between selected neurons is missing

## Output Format

The submission CSV has three columns and N rows:

```csv
FAFB,BANC,MCNS
720575940623047194,720575941613082588,76821
...
```

Each row is a neuron triplet: the three cells correspond to the same "slot" in the shared circuit, meaning they have identical directed connectivity patterns in slot-space.

## Project Structure

```
src/
├── 01_dataset/        Build unified neuron annotation tables
├── 02_type_graph/     Build conserved type-level graph
├── 03_grow/           Core algorithm: greedy circuit growth
│   ├── circuit.py     Circuit class with try_add_triple
│   ├── cell_graph.py  Load cell-level graphs from edge lists
│   ├── grow.py        Main pipeline: parallel growth + merge
│   └── signatures.py  Signature-based saturation
├── 04_merge/          Mega-merge multiple worker results
└── 05_verify/         Verification and visualization tools
```

## Algorithm Summary

1. **Type correspondence assumption**: neurons match only if they share the same cell type across datasets.
2. **Conserved type graph**: keep only type→type edges present in all three datasets.
3. **Greedy cell-level growth**: starting from a seed edge, iteratively add neuron triplets that preserve isomorphism (identical induced edges in all three datasets) and connectivity.
4. **Signature saturation**: batch-add cells sharing the same external connectivity signature.
5. **Parallel workers + mega-merge**: run independent workers with diversified seeds, then merge results.

## Citation

If you use this code, please cite:

- Dorkenwald, S. et al. (2024). Neuronal wiring diagram of an adult brain. *Nature*, 634, 124–138.
- Azevedo, A. et al. (2024). Connectomic reconstruction of a female-adult *Drosophila* ventral nerve cord. *Nature*, 631, 360–368.
- Takemura, S. et al. (2024). A connectome of the male *Drosophila* ventral nerve cord. *eLife*, 13, RP97766.

## License

MIT
