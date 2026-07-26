# Methodology

## Analytical objective

The system identifies candidate name matches and evaluates whether loaded
ownership relationships create a path from a directly designated entity to a
target. It preserves identity matching, legal classification, and contextual
indicators as separate layers.

## Layer 1: Source ingestion

The OFAC loader reconstructs the relational SDN flat-file release:

- `SDN.CSV`: primary record
- `ALT.CSV`: alternate names
- `ADD.CSV`: addresses
- `SDN_COMMENTS.CSV`: remarks exceeding the primary-field limit

The OFAC entity number becomes the stable source identifier. File hashes should
be retained in production to support reproducibility.

The targeted GLEIF client searches the Global LEI Index by legal name or
retrieves an exact LEI. It maps Level 1 identity fields into the common entity,
alias, address, and identifier structures. It also requests published direct
and ultimate accounting-consolidating parent relationships for the selected
LEI and retrieves the corresponding parent identity records.

## Layer 2: Normalization

Names are converted to Unicode NFKD form, combining marks are removed when
possible, characters are uppercased, punctuation becomes spaces, and repeated
whitespace is collapsed. A separate comparison form removes common company
suffixes.

The current transliteration is intentionally conservative. A production system
should add language-aware transliteration and nickname rules while preserving
the original source spelling.

## Layer 3: Candidate matching

The MVP score combines the strongest of:

- Sequence similarity on the full normalized name
- Sequence similarity after legal-suffix removal
- Sequence similarity on sorted tokens

with token-set overlap. Exact identifiers receive an exact match. Country
agreement can provide limited supporting context.

The score ranks candidates. It is not a probability that two records represent
the same real-world subject.

GLEIF name searches apply a separate disambiguation layer to the retrieved
legal-entity candidates. It accounts for legal-suffix and spacing variants,
then uses active entity and issued registration status as deterministic
tie-breakers. The interface warns when the leading scores are close. This
ranking does not replace identifier, jurisdiction, registration, and address
validation.

## Layer 4: Ownership propagation

Let \(B_0\) be the set of directly designated entities. At iteration \(t\), the
system evaluates each unclassified entity \(j\):

\[
O_{j,t} = \sum_{i \in B_{t-1}} w_{ij}
\]

where \(w_{ij}\) is the loaded direct ownership percentage from entity \(i\) to
entity \(j\). If \(O_{j,t} \geq 50\), entity \(j\) is added to \(B_t\).
Iterations continue until no additional entity crosses the threshold.

This approach models stage-wise propagation through majority-owned entities. It
does not substitute for a current legal assessment.

Only relationships with type `OWNS` and a numeric `ownership_pct` participate
in the calculation. GLEIF direct and ultimate parent links describe accounting
consolidation. They are stored as
`DIRECT_ACCOUNTING_CONSOLIDATING_PARENT_OF` and
`ULTIMATE_ACCOUNTING_CONSOLIDATING_PARENT_OF`, retain a null percentage, and
cannot change sanctions classification.

## Layer 5: Contextual indicators

The demonstration adds shared-address and control-related indicators.
Contextual relationships do not automatically change designation status.

## Required production validation

- Labeled match and non-match pairs
- Multilingual and transliterated names
- Common-name false-positive testing
- Identifier conflicts
- Missing ownership percentages
- Multiple blocked owners
- Ownership effective dates
- Divestment scenarios
- Circular ownership
- Source freshness and retractions
- GLEIF candidate-ranking validation and reporting exceptions
- Analyst inter-rater consistency

## Archived-case comparison

The comparison layer reads two completed result and graph artifacts. It
calculates numeric deltas as comparison minus baseline and uses stable entity
IDs and graph-edge signatures to identify added or removed evidence. Source and
indicator differences are compared by stored names and titles.

This layer does not infer why an artifact changed. Differences can reflect a
different target, source refresh, coverage change, model version, enrichment
choice, or genuine source-data change. Analysts must review those causes
separately.

## Governance

Every source-derived or analyst-derived relationship should retain:

- Source name and URL
- Retrieval timestamp
- Effective dates
- Source record identifier
- Confidence
- Match method
- Analyst status
- Version history
