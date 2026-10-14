# Figure 2 legend

**Figure 2. Validation framework and outcomes for NEXCISION v0.1.0.**
Seven complementary evidence layers assessed exact coordinate-based excision
for the supported SPANDx-style transposed NEXUS matrix model. Three genuine
SPANDx-derived matrices underwent six recorded compatibility checks. An
independent naïve oracle supplied expected interval membership for 17 fixed
correctness/preservation cases and a separate all-sites safety case. Another
26 malformed-input challenges verified controlled failure and no unintended
outputs. A deterministic corpus of 1,000 synthetic matrices contained 304,000
site rows. Property-based testing covered nine invariants across 1,800
generated examples. Mutation testing detected all 12 deliberately introduced
faults. Results shown belong to the original frozen v0.1.0 validation; the
new publication release must be revalidated independently.

The six real-matrix checks are documented in the archival result table; the
three original matrices are not distributed in the benchmarking repository.
