import random

TWISTS = [
    ("👻 HORROR MODE", "Make the next part of the story frightening.", ["ghost", "dark", "blood", "scream", "haunted", "dead", "fear", "shadow"]),
    ("😂 COMEDY MODE", "Make the next part funny or ridiculous.", ["banana", "clown", "funny", "dance", "silly", "pants", "joke", "chicken"]),
    ("🚀 SCI-FI MODE", "Bring science fiction into the story.", ["alien", "robot", "space", "planet", "laser", "rocket", "future", "time"]),
    ("❤️ ROMANCE MODE", "Add a romantic moment.", ["love", "heart", "kiss", "rose", "date", "romantic", "wedding"]),
    ("🕵️ MYSTERY MODE", "Add a clue or a suspicious detail.", ["secret", "key", "clue", "hidden", "mystery", "message", "shadow"]),
    ("🧟 ZOMBIE ALERT", "Bring a zombie or something undead into the story.", ["zombie", "undead", "grave", "brain", "monster", "dead"]),
]

def choose_twist():
    return random.choice(TWISTS)

def get_twist_by_title(title):
    return next((twist for twist in TWISTS if twist[0] == title), None)
