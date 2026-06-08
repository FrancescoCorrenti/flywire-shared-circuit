# Largest Shared Neural Circuit - FlyWire Qualification Challenge

Francesco Correnti - June 2026

## Problem

The goal is to identify the largest directed induced subgraph that is isomorphic across three *Drosophila* connectome datasets - **FAFB** (female adult fly brain), **BANC** (female adult nerve cord & brain), and **Male CNS** - using the edge lists provided by the FlyWire challenge.

A valid solution consists of **N** neuron triplets `(f_i, b_i, m_i)` - one FAFB, one BANC, and one MCNS neuron per row - such that the three directed subgraphs induced by the selected neurons are identical in edge structure. The objective is to maximise **N**.

### Assumptions

In addition to the constraints imposed by the challenge, two assumptions are adopted:

1. **Type correspondence** - a neuron in one dataset can only match a neuron of the same cell type in another dataset.
2. **Connected graph** - the final graph should be a single connected component.

The challenge specification provides only the three synaptic edge lists. To assign neuronal labels, each graph is linked to publicly available annotation tables:

- **FAFB** and **BANC** - FlyWire tables: `super_class` defines the common class/brain-region vocabulary; `primary_type` and `cell_type` define the cell-type vocabulary.
- **Male CNS** - NeuPrint body metadata: `superclass` maps to the same class vocabulary; `flywireType/type` defines the cell type.

## Pipeline

### (1) Type graph and seed selection

For every pair of cell types `(A, B)`, the existence of at least one `A → B` edge in each dataset is checked. This yields a **type graph** of 5,116 cell types and ~45,000 directed edges, filtering out cell types (and their neurons) whose connectivity is not conserved across all three datasets - a necessary condition for any valid isomorphic subgraph given the type correspondence assumption.

For each intra-class pair `(A_C, B_C)` within a given class **C**, a seed score is computed as `deg(A_C) + deg(B_C)`, where `deg(·)` is the number of cell types connected by at least one edge to or from the given cell type in the type graph, favouring pairs with a large expansion frontier. Ties are broken by the minimum neuron-level multiplicity of the `A → B` edge across the three datasets.

### (2) Greedy cell-level growth

A circuit is grown from a seed edge by alternating two operators until no further progress is made.

- **Extend** adds neurons of new cell types. It selects a cell type from the frontier of the current circuit - a cell type not already in the circuit that has an edge in the type graph to at least one cell type already in the circuit - then searches for a neuron triplet (one per dataset) realizing that edge, checks whether its addition preserves isomorphism, and adds the triplet to the circuit.
- **Saturate** adds more neurons of cell types already present. Each neuron still outside the circuit is characterised by its **signature**: a list of (neuron in the circuit, edge direction) pairs for each synapse it has with a neuron in the circuit. Neurons of the same cell type whose signatures coincide across all three datasets can be added in batch, as they respect the constraints by construction.

### (3) Parallelism and merge

Eight independent workers grow circuits from diversified seeds (round-robin across classes). The best (higher **N**) worker result is taken as base; the remaining seven are merged via bridge-cell search and further extend/saturate cycles.

## Result

| Quantity | Value |
| --- | ---: |
| Neuron triplets (*N*) | 4,485 |
| Cell types | 673 |
| Directed edges | 5,450 |

The greedy approach converges to ~4,000-4,500 neurons independently of seed choice. Eight independent workers seeded from different classes produce consistent class proportions (±10 percentage points), suggesting this is near the structural limit imposed by cross-dataset edge divergence rather than an artefact of seed choice.

Biological interpretation, figures, and references are in [`science.md`](science.md).

## Limitations

1. **Type correspondence assumption.** Matching neurons only by cell type is a strong constraint: it makes the result sensitive to annotation quality and consistency across datasets.
2. **Greedy, non-optimal search.** The extend/saturate loop is greedy and order-dependent. Different seed choices converge to similar sizes (~4,000-4,500), but there is no guarantee that the global maximum has been reached.
3. **Single connected component.** Requiring connectivity may exclude valid isolated clusters of conserved neurons that are not reachable from the main component.

