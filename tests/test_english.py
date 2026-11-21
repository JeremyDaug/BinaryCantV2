"""English <-> Cant translation tests (v2.2).

Round-trip cases are (input English, expected English after en2cant -> encode -> decode -> cant2en).
Expected output differs from input only by the documented normalizations (TRANSLATION.md section 3):
  - gendered pronouns -> "they"; kin terms -> the neutral root word (mother -> parent)
  - indirect objects -> "to" phrases (gives the woman a book -> gives a book to the woman)
  - time adverbs move to the end; "please" and unsupported modals are dropped (with warnings)
  - "extremely small" collapses to "very small" (both are degree Minimal)
"""
import unittest

from cant.codec import decode, encode
from cant.english import EnglishLexicon, cant2en, en2cant
from cant.gloss import parse as parse_gloss
from tests.test_spec_examples import spec_examples

EN = EnglishLexicon()

ROUND_TRIPS = [
    ("The cat sleeps.", None),
    ("The cats sleep.", None),
    ("A bird is flying.", None),
    ("The birds were singing.", None),
    ("I saw a big dog yesterday.", None),
    ("She will help you tomorrow.", "They will help you tomorrow."),
    ("He has eaten the bread.", "They have eaten the bread."),
    ("They had left the city.", None),
    ("The woman is not happy.", None),
    ("The child is very small.", None),
    ("The child is extremely small.", "The child is very small."),
    ("The water is cold.", None),
    ("My mother is a teacher.", "My parent is a teacher."),
    ("Your house is big.", None),
    ("The man gives the woman a book.", "The man gives a book to the woman."),
    ("We are going to the school.", None),
    ("The teacher reads a story to the children.", None),
    ("The robot is in the room.", None),
    ("The book is on the table.", None),
    ("The cat is under the bed.", None),
    ("The dog runs to the river.", None),
    ("Two dogs and a cat are in the garden.", None),
    ("I have five friends.", None),
    ("Ten people are working in the field.", None),
    ("Do you know the answer?", None),
    ("Does the cat like fish?", None),
    ("Are the children sleeping?", None),
    ("Have you seen my dog?", None),
    ("When did you come home?", None),
    ("Why is the child crying?", None),
    ("How do you make bread?", None),
    ("Which dog is bigger?", None),
    ("What do you want?", None),
    ("Who wants the food?", None),
    ("Where do you live?", None),
    ("Open the door.", None),
    ("Do not touch the fire.", None),
    ("Please give me water.", "Give water to me."),
    ("The sky is blue.", None),
    ("The red car is fast.", None),
    ("The old man walked slowly to the shop.", None),
    ("The dog does not like the cat.", None),
    ("I will not go.", None),
    ("The computer knows my name.", None),
    ("The phone is on the bed!", None),
    ("Presumably, the river is dangerous.", None),
    ("In my opinion, the music is beautiful.", None),
    ("Reportedly, the king is dead.", "Reportedly, the leader is dead."),
    ("The dog is happier than the cat.", None),
    ("The dog is not bigger than the horse.", None),
    ("There are many birds in the sky.", None),
    ("There is a dog in the house.", None),
    ("All dogs eat meat.", None),
    ("That is my house.", None),
    ("This apple is good.", None),
    ("I am home.", None),
    ("The child has a red ball.", None),
    ("Yesterday I ran quickly.", "I ran quickly yesterday."),
    ("Will you come to the city tomorrow?", None),
    ("Nothing is happening.", None),
    ("Did you see my two dogs yesterday?", None),
    ("These three cats are small.", None),
    ("All my friends are here.", None),
    ("Which two dogs are big?", None),
    ("My friend's house is big.", None),
    ("My old friend's big house is red.", None),
    ("The teacher's dog sleeps.", None),
    ("Your two brothers' cats are here.", "Your two siblings' cats are here."),
]


def round_trip(text):
    conv, warnings = en2cant(text, EN)
    words = encode(conv, file=False)
    return cant2en(decode(words, file=False), EN), warnings, words


class RoundTrip(unittest.TestCase):
    def test_count(self):
        self.assertGreaterEqual(len(ROUND_TRIPS), 40)

    def test_round_trips(self):
        for src, expected in ROUND_TRIPS:
            with self.subTest(src=src):
                out, warnings, _ = round_trip(src)
                self.assertEqual(out, expected or src)
                if expected is None:
                    self.assertEqual(warnings, [], src)

    def test_round_trip_via_gloss(self):
        # en2cant -> gloss text -> parse -> render must match the binary path
        from cant.gloss import format_conversation as fmt
        for src, _ in ROUND_TRIPS[:15]:
            conv, _ = en2cant(src, EN)
            self.assertEqual(cant2en(parse_gloss(fmt(conv)), EN), cant2en(conv, EN))


class Robustness(unittest.TestCase):
    def test_unknown_word_warns_not_fails(self):
        out, warnings, _ = round_trip("The glorp eats bread.")
        self.assertTrue(any("glorp" in w for w in warnings))
        self.assertIn("glorp", out)
        self.assertIn("bread", out)

    def test_unparseable_kept_as_text(self):
        out, warnings, words = round_trip("Colorless green ideas sleep furiously , and , and.")
        self.assertTrue(warnings)
        self.assertTrue(words)

    def test_names_and_possessive(self):
        out, warnings, _ = round_trip("Mary's dog is big.")
        self.assertEqual(out, "Mary's dog is big.")
        self.assertTrue(any("Mary" in w for w in warnings))

    def test_numbers(self):
        self.assertEqual(round_trip("I have 42 books.")[0], "I have 42 books.")
        self.assertEqual(round_trip("Three people are moving.")[0], "Three people are moving.")

    def test_colour_becomes_rgb_external(self):
        from cant.english import en2cant as e2c
        from cant.gloss import format_conversation as fmt
        conv, _ = e2c("The ball is red.", EN)
        self.assertIn("rgb(#FF0000)", fmt(conv))

    def test_multiple_sentences(self):
        out, _, _ = round_trip("The cat sleeps. The dog runs.")
        self.assertEqual(out, "The cat sleeps. The dog runs.")

    def test_empty(self):
        conv, warnings = en2cant("", EN)
        self.assertEqual(cant2en(conv, EN), "")


SPEC_RENDERINGS = [
    "What?",
    "What is that?",
    "Nothing happens.",
    "They have the shirt, and the shirt is red.",
    "Entity-1 is the partner of entity-2, and entity-1 is the family of entity-2 and entity-3.",
    "Three people are moving.",
    "Therefore, two plus three is five.",
    "I say that you are home.",
    "If you are home, then I will be home.",
    "Narrator: Concerning that.\nSpeaker 1: What is that?\nSpeaker 2: That is a tool.",
]


class SpecExamples(unittest.TestCase):
    def test_every_spec_example_renders(self):
        examples = list(spec_examples())
        self.assertEqual(len(examples), len(SPEC_RENDERINGS))
        for (gloss, words), expected in zip(examples, SPEC_RENDERINGS):
            file_mode = gloss.lstrip().startswith("; file")
            with self.subTest(gloss=gloss[:40]):
                self.assertEqual(cant2en(decode(words, file=file_mode), EN), expected)


if __name__ == "__main__":
    unittest.main()
