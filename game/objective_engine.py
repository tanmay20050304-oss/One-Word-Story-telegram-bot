import random

OBJECTIVES = [
    ("animal", "Introduce an animal into the story.", ["dog", "cat", "horse", "bird", "wolf", "lion", "rabbit", "snake", "dragon", "elephant"]),
    ("magic", "Introduce something magical.", ["magic", "wizard", "witch", "spell", "wand", "potion", "fairy", "dragon", "enchanted"]),
    ("villain", "Introduce a villain or dangerous character.", ["villain", "enemy", "monster", "killer", "thief", "witch", "evil", "demon", "bandit"]),
    ("romance", "Add a romantic element.", ["love", "kiss", "heart", "romance", "lover", "wedding", "date", "rose"]),
    ("food", "Make food important to the story.", ["pizza", "cake", "food", "burger", "rice", "chocolate", "apple", "feast"]),
    ("travel", "Introduce a journey or a place.", ["city", "forest", "island", "mountain", "village", "journey", "travel", "ship"]),
    ("technology", "Introduce technology or science fiction.", ["robot", "computer", "laser", "spaceship", "alien", "machine", "phone", "rocket"]),
    ("mystery", "Introduce a clue or something mysterious.", ["secret", "mystery", "key", "message", "shadow", "hidden", "strange", "mysterious"]),
    ("royalty", "Introduce royalty.", ["king", "queen", "prince", "princess", "kingdom", "castle", "throne"]),
    ("weather", "Make the weather affect the story.", ["rain", "storm", "snow", "sun", "thunder", "wind", "lightning", "fog"]),
]

def assign_objectives(player_ids):
    choices = OBJECTIVES[:]
    random.shuffle(choices)
    # Avoid duplicates until all available objectives have been assigned.
    return {uid: choices[i % len(choices)] for i, uid in enumerate(player_ids)}
