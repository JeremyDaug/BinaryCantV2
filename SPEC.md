# Binary Cant V2.1 — Specification

Binary Cant is a machine-first language built on the 64-bit word. This document is the
normative bit-level spec for **V2.1**. It consolidates the user's *Binary Cant* Google Doc
(V1 16/32-bit notes plus the V2.0 64-bit draft), the *Binary Cant Spreadsheet*, and the 2018
Python prototype into one consistent design. The reference codec in `cant/` implements every
rule here. `tests/test_spec_examples.py` checks every example in §12 against the hex shown.

**Provenance tags** are used throughout:

| Tag | Meaning |
|---|---|
| **[DOC]** | Taken from the user's Binary Cant doc (V1 or V2.0 sections) |
| **[SHEET]** | Taken from the Binary Cant Spreadsheet |
| **[2018]** | Carried over from the 2018 Python prototype (`gh-BinaryCant`) |
| **[V2.1]** | New decision made in this revision. Each one is explained in DECISIONS.md |

Bit 63 is the most significant bit. Hex masks are full 64-bit masks. "Word" always means one
64-bit unit unless it says *counted word* (see §8).

---

## 1. Priorities

These come straight from the doc **[DOC]** and decide every tie in this spec:

1. **Consistency**: no exceptions to the rules. Reserved values are *errors*, never silently accepted.
2. **Clarity**: one meaning per word, and no ambiguous sentences.
3. **Density**: everything fits the word length.
4. **Machines first**: organic readability is not a goal. The text *gloss* in §11 is a debugging
   aid for humans. It is not the language. A pronounceable form is a low-priority roadmap item.

Guidelines **[DOC]**: say what something is before it exists; operate only when everything
exists (Reverse Polish Notation); sentences carry their own length; nested sentences and
externals count as one word; sentences are scopes; a conversation is a file with a total length.

---

## 2. Word classes

The top two bits of every word give its class:

| Bits 63..62 | Class | Top byte range | Origin |
|---|---|---|---|
| `00` | **Lexical**: an in-language word (grammar half + semantic half) | `0x00`–`0x3F` | [DOC] "inside the language" |
| `01` | **External**: a typed word from "outside the language" (numbers, colours, time, IDs, operations …) | `0x40`–`0x7F` | [DOC] flag; [V2.1] placement |
| `10` | **Sentence header, Query** | `0x80`–`0xBF` | [DOC] V2.0 header values |
| `11` | **Sentence header, Statement** | `0xC0`–`0xFF` | [DOC] V2.0 header values |

The conversation file header and the speaker/listener markers are external control types
(`0x40`–`0x42`, §6.1). That keeps all four classes uniform, and a file always starts with byte
`0x40` followed by the version byte `0x21`. **[V2.1]**

---

## 3. Lexical word (class `00`)

A lexical word is two 32-bit halves **[DOC core idea]**:

* **High half (bits 63..32): grammar and relational meaning.** It says how this word works in
  the sentence and how it binds to other words.
* **Low half (bits 31..0): semantic meaning.** It holds a 30-bit root and a 2-bit category.

```
 63 62 61-59 58-57 56-55 54-53 52-50 49  48  47-46 45  44 ........ 35 34-32 | 31 ........................ 2  1-0
 [00][role][tmp ][prg ][rec ][deg ][E][D][plu ][L][ link offset   ][res ] | [          root (30)         ][cat]
```

### 3.1 High half: grammar/relational fields

| Bits | Width | Field | Mask | Values | Origin |
|---|---|---|---|---|---|
| 63–62 | 2 | class | `0xC000000000000000` | `00` | [DOC] |
| 61–59 | 3 | grammar role | `0x3800000000000000` | 0 Subject, 1 Object, 2 Topic, 3 Verb, 4 Modifier, 5 Relation, 6 Fusion, 7 *reserved* | [DOC] (V1 positions; Fusion from V2 text) |
| 58–57 | 2 | temporal aspect | `0x0600000000000000` | 0 Timeless, 1 Past, 2 Present, 3 Future | [DOC] |
| 56–55 | 2 | progression | `0x0180000000000000` | 0 Unprogressed, 1 Unstarted, 2 InProgress, 3 Complete | [DOC] |
| 54–53 | 2 | recurrence | `0x0060000000000000` | 0 NonRecurring, 1 Irregular, 2 Continuous, 3 Habitual | [DOC] |
| 52–50 | 3 | degree / intensity | `0x001C000000000000` | 0 Unspecified, 1 None, 2 Minimal, 3 Small, 4 Medium, 5 Large, 6 Maximal, 7 Total | [DOC] |
| 49 | 1 | emphasis | `0x0002000000000000` | 0 unemphasized, 1 emphasized | [DOC] |
| 48 | 1 | determinative | `0x0001000000000000` | 0 nonspecific (a/an), 1 specific (the) | [DOC] |
| 47–46 | 2 | plurality | `0x0000C00000000000` | 0 Unnumbered, 1 Singular, 2 Plural (nonspecific), 3 Numbered (plural, specific) | [DOC]/[2018] order; [V2.1] Numbered binding |
| 45 | 1 | link flag L | `0x0000200000000000` | 0 implicit binding, 1 explicit link | [V2.1] |
| 44–35 | 10 | link offset | `0x00001FF800000000` | 1..1023 when L=1; must be 0 when L=0 | [V2.1] |
| 34–32 | 3 | reserved | `0x0000000700000000` | must be 0 | [V2.1] |

The top 16 bits are **exactly the V1 16-bit "Binary logic" layout** from the doc. The doc's
own encoded word `0x1C00…` for *Nothing⟨Verb, Present⟩* is therefore still valid in V2.1.
V1 put plurality at the top of the semantic half. V2.1 moves it into the grammar half (bits
47–46), right after the V1 block. **[V2.1]**

### 3.2 Low half: semantic fields

| Bits | Width | Field | Mask | Notes |
|---|---|---|---|---|
| 31–2 | 30 | root ID | `0x00000000FFFFFFFC` | One concept. Layout in §9 (domain 8 / cluster 8 / concept 14) |
| 1–0 | 2 | category | `0x0000000000000003` | `00` object/abstract/state, `01` relation, `10` action, `11` location **[SHEET]** |

Inside the root, §9 assigns: domain at word bits 31–24 (`0x00000000FF000000`), cluster at
23–16 (`0x0000000000FF0000`), and concept at 15–2 (`0x000000000000FFFC`).

One root has four **sibling senses**, one per category. For example, `manipulator` has
object *manipulator (hand)*, relation *one who manipulates another*, action *to manipulate*,
and location *at the manipulator (in hand)*. The senses differ only in bits 1..0, so related
words across categories always sit together **[DOC rule]**. Every sense is its own word with
exactly one meaning (Clarity). A sense with no definition in the lexicon is unassigned.
Encoders must refuse it unless the root is given raw.

Reserved roots **[DOC Words Methodology]**:

| Root | obj `00` | rel `01` | act `10` | loc `11` |
|---|---|---|---|---|
| `0x00000000` **null** | Null | Unrelated | Nothing (happening) | Nowhere |
| `0x3FFFFFFF` **everything** | Everything | related to everything *(proposed)* | everything happening *(proposed)* | Everywhere |

---

## 4. Grammar semantics

### 4.1 Roles **[DOC]**

* **Subject**: the actor or actors. A sentence may have more than one.
* **Object**: what is acted upon. A sentence may have more than one.
* **Topic**: what the conversation relates to without talking about it directly.
* **Verb**: a change of state or information. Objects used as verbs mean *to be / become*
  (`you⟨S⟩ cat⟨V⟩` = you are a cat). Locations used as verbs mean *to be at*
  (`I⟨S⟩ home⟨V⟩` = I am home). Progression refines this: Unstarted/InProgress = *going to*,
  Complete = *arrived at* **[V2.1, DECISIONS D-20]**. Relations used as verbs mean *acts like a*.
* **Modifier**: like an adjective or adverb. Modifiers stack and bind to the nearest preceding
  non-modifier (`Jim⟨S⟩ cat⟨M⟩ red⟨M⟩` all apply to Jim). Any non-modifier ends the chain.
* **Relation**: a relative state between static entities. With implicit binding it applies
  *every preceding Subject to every preceding Object* in the sentence (`John⟨S⟩ Billy⟨O⟩
  parent⟨R⟩` = John is Billy's parent).
* **Fusion**: like a modifier, but it *combines* with its head instead of qualifying it
  (`Jim⟨S⟩ cat⟨F⟩ red⟨F⟩` = Jim-Cat-Red). Fusions stack.
* Role 7 is reserved. Decoders reject it.

### 4.2 Explicit links (relational structure) **[V2.1]**

The doc binds words by adjacency. That works, but some sentences can only be said one way or
must be split. V2.1 uses the spare high-half bits for an explicit **back-link**. When L=1,
`link offset = k` names the *k-th counted word before this one in the same sentence* (§8).
Operations are skipped, and a nested sentence or an external counts as one word. Links can
only point backwards ("say what something is before it exists"). They never leave the
sentence (scope).

| Role of the linking word | Meaning of an explicit link |
|---|---|
| Modifier / Fusion | binds to the linked word instead of the adjacency chain head |
| Relation | relates the preceding Subjects to **only** the linked word (instead of all preceding Objects) |
| Verb | the linked word is this verb's actor (overrides "all Subjects") |
| Subject / Object / Topic | apposition: same referent as the linked word |

L=0 always means the doc's implicit rules, so a V2.0-style sentence without links is unchanged.

### 4.3 Numbered plurality **[V2.1]**

`plurality = Numbered` means "a specific number of". The number is the **operand immediately
before the word**: a numeric external (§6.2) or the result of an arithmetic operation. The
validator enforces this. (`int(3) sophont⟨S,Numbered⟩` = three sophonts.) This follows the
2018 prototype's `(int)1000<obj> person<sub,num>`.

### 4.4 Defaults **[DOC Word defaults]**

Every all-zero field means "unspecified / neutral". A word claims nothing it does not state.

---

## 5. Sentence header (class `1x`)

```
 63  62  61-59   58-55       54-52        51 .............. 32  31 ........................ 0
 [1][Q/S][sub ][affection ][evidential ][   word count (20)   ][        span (32)          ]
```

| Bits | Width | Field | Mask | Origin |
|---|---|---|---|---|
| 63 | 1 | header flag = 1 | `0x8000000000000000` | [DOC V2.0] |
| 62 | 1 | 0 Query, 1 Statement | `0x4000000000000000` | [DOC V2.0] |
| 61–59 | 3 | subtype | `0x3800000000000000` | [DOC V2.0] |
| 58–55 | 4 | affection | `0x0780000000000000` | [DOC V2.0] |
| 54–52 | 3 | evidentiality | `0x0070000000000000` | [DOC V2.0] |
| 51–32 | 20 | **word count**: counted words in this sentence (max 1 048 575) | `0x000FFFFF00000000` | [DOC] rule; [V2.1] width |
| 31–0 | 32 | **span**: total 64-bit words in the body after the header | `0x00000000FFFFFFFF` | [V2.1] |

The top 12 bits reproduce the doc's V2.0 hex values exactly. Type byte `0x80 + 8·subtype`
(queries) or `0xC0 + 8·subtype` (statements). Affection `0x800 + 8·a`. Evidentiality `0x800 + e`.

| Subtype | Query (`0x80`…) | Statement (`0xC0`…) |
|---|---|---|
| 0 | `0x80` Subject (who) | `0xC0` Assertion |
| 1 | `0x88` Object (whom) | `0xC8` Deletion |
| 2 | `0x90` Verb (what) | `0xD0` Condition |
| 3 | `0x98` Time (when) | `0xD8` Result |
| 4 | `0xA0` Location (where) | `0xE0` Imperative |
| 5 | `0xA8` Reasoning (why) | `0xE8` Exclamatory |
| 6 | `0xB0` Explain (how) | `0xF0` Uncertain |
| 7 | `0xB8` Specify (which) | `0xF8` Correction *(proposed; doc slot "[empty] (correction)?")* |

| Value | Affection | | Value | Evidentiality |
|---|---|---|---|---|
| 0 | Honest (neutral) | | 0 | Direct (observation) |
| 1 | Dishonest | | 1 | Hearsay (quotation) |
| 2 | Happy | | 2 | Expectation (assumption) |
| 3 | Sad | | 3 | Conclusion (from evidence) |
| 4 | Fear | | 4 | Generalization |
| 5 | Anger | | 5 | Postulate (theory) |
| 6 | Anticipation | | 6 | Opinion |
| 7 | Surprise | | 7 | *reserved* |
| 8 | Benevolent | | | |
| 9 | Malice | | | |
| 10 | Pain | | | |
| 11 | Pleasure | | | |
| 12–15 | *reserved* | | | |

**Sentence-type semantics [DOC V2.0]:**

* Assertion, Uncertain (and the doc's fact/fiction notion) must update data or answer an open question.
* Deletion removes a previous statement. Point at it with `ptr()`.
* Correction (proposed) replaces a pointed-to statement.
* Imperative commands the listener unless an Object names who is commanded. Exclamatory is an
  imperative aimed at the speaker.
* A Query names the missing part with its subtype. Its words add detail. With no words, it
  applies to the previous sentence. With no previous sentence, it is aimed at the listener.
* Condition and Result sentences are inert until an `IF`/`IF_ELSE` operation follows them (§7).

---

## 6. External words (class `01`)

```
 63 62 61 ...... 56 55 ............................................... 0
 [01][  type (6)  ][                   payload (56)                     ]   + continuation words (type-defined)
```

The top byte is `0x40 | type`. The low 3 bits of the type are a subtype inside one of eight
groups of 8, so the doc's V1 "format groupings" (colour, direction, number, atom/compound)
survive as groups. **Continuation words** are raw 64-bit data that follow some heads. The
head word alone fixes how many there are, so a parser can always skip an external without
understanding it. A head plus its continuations is **one counted word** **[DOC]**. Every
64-bit word still counts toward span and file length.

### 6.1 Registry

| Top byte | Name (gloss) | Payload / continuations | Origin |
|---|---|---|---|
| **Control** | | | |
| `0x40` | `file` | version(8) `0x21` · reserved(8) · length(40). Word 0 only | [DOC] "speech is a file"; [V2.1] |
| `0x41` | `speaker(id)` | 56-bit speaker ID; 0 = Narrator. Conversation level only | [DOC V2.0] dialogues; [V2.1] |
| `0x42` | `listener(id)` | 56-bit listener ID; 0 = everyone. Conversation level only | [V2.1] |
| **Numbers** | | | [DOC V1] widened |
| `0x48` | `int(n)` | signed 56-bit two's complement | V1: signed 23-bit |
| `0x49` | `float(x)` | IEEE-754 binary32 in bits 31..0; 55..32 = 0 | V1: 1/6/17 custom float |
| `0x4A` | `float64(x)` | payload 0; +1 word IEEE-754 binary64 | [V2.1] |
| `0x4B` | `complex(re,im)` | signed 28 · signed 28 | V1: 12/12 |
| `0x4C` | `rational(±n/d)` | sign(1) · numerator(27) · denominator(28, ≠0) | V1: 1/11/12 |
| `0x4D` | `bigint(n)` | bits 31..0 = word count k ≥ 1; +k words two's complement big-endian | [V2.1] |
| **Colours** | | | [DOC V1] |
| `0x50` `0x51` | `rgb(#RRGGBB)` `rgba(#RRGGBBAA)` | 8 bits/channel in the low bits; unused high bits 0 | V1 RGB; RGBA from V2 list |
| `0x52` `0x53` `0x54` | `hsl` `yuv` `ycbcr` | 3 × 8 bits | [DOC V1] |
| `0x55` | `rgba14(r,g,b,a)` | 4 × 14 bits: the doc's "expanded" colour | [V2.1] |
| **Direction** | | | [DOC V1] |
| `0x58` | `dir(yaw,pitch,roll[,relative][,to][,frame=F])` | bit55 relative · bit54 to(1)/from(0) · bits53–52 frame (speaker, listener, subject, object; relative only) · 51–48 reserved · yaw16 · pitch16 · roll16, unit τ/65536 | V1: z-y-z, 8-bit steps τ/256 |
| **Chemistry** | | | [DOC V1] |
| `0x60` | `atom(P,N,E)` | protons16 · neutrons16 · electrons16 · reserved8 | V1: 9 bits each |
| `0x61` | `compound(node; …)` | payload = node count k ≥ 1; +k node words (below) | V1 tree, widened |
| **Time** | | | [DOC] (unfinished there) |
| `0x68` | `time(s)` | signed 56-bit seconds since 1970-01-01T00:00:00Z (Unix epoch) | [V2.1] completes "Raw time" |
| `0x69` | `duration(s)` | signed 56-bit seconds | [V2.1] |
| `0x6A` | `datetime(ISO-8601)` | year s20 · month4 · day5 · hour5 · min6 · sec6 · UTC offset s7 (×15 min) · reserved3 | [V2.1] completes "Formatted" |
| `0x6B` | `time_ns(ns)` | payload 0; +1 word signed ns since epoch | [V2.1] |
| **Reference / identity** | | | [DOC V2 list] |
| `0x70` | `ptr(i)` | absolute word index in this file (0 = file header). Must point *backwards* at the start of an item | [DOC V1 "Reference"] |
| `0x72` | `id(n)` | 56-bit opaque ID: a specific name (Jim, Carol …) | [DOC] "IDs (Specific names)" |
| `0x73` | `sig(alg,hex)` | blob layout; tag = algorithm (0 unspecified, 1 ed25519, 2 ecdsa-p256, 3 hmac-sha256) | [DOC] Signatures, `skey` |
| `0x74` | `coord(lat,lon)` | signed 28 · signed 28, unit 360°/2²⁸ (≈1.3×10⁻⁶°, ≈15 cm) | [DOC] Coordinates |
| `0x75` | `uri("…")` | blob layout, UTF-8 | [DOC] XML `src=URI` |
| **Raw data** | | | [DOC] "literal ascii, images, gifs …" |
| `0x78` | `text("…")` | blob layout, UTF-8, tag 0 | [DOC] Characters |
| `0x79` | `bytes(fmt,hex)` | blob layout; tag = format (0 raw, 1 png, 2 jpeg, 3 gif, 4 webp) | [DOC] |
| `0x7A` | `char(U+XXXX)` | one Unicode code point (≤ `0x10FFFF`) | [DOC] Characters |
| **Operations** | | | |
| `0x7E` | (operation) | opcode16 · reserved8 · operand32. See §7 | [DOC] |
| other | *reserved* | Decoders reject them | |

**Blob layout** (`sig`, `uri`, `text`, `bytes`): payload = tag(8) · reserved(16) · byte length L(32).
Then ⌈L/8⌉ continuation words carry the bytes big-endian, zero-padded. Padding must be zero.

**Compound node word** (pre-order tree; each node states its child count):

| Bits | Field |
|---|---|
| 63–62 | bond-to-parent type (0 ionic, 1 covalent, 2 metallic, 3 none) |
| 61–58 | bond-to-parent count |
| 57–56 | secondary bond type (to previous sibling; *proposed*) |
| 55–52 | secondary bond count |
| 51–44 | child count |
| 43–32 | reserved (0) |
| 31–16 | protons (element) |
| 15–0 | neutrons (65535 = natural isotope mix) |

The root node must have bond type `none`, count 0. The tree must be exactly complete.

### 6.2 Numeric types

`int`, `float`, `float64`, `complex`, `rational`, and `bigint` are *numeric*. Arithmetic
accepts only these, and only they can satisfy `Numbered` plurality.

---

## 7. Operations (external type `0x7E`)

An operation word is an RPN operator run at read time **[DOC]**. It pops operands from its
scope's stack and pushes one result. Operations **never count** toward a sentence's word count,
because they mean nothing alone **[DOC V2.0]**. Each one still takes one word of span.

```
 0x7E | opcode (16) | reserved (8) = 0 | operand (32)
```

The **stack** of a scope holds the counted words of that scope in order: lexical words,
externals, and nested sentences (each nested sentence is one entry). Each operation replaces
its operands with its result. An operation can never reach outside its own sentence
**[DOC scoping]**.

| Opcode | Name | Pops | Semantics |
|---|---|---|---|
| `0x0001` | ADD | 2 | a b → a+b |
| `0x0002` | SUB | 2 | a b → a−b |
| `0x0003` | MUL | 2 | a b → a·b |
| `0x0004` | DIV | 2 | a b → a/b (exact rational for integers/rationals; ÷0 is an error) |
| `0x0005` | POW | 2 | a b → aᵇ |
| `0x0006` | LOG | 2 | x b → log_b x |
| `0x0007` | LN | 1 | x → ln x |
| `0x0008` | LB | 1 | x → log₂ x |
| `0x0100`+r | TO_SUBJECT … TO_FUSION | 1 | **grammar cast**: give the operand role r (0..6) plus the grammar fields in the operand |
| `0x0200` | AND | 2 | conjunction of conditions |
| `0x0201` | OR | 2 | disjunction |
| `0x0202` | NOT | 1 | negation |
| `0x0203` | NAND | 2 | |
| `0x0204` | NOR | 2 | |
| `0x0205` | XNOR | 2 | the doc's "Xand" (equivalence) |
| `0x0206` | XOR | 2 | |
| `0x0300` | IF | 2 | cond then → evaluate *then* if cond holds |
| `0x0301` | IF_ELSE | 3 | cond then else → If-Then-Else **[DOC V2.0]** |

* **Arithmetic** operands must be numeric (§6.2). The reference codec evaluates them and shows
  the result when decoding.
* **Casts** **[DOC: "turn a colour into a topic or a number into an object"]**. The 32-bit
  operand is a *grammar template*: the same layout as a lexical high half (bits 63..32 moved
  down to 31..0). The class and role bits must be 0, because the opcode supplies the role.
  Every other field (tense, degree, link …) applies to the cast item. Links count from the
  operation's position. Casts cannot carry `Numbered`.
* **Logic** operands must be Condition statements (`0xD0`) or other logic results.
* **IF / IF_ELSE**: the first operand is a Condition statement or a logic result. The branches
  must be Result statements (`0xD8`). Conditions and Results are not evaluated until the
  operation runs **[DOC]**. Conditionals may appear inside a sentence or at conversation level.

---

## 8. Scoping, nesting, counting and framing

1. **Counted words** **[DOC]**. A sentence's *word count* is the number of lexical words,
   external heads (each with its continuations is 1), and nested sentences (each is 1) directly
   inside it. Operations are not counted.
2. **Span** **[V2.1]**. A sentence's *span* is the total number of 64-bit words in its body:
   nested sentences in full, continuations, and operations. A parser needs only the span to
   skip a sentence. The span also settles one framing question: an operation right after a
   nested sentence belongs to the outer sentence if it falls outside the inner span.
3. **Validation**. Decoders must reject: a count that differs from the actual count, a span
   that runs past the parent's end, an external whose continuations leave the scope, and any
   reserved value.
4. **Scopes** **[DOC]**. A nested sentence shares its parent's context. Changes it makes (for
   example a redefined Topic) revert when it ends. The conversation is the outermost scope.
5. **Placement**. Lexical words and non-control externals appear only inside sentences.
   `speaker`/`listener` markers appear only at conversation level. They are not counted and are
   not operands. Operations may appear at either level.
6. **Wordless sentences** are legal (count 0, span 0), for example the doc's bare "What?".
7. **Limits**: 1 048 575 counted words and 2³²−1 span words per sentence; 2⁴⁰−1 words per file.

---

## 9. Semantic locality (Hamming distance ≈ semantic closeness) **[V2.1]**

The goal is a soft one: the more alike two meanings are, the fewer bits their words differ by.
V2.1 builds this into the 30-bit root as a three-level tree, with codes picked for their
distance properties:

```
 root (30) = domain (8) | cluster (8) | concept (14)
 word bits:  31......24   23......16    15.........2   | category 1..0
```

* **Domain** and **cluster** values are drawn from the 16 codewords of the first-order
  Reed–Muller code RM(1,3) (the extended Hamming [8,4,4] code):
  `00 0F 33 3C 55 5A 66 69 96 99 A5 AA C3 CC F0 FF`. Any two distinct codewords differ in
  **at least 4 bits**. Words in different domains are therefore always ≥ 4 bits apart, and
  usually much more.
* **Concept** is the sibling's index inside its cluster, **Gray-coded**. Consecutive siblings
  differ by exactly 1 bit, and nearby siblings by a few.
* **Category** (bits 1..0) holds the four senses of a root. They differ by 1–2 bits.

Measured over the seeded lexicon (`python3 tools/locality_report.py`; asserted in `tests/test_locality.py`):

| Pair type | n | mean Hamming distance (of 32) |
|---|---|---|
| same root, different sense | 110 | 1.34 |
| same cluster (siblings) | 170 | 2.17 |
| same domain, other cluster | 813 | 5.69 |
| different domain | 4685 | 10.12 (min 4) |

The CLI reports both metrics: `cant distance mover.act manipulator.obj`.

**Tradeoffs and limits**

* **Hamming vs tree distance.** The tree (prefix) distance is exact and cheap: compare the
  domain, then cluster, then root. Hamming distance is only a rough proxy. Two unrelated roots
  in "neighbouring" codewords can be as close as 4 bits, while siblings with distant Gray
  indices can be 10+ bits apart. Use tree distance when the answer must be exact. Use Hamming
  when you need a hardware-friendly XOR+popcount similarity or error tolerance.
* **One parent per concept.** A tree gives every concept one domain. *Instrument* sits next
  to *tool* (artifacts) and far from *music* (arts). Cross-cutting closeness would need
  feature bits (e.g. "animate", "made", "audible"). That is listed as an open question.
* **Address space.** Only 16 × 16 of the 256 × 256 domain/cluster values are codewords. That
  still leaves 4.2 M concepts (16 × 16 × 16 384). Non-codeword values are reserved as
  extension space, for future domains or private lexicons. The decoder accepts raw roots
  there but reports them as "not in lexicon".
* **Grammar half excluded.** Locality is defined on the 32-bit semantic half. Full-word
  distance also counts grammar differences, which is intended: *the cat* and *a cat* are the
  same concept.
* **Not robust to every edit.** A 1-bit error inside the concept field yields a sibling, not
  the same word. Error detection belongs at the transport layer.

---

## 10. Conversation file format

* A file is a sequence of 64-bit words, **big-endian** (most significant byte first). **[V2.1]**
* Word 0 is the **file header** `0x40 | 0x21 | 0x00 | length(40)`. `length` is the number of
  words after the header **[DOC: "stores the length of the entire speech event"]**.
* Then come conversation-level items in order: sentences, `speaker`/`listener` markers, and
  operations.
* **Monologue / dialogue** **[DOC V2.0]**. A conversation with at most one distinct non-zero
  speaker ID is a monologue, and its speaker needs to be stated once at most. With two or more,
  it is a dialogue. In a dialogue, sentences before the first `speaker` marker, or after
  `speaker(0)`, belong to the **Narrator**. The Narrator is not spoken or heard. It sets shared
  context for the whole conversation.
* A *bare stream* (no file header) is allowed for embedding and for the examples in §12.
  Pointer indices in a bare stream are numbered as if a header sat at index 0.

---

## 11. Gloss syntax (reference text form)

The gloss is the codec's text form for writing and inspecting cant. It is a tool, not the
language. `;` starts a comment.

```
item      := sentence | lexical | external | operation | marker
sentence  := ("QUERY" | "STATEMENT") "<" subtype ["," affection] ["," evidentiality] ">" "{" item* "}"
lexical   := root "." ("obj"|"rel"|"act"|"loc") "<" flag ("," flag)* ">"      ; a role flag is required
root      := lexicon-key | 0xHEX                                              ; raw 30-bit root
flag      := S|O|T|V|M|R|F | Timeless|Past|Present|Future | Unprogressed|Unstarted|InProgress|Complete
           | NonRecurring|Irregular|Continuous|Habitual
           | Unspecified|None|Minimal|Small|Medium|Large|Maximal|Total
           | ! | Specific | Unnumbered|Singular|Plural|Numbered | ^N
external  := type "(" args ")"                                                ; §6.1 names
operation := OPNAME [ "<" flag,... ">" ]                                      ; flags only on TO_* casts
marker    := "speaker(" id ")" | "listener(" id ")"
```

Affection defaults to Honest and evidentiality to Direct. In canonical (decoded) output all
three header fields are always printed.

---

## 12. Worked examples

Each example gives the English, a gloss, and the exact hex. Every pair is checked by the test
suite. Examples are bare streams unless marked `; file`.

### 12.1 "What is that?" (doc example)

The doc writes `Query<Clarify, Honest, Direct, 0>` = `0x48000000` (V1). V2.0 renamed
*Clarify (What)* to *Verb (What)*, so V2.1 gives type byte `0x90`. With zero words, the query
applies to the previous sentence (or to the listener) **[DOC]**:

```cant
QUERY<Verb,Honest,Direct>{}
```
```hex
9000000000000000
```

Stated explicitly, "what is *that* (being)?": the query targets the verb, and `that` is the subject.

```cant
QUERY<Verb,Honest,Direct>{
    that.obj<S,Present,Specific>
}
```
```hex
9000000100000001
0401000000330018
```

### 12.2 "Nothing is happening." (doc example)

The doc's V1 words were `0x60400001` (header) and `0x1C000002` (word). The word half carries
over *unchanged*: `0x1C…` = Verb, Present, and root 0 category action = *Nothing (happening)*.
The doc's header used *Dishonest*. V2.1 uses Honest, because this is plainly a neutral
statement (see DECISIONS D-07).

```cant
STATEMENT<Assertion,Honest,Direct>{
    null.act<V,Present>
}
```
```hex
C000000100000001
1C00000000000002
```

### 12.3 "His shirt is red." (completes the doc's unfinished example)

*He* is the gender-neutral third party `other` (doc rule: assume neutrality). *Shirt* is
`cover` (clothing). *Red* is an external colour, cast to a Verb ("is red"). The cast's explicit
link `^3` makes the shirt the actor of "is red", not *he*.

```cant
STATEMENT<Assertion,Honest,Direct>{
    other.obj<S,Present,Specific,Singular>
    cover.obj<O,Present,Specific,Singular>
    possession.rel<R,Present>
    rgb(#FF0000)
    TO_VERB<Present,^3>
}
```
```hex
C000000400000005
040140000033000C
0C01400055000000
2C000000003C0001
5000000000FF0000
7E01030004002018
```

Gloss: *[the singular other]⟨S⟩ [the singular cover]⟨O⟩ possessor⟨R⟩ #FF0000→Verb(actor = cover)*.
Count 4 (the cast is not counted), span 5.

### 12.4 Relations: "Jim and Carol are a couple, and Carol and Jack are Jim's family." (doc example)

Names are `id()` externals, cast to roles with `TO_SUBJECT`/`TO_OBJECT` **[DOC operations]**.
Implicit relation binding applies each relation to all preceding Subjects × Objects. So
`couple` links Jim–Carol, and `family` links Jim–{Carol, Jack}, exactly as in the doc.

```cant
STATEMENT<Assertion,Honest,Direct>{
    id(1) TO_SUBJECT
    id(2) TO_OBJECT
    partner.rel<R,Present>
    id(3) TO_OBJECT
    kin.rel<R,Present>
}
```
```hex
C000000500000008
7200000000000001
7E01000000000000
7200000000000002
7E01010000000000
2C0000003C00000D
7200000000000003
7E01010000000000
2C0000003C000005
```

Count 5, span 8. To say *only Jack* is family, write `kin.rel<R,Present,^1>`.

### 12.5 External number: "Three sophonts are moving."

```cant
STATEMENT<Assertion,Honest,Direct>{
    int(3)
    sophont.obj<S,Present,Numbered>
    mover.act<V,Present,InProgress>
}
```
```hex
C000000300000003
4800000000000003
0400C00033000000
1D0000000F000006
```

### 12.6 RPN operation: "Two plus three is five." (a conclusion)

`int(2) int(3) ADD` leaves 5 on the stack. `TO_SUBJECT` makes it the subject. `int(5)
TO_VERB<Present>` reads "is (being) 5". Count 3, span 6.

```cant
STATEMENT<Assertion,Honest,Conclusion>{
    int(2) int(3) ADD TO_SUBJECT
    int(5) TO_VERB<Present>
}
```
```hex
C030000300000006
4800000000000002
4800000000000003
7E00010000000000
7E01000000000000
4800000000000005
7E01030004000000
```

### 12.7 Nesting: "I am saying that you are home."

The inner sentence is one counted word of the outer sentence, and `TO_OBJECT` makes it what is
said. The outer span (6) includes the inner header and words. The outer count is 3.

```cant
STATEMENT<Assertion,Honest,Direct>{
    self.obj<S,Present>
    auditory_communicator.act<V,Present>
    STATEMENT<Assertion,Honest,Direct>{
        addressee.obj<S,Present>
        dwelling.loc<V,Present>
    }
    TO_OBJECT
}
```
```hex
C000000300000006
0400000000330000
1C0000000F0F0002
C000000200000002
0400000000330004
1C000000553C0003
7E01010000000000
```

### 12.8 Conditional: "If you are home, I will be home."

A location used as a verb means *to be at / go to*. Neither sentence is evaluated until `IF`
runs **[DOC]**.

```cant
STATEMENT<Condition,Honest,Direct>{
    addressee.obj<S,Present>
    dwelling.loc<V,Present>
}
STATEMENT<Result,Honest,Direct>{
    self.obj<S,Future>
    dwelling.loc<V,Future>
}
IF
```
```hex
D000000200000002
0400000000330004
1C000000553C0003
D800000200000002
0600000000330000
1E000000553C0003
7E03000000000000
```

### 12.9 A complete dialogue file: Narrator, "What is that?" / "That is a tool."

```cant
; file
STATEMENT<Assertion,Honest,Direct>{
    that.obj<T,Present,Specific>
}
speaker(1)
QUERY<Verb,Honest,Direct>{
    that.obj<S,Present,Specific>
}
speaker(2)
STATEMENT<Assertion,Honest,Direct>{
    that.obj<S,Present,Specific>
    tool.obj<V,Present>
}
```
```hex
4021000000000009
C000000100000001
1401000000330018
4100000000000001
9000000100000001
0401000000330018
4100000000000002
C000000200000002
0401000000330018
1C000000550F0000
```

The Narrator sets *that* as the shared Topic. Speaker 1 asks what it is. Speaker 2 answers
that it *is a tool* (object used as a verb = "to be").

---

## 13. Conformance

* An **encoder** must emit correct counts, spans, and file length. It must never emit
  reserved values or undefined lexicon senses (raw roots are allowed).
* A **decoder** must reject everything listed in §8.3, plus: reserved roles, affections,
  evidentialities, external types, and opcodes; non-zero reserved bits; link-flag/offset
  disagreement; links or operations that reach outside their sentence; type-invalid operations;
  forward or misaligned pointers; and file-length or version mismatches.
* Round-trip: decode(encode(x)) must reproduce x bit for bit.
