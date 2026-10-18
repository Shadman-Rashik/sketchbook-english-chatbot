"""Curriculum: word pools for chat teaching + a registry of quiz items per level.

L1 = first words (objects, colors)        -> "Little Sprout"
L2 = numbers, opposites, greetings        -> "Word Explorer"
L3 = tiny sentences (fill the blank)      -> "Sentence Star"
"""
import random

LEVEL_NAMES = {1: "Little Sprout", 2: "Word Explorer", 3: "Sentence Star"}

L1_WORDS = [("🍎", "apple"), ("🐱", "cat"), ("🐶", "dog"), ("⚽", "ball"), ("🌞", "sun"),
            ("🐟", "fish"), ("🚗", "car"), ("🌳", "tree"), ("🐦", "bird"), ("📖", "book")]
COLORS = [("red", "#e5534b"), ("blue", "#4f8fe0"), ("green", "#4caf6a"),
          ("yellow", "#f5c542"), ("pink", "#f29bbb"), ("purple", "#9b7fd4")]
OPPOSITES = [("hot", "cold", "🔥"), ("big", "small", "🐘"), ("up", "down", "⬆️"),
             ("happy", "sad", "😊"), ("day", "night", "☀️"), ("fast", "slow", "🐇")]
COUNT_EMOJI = ["🐟", "🍎", "⭐", "🐥", "🎈"]
NUM_WORDS = ["one", "two", "three", "four", "five"]
GREETINGS = [
    ("morning", "It is morning. What do we say?", "🌅", "Good morning", ["Good night", "Goodbye"]),
    ("night", "It is bedtime. What do we say?", "🌙", "Good night", ["Good morning", "Hello"]),
    ("bye", "A friend is leaving. What do we say?", "👋", "Goodbye", ["Hello", "Thank you"]),
    ("thanks", "Someone gave you a gift. What do we say?", "🎁", "Thank you", ["Sorry", "Hello"]),
]
SENTENCES = [
    ("The cat ___ on the mat.", "sits", ["sit", "sitting"], "🐱"),
    ("I ___ a red ball.", "have", ["has", "having"], "🔴"),
    ("She ___ happy.", "is", ["am", "are"], "😊"),
    ("We ___ friends.", "are", ["is", "am"], "🤝"),
    ("I ___ milk.", "drink", ["drinks", "drinking"], "🥛"),
    ("The sun is ___.", "hot", ["hat", "hit"], "☀️"),
    ("Birds can ___.", "fly", ["flies", "flew"], "🐦"),
    ("I ___ my mom.", "love", ["loves", "loving"], "💛"),
]


def _art(w):
    return "an" if w[0] in "aeiou" else "a"


# (key, emoji, example phrase) used by the chat when it teaches a word
POOLS = {
    1: [(w, e, f"This is {_art(w)} {w}.") for e, w in L1_WORDS],
    2: [("one", "1️⃣", "I have one nose."), ("two", "2️⃣", "I have two eyes."),
        ("three", "3️⃣", "One, two, three!"), ("hello", "👋", "Hello! Nice to meet you."),
        ("big", "🐘", "An elephant is big."), ("small", "🐭", "A mouse is small."),
        ("hot", "🔥", "Fire is hot."), ("cold", "🧊", "Ice is cold.")],
    3: [("happy", "😊", "I am happy today."), ("friend", "🤝", "You are my friend."),
        ("jump", "🤸", "I can jump high."), ("water", "💧", "I drink water."),
        ("mom", "👩", "I love my mom."), ("sleep", "😴", "I sleep at night.")],
}

# ---- quiz registry ---------------------------------------------------------
REG = {}


def _add(id_, level, prompt, visual, answer, distractors):
    REG[id_] = {"id": id_, "level": level, "prompt": prompt, "visual": visual,
                "answer": answer, "distractors": distractors}


for emo, w in L1_WORDS:
    _add(f"w:{w}", 1, "Which word is this?", {"kind": "emoji", "value": emo}, w,
         [x for _, x in L1_WORDS if x != w])
for name, hexv in COLORS:
    _add(f"c:{name}", 1, "What color is this?", {"kind": "color", "value": hexv}, name,
         [n for n, _ in COLORS if n != name])
for i, word in enumerate(NUM_WORDS):
    n = i + 1
    _add(f"n:{n}", 2, "How many do you see?",
         {"kind": "emoji", "value": COUNT_EMOJI[i] * n}, word, [x for x in NUM_WORDS if x != word][:4])
for a, b, emo in OPPOSITES:
    pool = [y for x, y, _ in OPPOSITES if y != b] + [x for x, _, _ in OPPOSITES if x != a and x != b]
    _add(f"o:{a}", 2, f"What is the opposite of “{a}”?", {"kind": "emoji", "value": emo}, b, pool)
for key, prompt, emo, ans, dis in GREETINGS:
    _add(f"g:{key}", 2, prompt, {"kind": "emoji", "value": emo}, ans, dis)
for i, (sent, ans, dis, emo) in enumerate(SENTENCES):
    _add(f"s:{i}", 3, "Pick the missing word.",
         {"kind": "sentence", "value": sent, "emoji": emo}, ans, dis)


def make_quiz(level, prev=""):
    """Pick a random item of this level (20% review of the level below) and shuffle its options."""
    lv = level - 1 if level > 1 and random.random() < 0.2 else level
    cands = [i for i in REG.values() if i["level"] == lv and i["id"] != prev]
    item = random.choice(cands)
    opts = [item["answer"]] + random.sample(item["distractors"], 2)
    random.shuffle(opts)
    return {"id": item["id"], "level": item["level"], "prompt": item["prompt"],
            "visual": item["visual"], "options": opts}
