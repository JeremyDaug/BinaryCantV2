# English ↔ Binary Cant translation (v2.2)

`cant/english/` is a **rule-based, standard-library-only** translator between plain English and
Binary Cant. It is a convenience layer for humans. Cant is the language; English is a lossy view
of it. The translator never fails: anything it cannot handle is carried through as a `text(…)`
external with a warning, so you always get a valid Cant stream.

```sh
python3 -m cant translate en2cant "Did you see my two red dogs in the garden yesterday?"
python3 -m cant translate en2cant -f hex -o msg.cant "The cat sleeps."   # also writes binary
python3 -m cant translate cant2en msg.cant                               # binary, hex text or gloss file
python3 -m cant translate cant2en "4021000000000003 A000000200000002 0001400000330004 1C0000000F660002"
python3 -m cant translate cant2en "STATEMENT<Assertion>{ null.act<V,Present> }"
python3 -m cant serve        # the same thing in a browser (Translate tab)
```

```python
from cant.english import en2cant, cant2en
conv, warnings = en2cant("Where do you live?")
cant2en(conv)   # 'Where do you live?'
```

## 1. How it works

**en2cant** is a hand-written parser, not a statistical model:

1. Split into sentences, tokenize, expand contractions. `'s` after a pronoun or wh-word means
   "is"; otherwise it is a possessive. A trailing `(happily)` sets the header's affection.
2. Read prefixes: an evidential (`Reportedly,` → Hearsay, `Presumably,` → Expectation,
   `Therefore,` → Conclusion, `Generally,` → Generalization, `Hypothetically,` → Postulate,
   `In my opinion,` → Opinion), and `Perhaps`/`Maybe` → the Uncertain subtype.
3. Choose the sentence shape: a question (yes/no or wh-), a conditional (`If A, B.`), an
   imperative (starts with a verb, or `Please`/`Do not`), or a declarative.
4. Parse noun phrases (determiners, numbers, adjectives, colours, possessives, `and`-lists),
   then the verb group (an auxiliary state machine for will / do / have + participle /
   be + -ing / going to / not), then the predicate or objects, prepositional phrases and adverbs.
5. Map each word through `cant/english/en_lexicon.csv` (english → root.category + grammar
   flags + irregular forms). Build Cant words using the conventions in §2. Encode.

**cant2en** reads *any* valid Cant, not only its own output:

1. Simulate the RPN stack so externals, casts (`TO_SUBJECT` …), numbers and arithmetic become
   units with a role.
2. Bind modifiers, genitives and appositions the way SPEC §8 and the v2.2 conventions say.
3. Pick an English word for each root from the same mapping file. It chooses the most specific
   entry whose flags match the grammar (e.g. `size.obj` + degree Small → "small"). If none
   matches, it falls back to the lexicon gloss.
4. Assemble subject, verb (conjugated from tense / progression / recurrence / degree None =
   negation, with do-support and inversion for questions), objects, PPs and adverbs. Add the
   evidential prefix, affection suffix and punctuation. Speakers become `Speaker N:` lines and
   the Narrator becomes `Narrator:`.

## 2. Conventions used to express English in Cant

These are **language conventions**, not bit-layout changes; v2.2 keeps the V2.1 layout and file
version byte `0x21`. Each is recorded in SPEC §14 and DECISIONS §G.

| English | Cant | Example |
|---|---|---|
| a / the | plurality Singular; determinative bit = Specific | `the cat` → `cat.obj<S,Specific,Singular>` |
| plural / number | plurality Plural; or `int(n)` / `float64(x)` + Numbered | `two dogs` → `int(2) dog.obj<O,Numbered>` |
| scalar adjective | quality root + **degree** (very = one step more extreme) | `very small` → `size.obj<M,Minimal>` |
| predicate adjective / noun | object-as-verb | `is big` → `size.obj<V,Present,Large>` |
| possessive | non-relation word in Relation role binds to the preceding nominal | `my friend's house` → `dwelling<S> friend<R> self<R>` |
| preposition | `NP<O>` + `prep.rel<R,^k>` linked to that NP | `in the garden` → `garden.obj<O> interior.rel<R,^1>` |
| have / want / know / like | unlinked relation: Subjects × preceding Objects | `I have a dog` → `self<S> dog<O> possession.rel<R>` |
| comparative | the quality's relation sense | `bigger than the cat` → `cat<O> size.rel<R>` |
| this / that + noun | apposition `that.obj<S,^1>` | `that dog` |
| all / many / few / some / no | `amount.obj<M,degree>` (Total / Large / Small / Medium / None) | `all dogs` |
| not | verb degree None (or a following `null.act<M>` if degree is used) | `does not like` |
| tense / aspect | temporal + progression (perfect = Complete) | `has eaten` → `<V,Present,Complete>` |
| yesterday / now / soon | time root as modifier with tense | `day.obj<M,Past>` |
| be at a place | location sense as verb | `I am home` → `dwelling.loc<V,Present>` |
| go to a place | motion verb + InProgress + `toward.rel` | `is going to the house` |
| there is X | `existence.act<V>` | `There are many birds in the sky.` |
| questions | QUERY subtype: Verb (yes/no) · Object (what) · Subject (who) · Location · Time · Reasoning · Explain · Specify (which) | `Where do you live?` |
| imperative | `STATEMENT<Imperative>`, no subject, Timeless | `Open the door.` |
| If A, B. | Condition + Result sentences + `IF` | SPEC §12.8 |
| colour words | `rgb(#RRGGBB)` external | `red` → `rgb(#FF0000)` |
| unknown word / name | `text("…")` + `TO_<role>` cast + warning | `Mary`, `glorp` |
| unparseable sentence | `text("whole sentence") TO_TOPIC` + warning | |
| fiction | a Narrator-level sentence whose Topic is `story.obj`, with the fiction nested inside (scope, no header bits) | not produced by the parser yet |

## 3. Normalization: what does not survive a round trip

English → Cant → English is exact for the sentence types the test suite covers
(`tests/test_english.py`, 68 round trips). Where output differs, it is one of these deliberate
normalizations:

* **Gender.** he/she/him/her → they/them (the doc's neutrality rule: `other.obj` has no gender).
  Kin terms become the neutral root: mother/father → parent, brother/sister → sibling,
  king/queen → leader.
* **Synonyms collapse to one root**: one meaning per root, so large → big, little → small, and
  render the canonical word.
* **Indirect objects** become a "to" phrase: *gives the woman a book* → *gives a book to the woman*.
* **Adverb order**: manner adverbs come before time adverbs, at the end: *Yesterday I ran
  quickly* → *I ran quickly yesterday*.
* **Degree**: *extremely small* and *very small* are both degree Minimal and render as *very small*.
* **Dropped with a warning**: modals other than will (can, should, must …) and "please".
* **Determiners on unknown words** are approximate (`text` externals carry plurality but no
  lexical article).
* **"Who"** in identity questions renders as "what" (`QUERY<Verb>` without a verb asks "what is X").

## 4. Known limits

* Rule-based coverage only: simple and compound clauses are handled; relative clauses
  (*the man who…*), passives (*is broken*), subordinate clauses other than `If`, reported speech
  from English, and most idioms fall back to `text`.
* About 540 English entries over 337 roots. Anything else becomes `text("word")`. Extend
  `cant/english/en_lexicon.csv` (columns: english, pos, root key.cat, flags, irregular forms,
  render yes/no).
* No word-sense disambiguation: the first matching sense wins (e.g. *right* = correct, not the
  direction).
* Numbers: digits, decimals (→ `float64`), and number words up to ninety-nine plus hundred/thousand.
  Words render as English up to 99 and as digits above that (*42* → *forty-two*).
* Only `and` coordination; `or` / `but` are not parsed (Cant has `OR`/`XOR` operations, but the
  parser does not emit them).
* The fiction / narrator-topic convention and `dir()` externals are rendered by cant2en, but the
  English parser does not produce them.
