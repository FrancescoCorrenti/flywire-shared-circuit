# Largest Shared Neural Circuit - Biological Interpretation

FlyWire Qualification Challenge, June 2026 - Francesco Correnti

## Definitions

- **Circuit** - the largest connected directed induced subgraph found to be isomorphic across the three datasets (FAFB, BANC, Male CNS). It contains N = 4,485 neuron triplets.
- **Cell type** - a neuronal identity label (e.g. Mi1, KCab) shared across datasets; neurons of the same cell type are treated as interchangeable for matching purposes.
- **Class** - a coarse brain-region category to which each cell type belongs. Five classes appear in the circuit:
${\color[RGB]{68,119,170}\textbf{optic\ lobe\ (OL)}}$ · ${\color[RGB]{238,102,119}\textbf{central\ brain\ (CB)}}$ · ${\color[RGB]{34,136,51}\textbf{sensory\ (SE)}}$ · ${\color[RGB]{204,187,68}\textbf{visual\ projection\ (VP)}}$ · ${\color[RGB]{170,51,119}\textbf{descending\ (DN)}}$
- **Type graph** - a directed graph whose nodes are cell types and whose edges represent conserved synaptic connectivity (an A → B edge exists iff at least one A → B cell-level edge is present in each of the three datasets). The full type graph has 5,116 nodes and ~45,000 edges.
- **Circuit type graph** - the subgraph of the type graph restricted to the 673 cell types present in the circuit (673 nodes, 1,133 edges). Unless stated otherwise, degree and topology metrics in this document refer to this restricted graph.
- **Neuron triplet** - a matched set of three neurons (one per dataset) of the same cell type, occupying one slot in the circuit.
- **ORN** - olfactory receptor neuron. **lLN** - local interneuron (antennal lobe). **PN** - projection neuron. **KC** - Kenyon cell. **MBON** - mushroom body output neuron. **VPN** - visual projection neuron.

## Results

The circuit contains **4,485 neuron triplets**, **673 cell types**, and **5,450** directed edges.

| Class | *n* | % | L/R |
| --- | ---: | ---: | ---: |
| ${\color[RGB]{68,119,170}\text{Optic\ lobe}}$ | 2958 | 66.0 | 1623/1335 |
| ${\color[RGB]{238,102,119}\text{Central\ brain}}$ | 916 | 20.4 | 461/455 |
| ${\color[RGB]{34,136,51}\text{Sensory}}$ | 313 | 7.0 | 111/200 |
| ${\color[RGB]{204,187,68}\text{Visual\ projection}}$ | 205 | 4.6 | 85/120 |
| ${\color[RGB]{170,51,119}\text{Descending}}$ | 86 | 1.9 | 38/48 |
| Other† | 7 | 0.2 | 5/2 |
| **Total** | **4485** | | **2323/2160** |

† Visual centrifugal (5), motor (1), ascending (1).

Two thirds of the circuit sits in ${\color[RGB]{68,119,170}\text{OL}}$. This is not surprising: ${\color[RGB]{68,119,170}\text{OL}}$ neurons are arranged in repeated columns with near-identical wiring, so the isomorphism constraint is easy to satisfy there. ${\color[RGB]{34,136,51}\text{SE}}$, ${\color[RGB]{204,187,68}\text{VP}}$, and ${\color[RGB]{170,51,119}\text{DN}}$ together make up only 13.5% of neurons, but they carry most of the inter-class signal flow (see flow matrix below). Hemispheric balance is near-symmetric (L 2323 / R 2160), and 86.8% of edges are ipsilateral.

## Graph topology

The circuit type graph has 673 nodes and 1,133 directed edges. Feedforward loops outnumber 3-cycles 407:153 (ratio 2.7:1), so the overall architecture leans heavily feedforward. Only 94 edge pairs (8.3%) are reciprocal, and most of those sit at the ${\color[RGB]{238,102,119}\text{CB}}$ - ${\color[RGB]{34,136,51}\text{SE}}$ interface (38 pairs, the ORN-lLN back-and-forth in the antennal lobe) or within ${\color[RGB]{238,102,119}\text{CB}}$ itself (33 pairs).

The inter-class flow matrix is almost strictly feedforward:

| From ↓ / To → | ${\color[RGB]{68,119,170}\text{OL}}$ | ${\color[RGB]{238,102,119}\text{CB}}$ | ${\color[RGB]{34,136,51}\text{SE}}$ | ${\color[RGB]{204,187,68}\text{VP}}$ | ${\color[RGB]{170,51,119}\text{DN}}$ |
| --- | ---: | ---: | ---: | ---: | ---: |
| ${\color[RGB]{68,119,170}\text{OL}}$ | - | 0 | 0 | 454 | 0 |
| ${\color[RGB]{238,102,119}\text{CB}}$ | 0 | - | 215 | 6 | 162 |
| ${\color[RGB]{34,136,51}\text{SE}}$ | 0 | 257 | - | 0 | 26 |
| ${\color[RGB]{204,187,68}\text{VP}}$ | 5 | 55 | 0 | - | 37 |
| ${\color[RGB]{170,51,119}\text{DN}}$ | 0 | 27 | 0 | 0 | - |

The two heaviest inter-class flows are ${\color[RGB]{68,119,170}\text{OL}}$ → ${\color[RGB]{204,187,68}\text{VP}}$ (454 edges) and ${\color[RGB]{34,136,51}\text{SE}}$ ↔ ${\color[RGB]{238,102,119}\text{CB}}$ (257 + 215, bidirectional). Both converge on ${\color[RGB]{170,51,119}\text{DN}}$, which receives from ${\color[RGB]{204,187,68}\text{VP}}$ (37) and ${\color[RGB]{238,102,119}\text{CB}}$ (162) but sends almost nothing back (27 edges to ${\color[RGB]{238,102,119}\text{CB}}$).

![Top 50 cell types by neuron count](figures/cells_per_type.png)

*Figure 1: Top 50 cell types by neuron count, coloured by class. The distribution is right-skewed (median 1, mean 6.7). Columnar OL neurons dominate, with KCs (KCab, KCg-m) as the only non-OL types in the top 30.*

## Type selection for visualization

To ease visualization and retain biological relevance, **48 representative types** are selected via three graph-derived criteria and displayed in the network figure below.

1. Types are ranked by total inter-class edge count; the top types per class are retained (gateway selection).
2. Within ${\color[RGB]{238,102,119}\text{CB}}$, all types lying on a directed shortest path between ${\color[RGB]{34,136,51}\text{SE}}$\-connected sources and ${\color[RGB]{170,51,119}\text{DN}}$\-connected sinks are added (relay selection).
3. The top ${\color[RGB]{68,119,170}\text{OL}}$ types by edge count toward already-selected ${\color[RGB]{68,119,170}\text{OL}}$ gateways are added (feeder selection).

## Figures

![Type-level network (FAFB instance)](figures/network_graph_types.png)

*Figure 2: Type-level network (FAFB instance): 48 displayed types among 673 in the circuit. Node area ∝ cell count; class hue with saturation ∝ type degree (incident edges). Arrows: inter-/intra-class edges (width ∝ edge count).*

![3D meshes of constituent neurons in Neuroglancer (FAFB)](figures/codex_mesh.png)

*Figure 3: 3D meshes of constituent neurons in Neuroglancer (FAFB).*

## Visual stream

${\color[RGB]{68,119,170}\text{OL}}$ contributes 2,958 neurons (66%) across 399 cell types. Medulla neurons (${\color[RGB]{68,119,170}\text{Mi1}}$, ${\color[RGB]{68,119,170}\text{Tm1}}$, ${\color[RGB]{68,119,170}\text{Tm2}}$, ${\color[RGB]{68,119,170}\text{Tm3}}$, ${\color[RGB]{68,119,170}\text{Tm9}}$) feed columnar motion-sensitive neurons (${\color[RGB]{68,119,170}\text{T2}}$, ${\color[RGB]{68,119,170}\text{T2a}}$, ${\color[RGB]{68,119,170}\text{T3}}$, ${\color[RGB]{68,119,170}\text{T4b}}$), matching the ON/OFF motion pathways described by Shinomiya et al. [2]. These medulla cell types have the highest out-degree in ${\color[RGB]{68,119,170}\text{OL}}$ (${\color[RGB]{68,119,170}\text{Mi1}}$: 17, ${\color[RGB]{68,119,170}\text{Tm1}}$: 16, ${\color[RGB]{68,119,170}\text{Tm2}}$: 16). The circuit also includes many abundant columnar cell types not shown in Figure 2: ${\color[RGB]{68,119,170}\text{T4a}}$ (146 neurons), ${\color[RGB]{68,119,170}\text{T5c}}$ (146), ${\color[RGB]{68,119,170}\text{T4c}}$ (145), ${\color[RGB]{68,119,170}\text{Tm9}}$ (141), ${\color[RGB]{68,119,170}\text{T5b}}$ (69).

These feed into multiple VPN cell types: ${\color[RGB]{68,119,170}\text{T2}}$ / ${\color[RGB]{68,119,170}\text{T2a}}$ / ${\color[RGB]{68,119,170}\text{T3}}$ target ${\color[RGB]{204,187,68}\text{LC11}}$ and ${\color[RGB]{204,187,68}\text{LC17}}$; ${\color[RGB]{68,119,170}\text{T4b}}$ feeds ${\color[RGB]{204,187,68}\text{LPC1}}$ and ${\color[RGB]{204,187,68}\text{LPLC2}}$; ${\color[RGB]{68,119,170}\text{Tm2}}$ feeds ${\color[RGB]{204,187,68}\text{LC4}}$. The ${\color[RGB]{68,119,170}\text{OL}}$ → ${\color[RGB]{204,187,68}\text{VP}}$ flow totals 454 edges, the strongest inter-class connection in the circuit.

${\color[RGB]{204,187,68}\text{LC11}}$ → ${\color[RGB]{238,102,119}\text{CB0744}}$ (11 edges) is the only ${\color[RGB]{204,187,68}\text{VP}}$ → ${\color[RGB]{238,102,119}\text{CB}}$ link among the displayed cell types. ${\color[RGB]{204,187,68}\text{LC11}}$ is a small-object detector that drives freezing behaviour [9], while ${\color[RGB]{238,102,119}\text{CB0744}}$ is a ventrolateral protocerebrum interneuron [1] with no outgoing edges in the circuit type graph (though in the full type graph it connects onward to anterior ventrolateral protocerebrum and posterior ventrolateral protocerebrum cell types).

${\color[RGB]{204,187,68}\text{LC4}}$ and ${\color[RGB]{204,187,68}\text{LPLC2}}$ reach ${\color[RGB]{170,51,119}\text{DN}}$ neurons directly. These two cell types are looming detectors: ${\color[RGB]{204,187,68}\text{LC4}}$ encodes approach velocity, ${\color[RGB]{204,187,68}\text{LPLC2}}$ encodes angular size, and together they drive escape take-off via the giant fiber pathway [3]. ${\color[RGB]{204,187,68}\text{LC22}}$ also projects to ${\color[RGB]{170,51,119}\text{DN}}$ cell types (${\color[RGB]{170,51,119}\text{DNp06}}$, ${\color[RGB]{170,51,119}\text{DNp26}}$, ${\color[RGB]{170,51,119}\text{DNp31}}$, ${\color[RGB]{170,51,119}\text{DNg81}}$, ${\color[RGB]{170,51,119}\text{DNpe001}}$, ${\color[RGB]{170,51,119}\text{DNpe016}}$).

## Olfactory stream

The olfactory stream runs through ${\color[RGB]{34,136,51}\text{SE}}$ (313 neurons, 7%) and ${\color[RGB]{238,102,119}\text{CB}}$ (916 neurons, 20.4%). The flow between them is bidirectional (${\color[RGB]{34,136,51}\text{SE}}$ → ${\color[RGB]{238,102,119}\text{CB}}$: 257 edges, ${\color[RGB]{238,102,119}\text{CB}}$ → ${\color[RGB]{34,136,51}\text{SE}}$: 215), which reflects the bidirectional synapses between ORNs and lLNs in the antennal lobe [4]. This is the only strongly bidirectional inter-class connection in the circuit (38 reciprocal type pairs).

ORN cell types (${\color[RGB]{34,136,51}\text{ORN-V}}$, ${\color[RGB]{34,136,51}\text{ORN-VA2}}$, ${\color[RGB]{34,136,51}\text{ORN-DM1}}$, ${\color[RGB]{34,136,51}\text{ORN-VM5d}}$) synapse onto PNs (e.g. ${\color[RGB]{238,102,119}\text{V-ilPN}}$) and lLNs. ${\color[RGB]{238,102,119}\text{lLN2F-b}}$ stands out immediately: it has the highest degree in the circuit type graph (50 in, 48 out). The lLN cell types (${\color[RGB]{238,102,119}\text{lLN1-bc}}$, ${\color[RGB]{238,102,119}\text{lLN2F-b}}$, ${\color[RGB]{238,102,119}\text{lLN2X04}}$) are densely interconnected and mediate lateral inhibition across glomeruli, a mechanism for gain control [4].

PNs (${\color[RGB]{238,102,119}\text{V-ilPN}}$, ${\color[RGB]{238,102,119}\text{VM1-lPN}}$, ${\color[RGB]{238,102,119}\text{M-l2PN3t18}}$) relay signals to KCs. Two KC cell types are present: ${\color[RGB]{238,102,119}\text{KCab}}$ (170 neurons) and ${\color[RGB]{238,102,119}\text{KCg-m}}$ (156 neurons). Interestingly, ${\color[RGB]{238,102,119}\text{KCab}}$ receives input from five PN cell types but has zero outgoing edges in the circuit type graph. This is consistent with KCs acting as a sparse-coding memory layer [6] rather than a relay: they integrate input but do not propagate it further in the same way. ${\color[RGB]{238,102,119}\text{KCg-m}}$ instead connects to ${\color[RGB]{238,102,119}\text{MBON12}}$, linking olfactory memory to downstream decision circuits [7].

## Integration

Both streams converge on ${\color[RGB]{170,51,119}\text{DN}}$ (86 neurons, 1.9%). It receives 37 edges from ${\color[RGB]{204,187,68}\text{VP}}$ and 162 from ${\color[RGB]{238,102,119}\text{CB}}$, but sends only 27 back to ${\color[RGB]{238,102,119}\text{CB}}$. ${\color[RGB]{170,51,119}\text{DNp06}}$ has the highest in-degree among ${\color[RGB]{170,51,119}\text{DN}}$ cell types (29 incoming edges) and the highest betweenness centrality (BC = 0.040). Each of the other ${\color[RGB]{170,51,119}\text{DN}}$ cell types (${\color[RGB]{170,51,119}\text{DNp26}}$, ${\color[RGB]{170,51,119}\text{DNp31}}$, ${\color[RGB]{170,51,119}\text{DNg81}}$, ${\color[RGB]{170,51,119}\text{DNpe001}}$, ${\color[RGB]{170,51,119}\text{DNpe016}}$) contributes a single neuron per dataset, as expected for individually identifiable descending neurons [8].

## Conclusion

The circuit recovered by the isomorphism search has a clear functional architecture. Two sensory streams, one visual and one olfactory, run in parallel through largely separate classes and converge on a small set of ${\color[RGB]{170,51,119}\text{DN}}$ cell types that act as a bottleneck toward motor output. The visual stream is dominated by feedforward columnar processing in ${\color[RGB]{68,119,170}\text{OL}}$, through VPNs that encode important features (looming, small-object motion) before reaching ${\color[RGB]{170,51,119}\text{DN}}$ directly. The olfactory stream instead passes through a recurrent stage of lateral inhibition in the antennal lobe (${\color[RGB]{34,136,51}\text{SE}}$ ↔ ${\color[RGB]{238,102,119}\text{CB}}$), then projects via PNs to a memory layer (KCs → MBONs) before reaching ${\color[RGB]{170,51,119}\text{DN}}$ through ${\color[RGB]{238,102,119}\text{CB}}$. The fact that these two pathways emerge intact from a purely structural constraint (edge-identical subgraph across three independently reconstructed brains) suggests that they represent a deeply conserved sensorimotor backbone of the *Drosophila* nervous system, robust across sex, developmental variation, and reconstruction methodology.

## References

1. Schlegel, P. et al. (2024). Whole-brain annotation and multi-connectome cell typing of *Drosophila*. *Nature*, 634, 139-152.
2. Shinomiya, K. et al. (2019). Comparisons between the ON- and OFF-edge motion pathways in the *Drosophila* brain. *eLife*, 8, e40025.
3. Ache, J. M. et al. (2019). Neural basis for looming size and velocity encoding in the *Drosophila* giant fiber escape pathway. *Current Biology*, 29(6), 1073-1081.
4. Olsen, S. R. & Wilson, R. I. (2008). Lateral presynaptic inhibition mediates gain control in an olfactory circuit. *Nature*, 452, 956-960.
5. Keleş, M. F. & Frye, M. A. (2017). Object-detecting neurons in *Drosophila*. *Current Biology*, 27(5), 680-687.
6. Honegger, K. S. et al. (2011). Cellular-resolution population imaging reveals robust sparse coding in the *Drosophila* mushroom body. *J. Neurosci.*, 31(33), 11772-11785.
7. Aso, Y. et al. (2014). Mushroom body output neurons encode valence and guide memory-based action selection. *eLife*, 3, e04580.
8. Namiki, S. et al. (2018). The functional organization of descending sensory-motor pathways in *Drosophila*. *eLife*, 7, e34272.
9. Tanaka, R. & Clark, D. A. (2020). Object-displacement-sensitive visual neurons drive freezing in *Drosophila*. *Current Biology*, 30(13), 2532-2550.
