# Binary Cant v2.2

A **machine-first language built on the 64-bit word**, loosely inspired by the Binary Cant of
Warhammer 40k (no Games Workshop material is used). Every word is 64 bits. The **high 32 bits**
carry grammar and the relations between words. The **low 32 bits** carry meaning: a 30-bit
concept root and a 2-bit category (object, relation, action, location). Sentences carry their
own word counts and are scopes. A conversation is a self-describing file.

```
"Nothing is happening."                      "His shirt is red."
C000000100000001  STATEMENT Assertion 1w     C000000400000005  STATEMENT Assertion 4w span 5
1C00000000000002  null.act<V,Present>        040140000033000C  other.obj<S,Present,Specific,Singular>
                                             0C01400055000000  cover.obj<O,Present,Specific,Singular>
                                             2C000000003C0001  possession.rel<R,Present>
                                             5000000000FF0000  rgb(#FF0000)
                                             7E01030004002018  TO_VERB<Present,^3>
```

## Quick start

```sh
python3 -m cant serve                 # web UI on http://127.0.0.1:8000  (--port 8765 to change)
python3 -m cant translate en2cant "Did you see my two red dogs in the garden yesterday?"
python3 -m cant translate cant2en "4021000000000003 A000000200000002 0001400000330004 1C0000000F660002"
#   -> Where do you live?
```

The UI has four tabs:
* **Translate**: English → gloss, hex, a per-word field table and a colour-coded 64-bit view,
  plus Cant → English.
* **Encode / Decode**: gloss ↔ hex with live validation errors, and `.cant` download/upload.
* **Lexicon**: search and filter by domain or category.
* **Distance**: semantic Hamming distance, showing the bits that differ.

It is standard-library only: `http.server` and one inline HTML page, no CDN. The same
features are available as a JSON API: `POST /api/en2cant {"text"}`,
`/api/cant2en {"text"|"gloss"|"hex"|"base64"}`, `/api/encode {"gloss","bare"}`,
`/api/decode {"hex"|"base64"}`, `GET /api/lexicon?q=&domain=&category=`,
`/api/distance {"a","b"}`, `GET /api/meta`.

English translation is rule-based and honest about its limits. Unknown words travel as
`text("…")` externals with a warning, never as an error. See **[TRANSLATION.md](TRANSLATION.md)**.

## What's here

| Path | What |
|---|---|
| `SPEC.md` | The normative bit-level spec (classes, layouts, masks, externals, RPN ops, scoping, file format, semantic locality, worked examples) and the v2.2 conventions (§14) |
| `DECISIONS.md` | Every conflict or gap found in the source notes, how V2.1/v2.2 resolve it, and open questions |
| `lexicon.csv` | Language-neutral lexicon: 337 roots (43 seed + 294 `proposed-v2.2`), each with up to four category senses, provenance, and proposed-sense flags |
| `TRANSLATION.md` | English ↔ Cant translator: approach, conventions, normalization, limits |
| `cant/` | Reference codec, Python 3 standard library only |
| `cant/english/` | Rule-based en2cant / cant2en and `en_lexicon.csv` (English forms → roots) |
| `cant/web/` | `cant serve`: http.server JSON API + single-page UI |
| `tests/` | `unittest` suite (field round-trips, every SPEC example's exact hex, nesting/count rules, externals, errors, locality, CLI, English round trips, web API) |
| `examples/*.cant` | The SPEC examples as gloss files |
| `tools/locality_report.py` | Bit-distance statistics for related vs unrelated lexicon pairs |
| `tools/build_lexicon_v22.py` | Generator for the v2.2 lexicon rows and the English mapping |
| `source/` | The author's original notes (doc export and spreadsheet) |
| `ROADMAP.md` | Next steps |

## Quick tour

```sh
python3 -m cant encode examples/dialogue.cant -o dialogue.bin   # gloss -> big-endian binary
python3 -m cant decode dialogue.bin                              # binary -> annotated gloss
python3 -m cant dump dialogue.bin                                # hex listing + per-field breakdown
python3 -m cant decode --hex "C000000100000001 1C00000000000002"
python3 -m cant encode --bare -e 'STATEMENT<Assertion>{ int(3) sophont.obj<S,Present,Numbered> mover.act<V,Present,InProgress> }'
python3 -m cant lexicon                # all roots;  python3 -m cant lexicon manipulator  for one
python3 -m cant distance mover.act manipulator.obj   # Hamming + tree distance between meanings
python3 -m cant types                  # external type registry and opcodes
python3 -m cant translate en2cant -o msg.cant "The cat sleeps."   # English -> gloss + hex (+ binary)
python3 -m cant translate cant2en msg.cant                         # any binary/hex/gloss -> English
python3 -m unittest discover -s tests -t .
python3 tools/locality_report.py
```

The gloss format (`root.cat<flags>`, `type(args)`, `OPNAME`, `QUERY<…>{…}`/`STATEMENT<…>{…}`)
is in SPEC §11. It is a debugging view for humans. The language itself is the binary.

## License

GPL-3.0, per the `BinaryCantV2` repository's LICENSE.
