# Largest Shared Neural Circuit - FlyWire Qualification Challenge

Francesco Correnti - June 2026

## Problem

The goal is to identify the largest directed induced subgraph that is isomorphic across three *Drosophila* connectome datasets - **FAFB** (female adult fly brain), **BANC** (female adult nerve cord & brain), and **Male CNS** - using the edge lists provided by the FlyWire challenge.

A valid solution consists of **N** neuron triplets `(f_i, b_i, m_i)` - one FAFB, one BANC, and one MCNS neuron per row - such that the three directed subgraphs induced by the selected neurons are identical in edge structure. The objective is to maximise **N**.

### Assumptions

In addition to the constraints imposed by the challenge, two assumptions are adopted:

1. **Type correspondence** - a neuron in one dataset can only match a neuron of the same cell type in another dataset.
2. **Connected graph** - the final graph should be a single connected component.
  UPDATE: 08/06/26 - This second assumption is now listed as a requirement for the challenge.

The challenge specification provides only the three synaptic edge lists. To assign neuronal labels, each graph is linked to publicly available annotation tables:

| Dataset | File | Fields used |
|---------|------|-------------|
| FAFB | `classification.csv.gz` + `consolidated_cell_types.csv.gz` (FlyWire Codex) | `super_class` → class; `primary_type` → cell type; `side` → laterality |
| BANC | `codex_annotations_flat_table.tab` (FlyWire Codex) | `super_class` → class; `cell_type` → cell type; `side` → laterality |
| Male CNS | `body-annotations-male-cns-v0.9-minconf-0.5.feather` (NeuPrint/neuPrint+) | `superclass` → class; `flywireType` (fallback: `type`) → cell type; `somaSide` → laterality |

## Pipeline

### (1) Type graph and seed selection

For every pair of cell types `(A, B)`, the existence of at least one `A → B` edge in each dataset is checked. This yields a **type graph** of 5,116 cell types and ~45,000 directed edges, filtering out cell types (and their neurons) whose connectivity is not conserved across all three datasets - a necessary condition for any valid isomorphic subgraph given the type correspondence assumption.

For each intra-class pair `(A_C, B_C)` within a given class **C**, a seed score is computed as `deg(A_C) + deg(B_C)`, where `deg(·)` is the number of cell types connected by at least one edge to or from the given cell type in the type graph, favouring pairs with a large expansion frontier. Ties are broken by the minimum neuron-level multiplicity of the `A → B` edge across the three datasets.

### (2) Greedy cell-level growth

A circuit is grown from a seed edge by alternating two operators until no further progress is made.

- **Extend** adds neurons of new cell types. It selects a cell type from the frontier of the current circuit - a cell type not already in the circuit that has an edge in the type graph to at least one cell type already in the circuit - then searches for a neuron triplet (one per dataset) realizing that edge, checks whether its addition preserves isomorphism, and adds the triplet to the circuit.
- **Saturate** adds more neurons of cell types already present. Each neuron still outside the circuit is characterised by its **signature**: a list of (neuron in the circuit, edge direction) pairs for each synapse it has with a neuron in the circuit. Neurons of the same cell type whose signatures coincide across all three datasets can be added in batch, as they respect the constraints by construction.

### (3) Parallelism and merge

Each worker grows multiple circuits from diversified seeds (`--n-seeds`), one circuit per seed. Within a worker, each seed is grown independently using `-j` parallel processes (e.g. `-j 8` runs 8 seeds in parallel on separate CPU cores). The `--free` flag enables unconstrained growth: all classes are eligible for expansion at every step, rather than restricting each seed to a single class. Once all seeds are exhausted, the worker performs an **intra-worker merge**: the largest circuit is taken as base, and the others are folded in via repeated extend/saturate cycles. The worker outputs a single `.pkl` file.

Multiple workers are launched in parallel (`--worker-id 0, 1, 2, ...`), each producing an independent result. A separate **inter-worker mega-merge** (`merge.py`) then combines all worker outputs: the largest is taken as base, and each remaining worker's circuit is merged in via repeated extend/saturate cycles. The final result is written to `worker_099_mega.pkl` and exported as a CSV.

## Result

| Quantity | Value |
| --- | ---: |
| Neuron triplets (*N*) | 4,485 |
| Cell types | 673 |
| Directed edges | 5,450 |

The submitted result was obtained with 8 workers of 10 seeds each, using unconstrained growth (`--free`). The best individual seeds already converge to ~4,000 neurons (e.g. TmY5a → TmY5a reaches N = 4,242). Intra-worker and inter-worker merges together add ~250 neurons on top.

Different workers produce consistent class proportions (±10 percentage points), suggesting this is near the structural limit of the proposed method within a single worker.

Biological interpretation, figures, and references are in [`science.md`](science.md).

## Quickstart

### 1. Download data

Place the following files under `data/` (not included in this repository):

| Path | Source |
|------|--------|
| `data/fafb_783_edge_list.csv` | FlyWire challenge edge lists |
| `data/banc_626_edge_list.csv` | FlyWire challenge edge lists |
| `data/mcns_0.9_edge_list.csv` | FlyWire challenge edge lists |
| `data/FAFB/classification.csv.gz` | FlyWire Codex — FAFB annotations |
| `data/FAFB/consolidated_cell_types.csv.gz` | FlyWire Codex — FAFB cell types |
| `data/BANC/codex_annotations_flat_table.tab` | FlyWire Codex — BANC annotations |
| `data/MCNS/body-annotations-male-cns-v0.9-minconf-0.5.feather` | NeuPrint — Male CNS annotations |

### 2. Install dependencies

```bash
pip install networkx pandas pyarrow
```

### 3. Run the pipeline

```bash
# Build neuron annotation tables
python src/01_dataset/build_dataset.py

# Build the conserved type graph and multiplicity tables
python src/02_type_graph/build_type_graph.py
python src/02_type_graph/build_multiplicity.py

# Grow circuits — launch multiple workers (each in a separate terminal)
# Each worker grows independently from diversified seeds; more workers = better merge
python src/03_grow/grow.py --template cand/all_types.csv --n-seeds 5 -j 8 --worker-id 0 --free
python src/03_grow/grow.py --template cand/all_types.csv --n-seeds 5 -j 8 --worker-id 1 --free
# ... repeat with --worker-id 2, 3, etc.

# Merge all worker results into the best circuit
python src/04_merge/merge.py --template cand/all_types.csv --pkl-dir runs_all_types

# Verify and export CSV
python src/05_verify/verify.py --pkl type_graphs/runs_all_types/worker_099_mega.pkl --csv submission.csv
```

The final `submission.csv` contains N rows of `(fafb_id, banc_id, mcns_id)` triplets.

## Limitations

1. **Type correspondence assumption.** Matching neurons only by cell type is a strong constraint: it makes the result sensitive to annotation quality and consistency across datasets.
2. **Greedy, non-optimal search.** The extend/saturate loop is greedy and order-dependent. Different seed choices converge to similar sizes (~4,000-4,500), but there is no guarantee that the global maximum has been reached.
3. **Single connected component.** Requiring connectivity may exclude valid isolated clusters of conserved neurons that are not reachable from the main component.
4. **Naive merge strategy.** The current merge simply transfers cells from smaller circuits into the largest one via extend/saturate. Independent seeds produce substantially different circuits with many disjoint neurons, but the merge fails to incorporate most of them because extend/saturate can only add cells that are directly compatible with the base circuit's current state.

