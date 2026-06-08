# Largest Shared Neural Circuit - Biological Interpretation

FlyWire Qualification Challenge, June 2026 - Francesco Correnti

## Definitions

- **Circuit** - the largest connected directed induced subgraph found to be isomorphic across the three datasets (FAFB, BANC, Male CNS). It contains N = 4,485 neuron triplets.
- **Cell type** - a neuronal identity label (e.g. Mi1, KCab) shared across datasets; neurons of the same cell type are treated as interchangeable for matching purposes.
- **Class** - a coarse brain-region category to which each cell type belongs. Five classes appear in the circuit:
<span style="color:#4477AA">**optic lobe (OL)**</span> ·
<span style="color:#EE6677">**central brain (CB)**</span> ·
<span style="color:#228833">**sensory (SE)**</span> ·
<span style="color:#CCBB44">**visual projection (VP)**</span> ·
<span style="color:#AA3377">**descending (DN)**</span>
- **Type graph** - a directed graph whose nodes are cell types and whose edges represent conserved synaptic connectivity (an A → B edge exists iff at least one A → B cell-level edge is present in each of the three datasets). The full type graph has 5,116 nodes and ~45,000 edges.
- **Circuit type graph** - the subgraph of the type graph restricted to the 673 cell types present in the circuit (673 nodes, 1,133 edges). Unless stated otherwise, degree and topology metrics in this document refer to this restricted graph.
- **Neuron triplet** - a matched set of three neurons (one per dataset) of the same cell type, occupying one slot in the circuit.
- **ORN** - olfactory receptor neuron. **lLN** - local interneuron (antennal lobe). **PN** - projection neuron. **KC** - Kenyon cell. **MBON** - mushroom body output neuron. **VPN** - visual projection neuron.

## Results

The circuit contains **4,485 neuron triplets**, **673 cell types**, and **5,450** directed edges.

| Class | *n* | % | L/R |
| --- | ---: | ---: | ---: |
| <span style="color:#4477AA">Optic lobe</span> | 2958 | 66.0 | 1623/1335 |
| <span style="color:#EE6677">Central brain</span> | 916 | 20.4 | 461/455 |
| <span style="color:#228833">Sensory</span> | 313 | 7.0 | 111/200 |
| <span style="color:#CCBB44">Visual projection</span> | 205 | 4.6 | 85/120 |
| <span style="color:#AA3377">Descending</span> | 86 | 1.9 | 38/48 |
| Other† | 7 | 0.2 | 5/2 |
| **Total** | **4485** | | **2323/2160** |

† Visual centrifugal (5), motor (1), ascending (1).

Two thirds of the circuit sits in <span style="color:#4477AA">OL</span>. This is not surprising: <span style="color:#4477AA">OL</span> neurons are arranged in repeated columns with near-identical wiring, so the isomorphism constraint is easy to satisfy there. <span style="color:#228833">SE</span>, <span style="color:#CCBB44">VP</span>, and <span style="color:#AA3377">DN</span> together make up only 13.5% of neurons, but they carry most of the inter-class signal flow (see flow matrix below). Hemispheric balance is near-symmetric (L 2323 / R 2160), and 86.8% of edges are ipsilateral.

## Graph topology

The circuit type graph has 673 nodes and 1,133 directed edges. Feedforward loops outnumber 3-cycles 407:153 (ratio 2.7:1), so the overall architecture leans heavily feedforward. Only 94 edge pairs (8.3%) are reciprocal, and most of those sit at the <span style="color:#EE6677">CB</span>-<span style="color:#228833">SE</span> interface (38 pairs, the ORN-lLN back-and-forth in the antennal lobe) or within <span style="color:#EE6677">CB</span> itself (33 pairs).

The inter-class flow matrix is almost strictly feedforward:

| From ↓ / To → | <span style="color:#4477AA">OL</span> | <span style="color:#EE6677">CB</span> | <span style="color:#228833">SE</span> | <span style="color:#CCBB44">VP</span> | <span style="color:#AA3377">DN</span> |
| --- | ---: | ---: | ---: | ---: | ---: |
| <span style="color:#4477AA">OL</span> | - | 0 | 0 | 454 | 0 |
| <span style="color:#EE6677">CB</span> | 0 | - | 215 | 6 | 162 |
| <span style="color:#228833">SE</span> | 0 | 257 | - | 0 | 26 |
| <span style="color:#CCBB44">VP</span> | 5 | 55 | 0 | - | 37 |
| <span style="color:#AA3377">DN</span> | 0 | 27 | 0 | 0 | - |

The two heaviest inter-class flows are <span style="color:#4477AA">OL</span> → <span style="color:#CCBB44">VP</span> (454 edges) and <span style="color:#228833">SE</span> ↔ <span style="color:#EE6677">CB</span> (257 + 215, bidirectional). Both converge on <span style="color:#AA3377">DN</span>, which receives from <span style="color:#CCBB44">VP</span> (37) and <span style="color:#EE6677">CB</span> (162) but sends almost nothing back (27 edges to <span style="color:#EE6677">CB</span>).

![Top 50 cell types by neuron count](figures/cells_per_type.png)

*Figure 1: Top 50 cell types by neuron count, coloured by class. The distribution is right-skewed (median 1, mean 6.7). Columnar <span style="color:#4477AA">OL</span> neurons dominate, with KCs (<span style="color:#EE6677">KCab</span>, <span style="color:#EE6677">KCg-m</span>) as the only non-<span style="color:#4477AA">OL</span> types in the top 50.*

## Type selection for visualization

To ease visualization and retain biological relevance, **48 representative types** are selected via three graph-derived criteria and displayed in the network figure below.

1. Types are ranked by total inter-class edge count; the top types per class are retained (gateway selection).
2. Within <span style="color:#EE6677">CB</span>, all types lying on a directed shortest path between <span style="color:#228833">SE</span>-connected sources and <span style="color:#AA3377">DN</span>-connected sinks are added (relay selection).
3. The top <span style="color:#4477AA">OL</span> types by edge count toward already-selected <span style="color:#4477AA">OL</span> gateways are added (feeder selection).

## Figures

![Type-level network (FAFB instance)](figures/network_graph_types.png)

*Figure 2: Type-level network (FAFB instance): 48 displayed types among 673 in the circuit. Node area ∝ cell count; class hue with saturation ∝ type degree (incident edges). Arrows: inter-/intra-class edges (width ∝ edge count).*

![3D meshes of constituent neurons in Neuroglancer (FAFB)](figures/codex_mesh.png)

*Figure 3: 3D meshes of constituent neurons in Neuroglancer (FAFB).*

## Visual stream

<span style="color:#4477AA">OL</span> contributes 2,958 neurons (66%) across 399 cell types. Medulla neurons (<span style="color:#4477AA">Mi1</span>, <span style="color:#4477AA">Tm1</span>, <span style="color:#4477AA">Tm2</span>, <span style="color:#4477AA">Tm3</span>, <span style="color:#4477AA">Tm9</span>) feed columnar motion-sensitive neurons (<span style="color:#4477AA">T2</span>, <span style="color:#4477AA">T2a</span>, <span style="color:#4477AA">T3</span>, <span style="color:#4477AA">T4b</span>), matching the ON/OFF motion pathways described by Shinomiya et al. [2]. These medulla cell types have the highest out-degree in <span style="color:#4477AA">OL</span> (<span style="color:#4477AA">Mi1</span>: 17, <span style="color:#4477AA">Tm1</span>: 16, <span style="color:#4477AA">Tm2</span>: 16). The circuit also includes many abundant columnar cell types not shown in Figure 2: <span style="color:#4477AA">T4a</span> (146 neurons), <span style="color:#4477AA">T5c</span> (146), <span style="color:#4477AA">T4c</span> (145), <span style="color:#4477AA">Tm9</span> (141), <span style="color:#4477AA">T5b</span> (69).

These feed into multiple VPN cell types: <span style="color:#4477AA">T2</span>/<span style="color:#4477AA">T2a</span>/<span style="color:#4477AA">T3</span> target <span style="color:#CCBB44">LC11</span> and <span style="color:#CCBB44">LC17</span>; <span style="color:#4477AA">T4b</span> feeds <span style="color:#CCBB44">LPC1</span> and <span style="color:#CCBB44">LPLC2</span>; <span style="color:#4477AA">Tm2</span> feeds <span style="color:#CCBB44">LC4</span>. The <span style="color:#4477AA">OL</span> → <span style="color:#CCBB44">VP</span> flow totals 454 edges, the strongest inter-class connection in the circuit.

<span style="color:#CCBB44">LC11</span> → <span style="color:#EE6677">CB0744</span> (11 edges) is the only <span style="color:#CCBB44">VP</span> → <span style="color:#EE6677">CB</span> link among the displayed cell types. <span style="color:#CCBB44">LC11</span> is a small-object detector that drives freezing behaviour [9], while <span style="color:#EE6677">CB0744</span> is a ventrolateral protocerebrum interneuron [1] with no outgoing edges in the circuit type graph (though in the full type graph it connects onward to anterior ventrolateral protocerebrum and posterior ventrolateral protocerebrum cell types).

<span style="color:#CCBB44">LC4</span> and <span style="color:#CCBB44">LPLC2</span> reach <span style="color:#AA3377">DN</span> neurons directly. These two cell types are looming detectors: <span style="color:#CCBB44">LC4</span> encodes approach velocity, <span style="color:#CCBB44">LPLC2</span> encodes angular size, and together they drive escape take-off via the giant fiber pathway [3]. <span style="color:#CCBB44">LC22</span> also projects to <span style="color:#AA3377">DN</span> cell types (<span style="color:#AA3377">DNp06</span>, <span style="color:#AA3377">DNp26</span>, <span style="color:#AA3377">DNp31</span>, <span style="color:#AA3377">DNg81</span>, <span style="color:#AA3377">DNpe001</span>, <span style="color:#AA3377">DNpe016</span>).

## Olfactory stream

The olfactory stream runs through <span style="color:#228833">SE</span> (313 neurons, 7%) and <span style="color:#EE6677">CB</span> (916 neurons, 20.4%). The flow between them is bidirectional (<span style="color:#228833">SE</span> → <span style="color:#EE6677">CB</span>: 257 edges, <span style="color:#EE6677">CB</span> → <span style="color:#228833">SE</span>: 215), which reflects the bidirectional synapses between ORNs and lLNs in the antennal lobe [4]. This is the only strongly bidirectional inter-class connection in the circuit (38 reciprocal type pairs).

ORN cell types (<span style="color:#228833">ORN_V</span>, <span style="color:#228833">ORN_VA2</span>, <span style="color:#228833">ORN_DM1</span>, <span style="color:#228833">ORN_VM5d</span>) synapse onto PNs (e.g. <span style="color:#EE6677">V_ilPN</span>) and lLNs. <span style="color:#EE6677">lLN2F_b</span> stands out immediately: it has the highest degree in the circuit type graph (50 in, 48 out). The lLN cell types (<span style="color:#EE6677">lLN1_bc</span>, <span style="color:#EE6677">lLN2F_b</span>, <span style="color:#EE6677">lLN2X04</span>) are densely interconnected and mediate lateral inhibition across glomeruli, a mechanism for gain control [4].

PNs (<span style="color:#EE6677">V_ilPN</span>, <span style="color:#EE6677">VM1_lPN</span>, <span style="color:#EE6677">M_l2PN3t18</span>) relay signals to KCs. Two KC cell types are present: <span style="color:#EE6677">KCab</span> (170 neurons) and <span style="color:#EE6677">KCg-m</span> (156 neurons). Interestingly, <span style="color:#EE6677">KCab</span> receives input from five PN cell types but has zero outgoing edges in the circuit type graph. This is consistent with KCs acting as a sparse-coding memory layer [6] rather than a relay: they integrate input but do not propagate it further in the same way. <span style="color:#EE6677">KCg-m</span> instead connects to <span style="color:#EE6677">MBON12</span>, linking olfactory memory to downstream decision circuits [7].

## Integration

Both streams converge on <span style="color:#AA3377">DN</span> (86 neurons, 1.9%). It receives 37 edges from <span style="color:#CCBB44">VP</span> and 162 from <span style="color:#EE6677">CB</span>, but sends only 27 back to <span style="color:#EE6677">CB</span>. <span style="color:#AA3377">DNp06</span> has the highest in-degree among <span style="color:#AA3377">DN</span> cell types (29 incoming edges) and the highest betweenness centrality (BC = 0.040). Each of the other <span style="color:#AA3377">DN</span> cell types (<span style="color:#AA3377">DNp26</span>, <span style="color:#AA3377">DNp31</span>, <span style="color:#AA3377">DNg81</span>, <span style="color:#AA3377">DNpe001</span>, <span style="color:#AA3377">DNpe016</span>) contributes a single neuron per dataset, as expected for individually identifiable descending neurons [8].

## Conclusion

The circuit recovered by the isomorphism search has a clear functional architecture. Two sensory streams, one visual and one olfactory, run in parallel through largely separate classes and converge on a small set of <span style="color:#AA3377">DN</span> cell types that act as a bottleneck toward motor output. The visual stream is dominated by feedforward columnar processing in <span style="color:#4477AA">OL</span>, through VPNs that encode important features (looming, small-object motion) before reaching <span style="color:#AA3377">DN</span> directly. The olfactory stream instead passes through a recurrent stage of lateral inhibition in the antennal lobe (<span style="color:#228833">SE</span> ↔ <span style="color:#EE6677">CB</span>), then projects via PNs to a memory layer (KCs → MBONs) before reaching <span style="color:#AA3377">DN</span> through <span style="color:#EE6677">CB</span>. The fact that these two pathways emerge intact from a purely structural constraint (edge-identical subgraph across three independently reconstructed brains) suggests that they represent a deeply conserved sensorimotor backbone of the *Drosophila* nervous system, robust across sex, developmental variation, and reconstruction methodology.

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
