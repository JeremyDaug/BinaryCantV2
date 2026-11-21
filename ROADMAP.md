# Roadmap

Ordered by priority. Items marked (Q-n) wait on an open question in DECISIONS.md.

## Next
1. **Author review of V2.1**: settle Q-1 … Q-8, then freeze the bit layout as V2.1.0.
2. **Grow the lexicon** from ~43 to a few hundred roots: function words (quantifiers, negation,
   comparison, causation, possession variants), body and being domains, and the doc's own
   example vocabulary (cat, red, Quetzalcoatl …). Keep `tools/locality_report.py` green, and
   add a lint for "sense defined but marked proposed for > N releases".
3. **Semantic evaluator**: an interpreter that applies statements to a knowledge store, so that
   Assertion/Deletion/Correction/Query/IF actually update and answer (the doc's "a statement must
   result in Data being updated"). Includes scope push/pop for nested sentences.
4. **Binding resolver**: make the implicit rules (modifier chains, relation Subjects×Objects,
   fusion stacks) explicit in the decoder's output as a graph, so links and adjacency can be
   checked against each other.

## Later
5. **Feature bits for cross-cutting locality** (Q-3), measured against the tree-only baseline.
6. **File metadata** (`cant id`, author, dictionary URI) as a `0x43 meta` control word (Q-6),
   and **lexicon versioning** so a file names the dictionary it was written against.
7. **Streaming codec**: decode by span without materialising the tree; a C or Rust
   implementation for embedded use; fuzzing the decoder against malformed streams.
8. **Transport integrity**: optional checksum or signature trailer using `sig()`.
9. **More externals**: matrices/vectors, units of measure, expanded colour spaces, and
   media containers by reference (`uri`) vs inline (`bytes`).

## Low priority
10. **Human-pronounceable form**: a lossless mapping from words to sound or syllables, for
    organics. The priorities say machines come first, so this stays last, and it must never
    constrain the binary layout.
