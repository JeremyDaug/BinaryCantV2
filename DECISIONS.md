# Binary Cant V2.1: Decisions log

This log records each conflict or gap found in the source material and how V2.1 resolves it.
The sources are the *Binary Cant* doc (V1 sections plus the V2.0 draft), the *Binary Cant
Spreadsheet*, and the 2018 Python prototype `JeremyDaug/BinaryCant`. Open questions for the
author are at the end, each with a recommendation. IDs (D-nn) are referenced from SPEC.md.

## A. Word layout and classes

**D-01 · Word class bits.**
* The sources disagree:
  * Doc V1: bit 15 = inside/outside the language, then bit 14 = sentence metadata.
  * Doc V2.0: headers have bit 63 = 1 (`0x80…`).
  * 2018 code: bit 63 = "pointer in/out", bit 62 = meta/word.
* **V2.1** sets the top two bits as the class: `00` lexical, `01` external, `1x` header. This
  keeps the V2.0 header bytes exact and keeps the doc's "inside/outside" flag for non-header
  words. It also gives lexical words exactly the V1 16-bit layout in their top 16 bits.

**D-02 · 2018 bit-position bug.**
* In `word_const.py`, GRAMMAR (3 bits at shift 60) overlaps SENTENCE_META (bit 62).
* Header fields there sit one bit lower than in the doc (types at 58, affection at 54,
  evidentiality at 51) because of the extra pointer bit.
* **V2.1** follows the doc's V2.0 hex values. The 2018 positions are not carried forward.

**D-03 · Plurality position.**
* V1 Words Methodology puts plurality at the top of the *semantic* half; the 2018 code puts it
  at bits 48–47.
* **V2.1** places it at bits 47–46, directly after the V1 16-bit grammar block, so the whole
  grammar half is contiguous and the semantic half is pure meaning.

**D-04 · Plurality value order.**
* The V1 "Binary logic" list gives `10` = Plural (specific) and `11` = Plural (nonspecific).
* The V2 list and the 2018 code (`uva, sin, plu, num`) give the reverse.
* **V2.1**: `00` Unnumbered, `01` Singular, `10` Plural (nonspecific), `11` Numbered (specific).
  This matches the later doc list and the code.

**D-05 · Grammar roles 6/7.**
* V1 had two `[Empty]` roles, which the 2018 code calls und1/und2. The V2 text defines Fusion
  as the 7th role.
* **V2.1**: 6 = Fusion, 7 = reserved (error).

**D-06 · Spare grammar-half bits → explicit links.**
* The doc's fields use 16 bits, and plurality brings that to 18. The doc relies on adjacency
  alone for Modifier, Relation and Fusion binding.
* **V2.1** spends 11 bits on an explicit back-link (flag plus 10-bit offset, §4.2) and keeps
  3 reserved bits.
* This is the "relational meaning between words" half of the user's core idea. Without it,
  some sentences ("his shirt is red") cannot bind unambiguously without nesting.

**D-07 · Reserved values are errors.**
* The doc leaves `[Empty]` slots in roles, affection (4), evidentiality (1), and the statement
  subtypes.
* **V2.1**: every reserved value is rejected by encoders and decoders (Consistency). This
  leaves room for future meaning without letting today's data become ambiguous.

## B. Sentence headers

**D-08 · V1 vs V2.0 header values.**
* V1 (16-bit, prefix `01`):
  * Query subtypes: Subject, Object, **Clarify**, Time, Location, Reasoning, Explain, Specify.
  * Statement subtypes: **Fact, Fiction, Uncertain, Condition, Result, Imperative,
    Exclamatory, [Empty]**.
* V2.0 (64-bit, `0x80..0xF8`) changes these to *Verb (What)* and *Assertion, Deletion,
  Condition, Result, Imperative, Exclamatory, Uncertain, [empty](correction?)*.
* **V2.1** adopts the V2.0 values exactly. Mapping: V1 Clarify → Verb, Fact → Assertion.
  Fiction has no V2 slot (see Q-1).

**D-09 · `0xF8` statement subtype.**
* The doc writes "[empty] (correction)?" and "Undefined (correction?".
* **V2.1** defines it as **Correction (proposed)**: a statement that replaces an earlier one,
  pointed at with `ptr()`. Deletion removes; Correction replaces.

**D-10 · Affection numbering.**
* In the V1 table, Sad = `0011` jumps to Fear = `0110`: two codes are skipped and the listed
  values overflow the 4-bit field.
* V2.0's hex list (`0x800`…`0x878`, step 8) is sequential: 12 values plus 4 empty.
* **V2.1** uses the V2.0 sequence. Values 12–15 are reserved. (One V2 list numbers the
  empties 13–16. That is the 1-based list numbering, not a conflict.)

**D-11 · "Nothing is happening" affection.**
* The doc's example gloss and hex (`0x6040…`) use **Dishonest** for a plain neutral statement.
  It reads like a slip.
* **V2.1**'s re-encoding uses Honest. The *word* half `0x1C00…0002` carries over bit-for-bit.

**D-12 · Word count semantics.**
* Doc scratch (V1): "an external inclusion (such as a file) is not included in this length."
* Doc V2.0: "External inclusions, sentences, and operations do not count in this length.
  External inclusions and sentences count as 1 word".
* **V2.1** follows the later and more specific rule: externals and nested sentences count as 1,
  and operations count as 0.

**D-13 · Framing ambiguity → span field.**
* Because operations are not counted, a word count alone cannot tell whether an operation right
  after a nested sentence's last word belongs to the inner or the outer sentence.
* **V2.1** adds a 32-bit **span** (total body words) to each header. The doc's word count stays
  (20 bits).
* The header has no spare bits now: 5 + 4 + 3 + 20 + 32 = 64. A parser can skip any sentence
  in O(1), which matches "conversation is a file".

**D-14 · Sentence source / XML attributes.**
* The XML sketch gives `<sentence src=…>` and `<cant id author dict>`.
* **V2.1** represents the speaker with conversation-level `speaker(id)` markers and leaves
  `src`, `author`, `cant id` and `dict` out of the binary for now (Q-6).

## C. Lexicon and categories

**D-15 · Category scheme: Methodology vs Spreadsheet.**
* Words Methodology: `00` abstract, `01` object/location (split by a 3rd bit), `10` action,
  `11` relation.
* Spreadsheet: `00` object/abstract/state, `01` relation, `10` action, `11` location.
* **V2.1** adopts the **spreadsheet**, because it is the more developed one and has one
  category per sense column.
* Consequences:
  * Methodology's *Unrelated* `…0011` becomes `…0001`.
  * *Nowhere* `…0101` becomes root 0 category `11`.
  * *Nothing (action)* `…0010` is unchanged.
  * *Null* = root 0 object.
  * *Everything* = all-ones root, object `…1100`, exactly as in the Methodology.

**D-16 · Null vs Nothing.**
* The doc lists both *Null* (abstract `0000`) and *Nothing* (object `0001`), and the
  spreadsheet has a "nothing" row. Merging the object and abstract categories makes the two
  collide.
* **V2.1**: root 0 = `null` (Null / Unrelated / Nothing-happening / Nowhere, as in the doc).
  Root 1 = `nothing`, the empty object, which is a 1-bit sibling of null.

**D-17 · Spreadsheet word-bit codes.**
* The spreadsheet's 12-bit codes (manipulator `0`, mover `1`, auditory communicator `2`)
  cannot survive, because 0 is Null.
* **V2.1** assigns hierarchical roots (§9). The spreadsheet's order is kept as Gray-coded
  sibling order inside each cluster.

**D-18 · Spreadsheet "plurality" column.**
* The column is empty. Plurality is a grammar field in every version, so it is not a lexicon
  property. Not carried.

**D-19 · Sense gaps.**
* Most spreadsheet rows define only the object sense.
* **V2.1** fills an obvious sense only where it is unambiguous (e.g. *controller* →
  controlling) and marks it in `proposed_senses`. Every other sense is left undefined, and
  encoders refuse undefined senses (Clarity). Roots added for function words and examples are
  marked `source=proposed`.

**D-20 · Location used as a verb.**
* *Grammar flags* says that with locations, Verb means "to go to".
* *Word groupings* says `I<S> Home<V>` means "I am home".
* **V2.1**: base meaning *to be at*. Progression carries motion: Unstarted/InProgress =
  going to, Complete = arrived. This satisfies both texts without a second meaning.

**D-21 · "listener" naming clash.**
* The spreadsheet's relation sense of *auditory listener* is "listener". Deixis also needs
  "you".
* **V2.1** names the deictic root `addressee`, which avoids two roots that would both gloss as
  "listener".

**D-22 · Ambiguous spreadsheet entries.**
* *uncontrolled* has no gloss. V2.1 reads it as "thing without a controller" (beings
  domain). Flagged in the lexicon notes.
* *instrument* could be musical or a tool. It is placed with *tool* (SPEC §9, "one parent per concept").

## D. Externals and operations

**D-23 · External code space.**
* V1 used `0x8_`/`0x9_`/`0xA_`/`0xB_` top nibbles in a 32-bit world.
* **V2.1** moves externals to `0x40–0x7F` and keeps the V1 grouping as 8 groups of 8 subtypes:
  control, numbers, colour, direction, chemistry, time, reference, raw data plus operations.

**D-24 · Number widths.**
* V1 had int 23-bit, a custom 1/6/17 float, complex 12/12 and rational 1/11/12, all in a
  24-bit payload.
* **V2.1** widens to the 56-bit payload: int s56, IEEE binary32 float (standard beats custom
  for machines), complex s28/s28, rational 1/27/28. It adds float64 and bigint with
  continuation words.

**D-25 · Colour.**
* V1 had RGB, HSL, YUV and YCbCr at 8 bits each. The V2 list adds RGBA. V1 mentions
  "expanded" colour but gives no layout.
* **V2.1** adds `rgba` and defines "expanded" as `rgba14` (4 × 14 bits).

**D-26 · Direction.**
* V1's hex labels overlap: objective, from and speaker are all written `0x90`. It also says
  "z-y-z, or more normally yaw, pitch, roll", but z-y-z proper Euler angles and yaw-pitch-roll
  are different conventions. Steps were τ/256.
* **V2.1** moves the flags into the payload (relative, to/from, 2-bit frame), widens angles to
  16-bit (τ/65536), and uses yaw-pitch-roll (Q-5).

**D-27 · Atoms and compounds.**
* V1 used 9-bit P/N/E fields. The compound length is encoded as "words + 1", and the bond
  word has bonds 1/2 but no explicit tree shape.
* **V2.1**: 16-bit P/N/E fields. The compound head stores the node count directly (0 is
  invalid). Each node word states its child count, so the pre-order tree is self-delimiting.
* The secondary bond's exact meaning is a guess ("to previous sibling", marked proposed).

**D-28 · Time.**
* The doc stops at "Raw time is the number of seconds since" and lists Raw/Formatted.
* **V2.1** completes it:
  * `time`: Unix-epoch seconds, s56.
  * `datetime`: formatted fields with a UTC offset.
  * `duration`: seconds.
  * `time_ns`: +1 word.

**D-29 · Grammar on externals.**
* The XML sketch gives typed words their own grammar (`<word type='int' grammar='object'>`).
* The V1 text says operations "apply grammar … to data from outside the language".
* **V2.1** uses **cast operations** (`TO_SUBJECT`…`TO_FUSION`) whose 32-bit operand is a full
  grammar template. Externals keep all 56 payload bits, and the cast costs one uncounted word
  (Q-2).

**D-30 · "Xand".**
* "Xand" is not a standard gate. Read with Nand/Nor/Xor, it can only mean exclusive-NOR
  (equivalence).
* **V2.1** names it `XNOR`, and the gloss accepts `XAND` as an alias.

**D-31 · Conditional evaluation.**
* The doc says If-Then-Else, "not evaluated unless the conditional operator is called after
  them".
* **V2.1** defines two fixed-arity opcodes, `IF` (2) and `IF_ELSE` (3). Variable arity would
  break RPN consistency.
* Operands are type-checked: a Condition statement or logic result, then Result statements.
  Logic operators combine Condition statements.

**D-32 · Pointers.**
* V1 lists "Reference", and the V2 list has "Pointer". **V2.1** defines `ptr()` as an absolute
  word index. It must point backwards ("say what something is before it exists") at the start
  of an item.

## E. Conversations

**D-33 · File header placement.**
* "Speech is like a file … stores the length of the entire speech event".
* **V2.1** makes it external type `0x40`: version byte `0x21`, 40-bit length of the following
  words, big-endian byte order.

**D-34 · Speakers and the Narrator.**
* "Changing speaker simply requires denoting speakers before they begin". "The global scope
  … when given no speaker is … the Narrator … only applies to Dialogues."
* **V2.1** adds `speaker(id)` and `listener(id)` markers at conversation level, which are not
  counted. `speaker(0)` = the Narrator.
* Monologue/dialogue is derived from the number of distinct speaker IDs and is not stored.

## F. Things carried from the 2018 prototype

| 2018 item | V2.1 |
|---|---|
| `lexCant_default.csv`: greet, speaker, self, listener, tall, friend, person, run, enjoy (random 44-bit IDs including flag bits) | Random IDs dropped for hierarchical roots. Mapped: speaker → `auditory_communicator.rel`; listener → `auditory_listener.rel`; person → `sophont.obj` (one meaning per concept); run → `mover.act<Large>` (degree, no new root); tall → `height<M,Large>`; enjoy → `pleasure.act`; self, friend, greet(ing) → new roots |
| Gloss style `self<sub> greet<ver, pre>` with flags in angle brackets | Kept as the idea; full named-flag gloss with `{}` scopes (§11) |
| Typed words `const`, `int`, `float`, `rbga` (sic) | int/float widened; "rbga" fixed to RGBA order |
| numpy uint64 | Pure-stdlib Python ints (no dependency) |
| `Flag_Groups` table approach | Same idea: one constants module (`cant/fields.py`) is the single source of truth |

## G. v2.2: language conventions, lexicon and tooling

None of these change a bit. All are conventions on top of V2.1 (SPEC §14, C-1 … C-18).

**D-35 · The version byte stays `0x21`.**
* v2.2 adds roots and conventions but no layout change.
* **Decision:** the file version names the *wire layout*. Bumping it would make V2.1 decoders
  reject files they can read perfectly well. Lexicon versioning is a separate problem (ROADMAP).

**D-36 · Lexicon growth keeps every existing root ID.**
* SPEC hex, examples and any stored files depend on root IDs.
* **Decision:** new roots only fill new concept slots or new clusters and domains.
  `tools/build_lexicon_v22.py` regenerates the v2.2 rows from the untouched base rows. New
  rows are `source = proposed-v2.2` until the author reviews them.

**D-37 · Scalar qualities use degree, not antonym roots (C-1).**
* The doc's "one meaning per word" plus the degree field (None … Total) make *small* =
  `size<Small>` and *big* = `size<Large>`. Antonym roots would duplicate the axis and waste
  locality: big and small *should* be 0 bits apart in the semantic half.
* The 2018 mapping did the same: run = `mover.act<Large>`, tall = `height<Large>`.

**D-38 · Predicates are object-as-verb (C-2), and location-as-verb means "be at" (C-14).**
* The doc's role × category table already lets an object word act as the verb ("to be X").
  So no copula root is needed, and "is big" costs one word.
* "Be at" for `.loc<V>` was the default offered to the author for v2.2 (no objection). Motion
  uses a motion verb + InProgress + `toward.rel`.

**D-39 · Genitive = non-relation word in the Relation role (C-3).**
* The alternatives were a dedicated `possession.rel` per noun phrase (2 words, and it collides
  with "have"), or a new grammar flag (no bits free in the high half).
* A Relation-role word whose category is not `rel` has no other meaning in V2.1, so the
  combination is free. It is one word per possessor and chains naturally
  ("my friend's house" = 3 words).

**D-40 · Negation = verb degree None (C-4).**
* The doc defines degree None as "not at all". Applied to a verb it is negation, for free.
  When degree is already used (e.g. "is not very big"), a following `null.act<M>` negates.

**D-41 · Prepositions are relations linked to their object (C-5), state verbs are unlinked relations (C-6).**
* This keeps the doc's Jim/Carol/Jack binding rule (Subjects × preceding Objects) for "have",
  "want", "know", and uses the V2.1 link offset for PPs, so "in the garden" binds to *garden*
  rather than to every object.

**D-42 · Questions and imperatives use only existing header subtypes (C-11, C-12).**
* The 8 query subtypes map directly onto who / what / yes-no / when / where / why / how / which.
* Imperative is the existing statement subtype. The addressee is implicit, which matches
  English and saves a word.

**D-43 · Fiction is a scope, not a header bit (C-15; resolves Q-1).**
* Accepted default: a Narrator-level sentence with Topic `story.obj` wraps the fiction. It
  costs one sentence header and one word per fictional passage, not one bit in every header.

**D-44 · Direction stays yaw-pitch-roll (C-16; resolves Q-5).** Accepted default; no change to `dir()`.

**D-45 · Gender neutrality in the lexicon.**
* The doc asks for neutral pronouns, so he/she/it/they all map to `other.obj`. Kin terms map
  to neutral roots (parent, sibling, child). English output therefore says "they" and
  "parent". If gender ever matters, a modifier word (`male.obj<M>`) can carry it. That is
  explicit content, not grammar.

**D-46 · The translator degrades to `text`, never fails (C-17).**
* An English sentence the parser cannot handle becomes `text(sentence) TO_TOPIC` with a
  warning. Unknown words become `text(word)` + a role cast. Output is always a valid Cant
  stream, and the loss is visible.

**D-47 · The English mapping is a separate file.**
* `cant/english/en_lexicon.csv` maps English forms to `root.cat` + grammar flags. `lexicon.csv`
  stays language-neutral (the interlingua), and another natural language would get its own
  mapping file.

**D-48 · Web UI is stdlib-only and local.**
* `http.server` + one inline HTML file: no dependencies, no CDN, binds 127.0.0.1 by default.
  The JSON API is a thin layer over the same functions the CLI uses, so the CLI, tests and UI
  cannot drift apart.

## Open questions for the author

| # | Question | Recommendation |
|---|---|---|
| **Q-1** | V2.0 dropped V1's **Fact vs Fiction** statement subtypes. Should fiction be markable? | **Accepted in v2.2 (D-43).** Yes, but not as a subtype. Mark it as a scope: put fiction inside a Narrator-level sentence whose Topic is a `fiction` root, so everything nested inherits it (uses the doc's scope rule, costs no header bits). Alternative: take 1 bit from word count (20 → 19) for a "hypothetical" flag. |
| **Q-2** | Grammar on externals: casts (current, +1 uncounted word) or a denser typed-lexical form? | Keep casts. They keep externals' full 56-bit payload, match the doc's description of operations, and the cost is one word only when an external needs a role. |
| **Q-3** | Semantic locality: pure tree (current) or add feature bits (animate, made, audible …) for cross-cutting closeness? | Keep the tree until the lexicon passes ~500 roots. Then consider spending the top 2–4 concept bits on features, measured with `tools/locality_report.py`. |
| **Q-4** | Header budget: word count 20 bits / span 32 bits. Other split? | Keep it. 1M words per sentence is ample; a 32-bit span lets a single sentence wrap a large blob (e.g. an image). |
| **Q-5** | Direction convention: the doc says both "z-y-z" and "yaw, pitch, roll". | **Accepted in v2.2 (D-44).** Yaw-pitch-roll (z-y′-x″). It is what "objective: 0 = north, vertical up" implies. |
| **Q-6** | File metadata from the XML sketch (`cant id`, `author`, `dict` URI): binary form? | Add an optional second control word, `0x43 meta`, followed by a Narrator sentence holding `id()`/`uri()` externals. Deferred until a second lexicon exists. |
| **Q-7** | Should `Correction` (`0xF8`) stay as proposed? | Yes. It pairs naturally with Deletion and `ptr()`. |
| **Q-8** | Relation binding with several subjects: Subjects × Objects (current, from the Jim/Carol/Jack example) or nearest pair? | Keep Subjects × Objects with the explicit link for narrowing. It matches the doc example exactly. |
