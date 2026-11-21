# Binary Cant V2.1

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

## What's here

| Path | What |
|---|---|
| `SPEC.md` | The normative bit-level spec (classes, layouts, masks, externals, RPN ops, scoping, file format, semantic locality, worked examples) |
| `DECISIONS.md` | Every conflict or gap found in the source notes, how V2.1 resolves it, and open questions |
| `lexicon.csv` | Seed lexicon: 43 roots, each with up to four category senses, provenance, and proposed-sense flags |
| `cant/` | Reference codec, Python 3 standard library only |
| `tests/` | `unittest` suite (field round-trips, every SPEC example's exact hex, nesting/count rules, externals, errors, locality, CLI) |
| `examples/*.cant` | The SPEC examples as gloss files |
| `tools/locality_report.py` | Bit-distance statistics for related vs unrelated lexicon pairs |
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
python3 -m unittest discover -s tests -t .
python3 tools/locality_report.py
```

The gloss format (`root.cat<flags>`, `type(args)`, `OPNAME`, `QUERY<…>{…}`/`STATEMENT<…>{…}`)
is in SPEC §11. It is a debugging view for humans. The language itself is the binary.

## License

GPL-3.0, per the `BinaryCantV2` repository's LICENSE.
