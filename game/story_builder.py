from database.db import connect

def get_story(game_id):
    with connect() as conn:
        rows = conn.execute(
            "SELECT word FROM story_words WHERE game_id=? ORDER BY position",
            (game_id,)
        ).fetchall()
    return " ".join(row["word"] for row in rows)

def add_word(game_id, user_id, word):
    with connect() as conn:
        game = conn.execute(
            "SELECT story_word_count FROM games WHERE game_id=? AND status='active'",
            (game_id,)
        ).fetchone()
        if not game:
            return None
        position = game["story_word_count"] + 1
        conn.execute(
            "INSERT INTO story_words(game_id,user_id,word,position) VALUES(?,?,?,?)",
            (game_id, user_id, word, position)
        )
        conn.execute(
            "UPDATE games SET story_word_count=? WHERE game_id=?",
            (position, game_id)
        )
    return position
