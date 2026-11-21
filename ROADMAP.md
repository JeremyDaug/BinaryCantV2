# Roadmap

Ordered by priority. Items marked (Q-n) wait on an open question in DECISIONS.md.

## Done in v2.2
* Lexicon grown 43 → 337 roots with locality preserved (related 2.20 vs unrelated 9.94 bits).
* Rule-based English ↔ Cant translator (`cant translate`, TRANSLATION.md).
* Local web UI and JSON API (`cant serve`).
* Q-1 (fiction as scope) and Q-5 (yaw-pitch-roll) accepted as defaults.

## Next
1. **Author review**: the 294 `proposed-v2.2` roots and conventions C-1 … C-18 (SPEC §14), then
   settle the remaining questions Q-2 … Q-4 and Q-6 … Q-8.
2. **Translator coverage**: relative clauses, passives, `or`/`but` (→ `OR`/`XOR` ops),
   modals (can/must → a modality root as modifier), reported speech from English ("X says that…"
   → nested sentence), fiction scopes, and word-sense disambiguation by context.
3. **Semantic evaluator**: an interpreter that applies statements to a knowledge store, so that
   Assertion/Deletion/Correction/Query/IF actually update and answer (the doc's "a statement must
   result in Data being updated"). Includes scope push/pop for nested sentences. The UI gets a
   "conversation" tab once this exists.
4. **Binding resolver**: make the implicit rules (modifier chains, genitives, relation
   Subjects×Objects, fusion stacks) explicit in the decoder's output as a graph. cant2en
   already does this internally, so it should be lifted into the codec.
5. **Lexicon versioning**: a file should name the dictionary it was written against (Q-6).

## Later
6. **Feature bits for cross-cutting locality** (Q-3), measured against the tree-only baseline;
   now worth revisiting as the lexicon approaches ~500 roots.
7. **File metadata** (`cant id`, author, dictionary URI) as a `0x43 meta` control word (Q-6).
8. **Other natural languages**: a second `xx_lexicon.csv` mapping to show the interlingua claim.
9. **Streaming codec**: decode by span without materialising the tree; a C or Rust
   implementation for embedded use; fuzzing the decoder against malformed streams.
10. **Transport integrity**: optional checksum or signature trailer using `sig()`.
11. **More externals**: matrices/vectors, units of measure, expanded colour spaces, and
   media containers by reference (`uri`) vs inline (`bytes`).

## Low priority
12. **Human-pronounceable form**: a lossless mapping from words to sound or syllables, for
    organics. The priorities say machines come first, so this stays last, and it must never
    constrain the binary layout.
