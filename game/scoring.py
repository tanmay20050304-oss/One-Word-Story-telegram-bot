from database.db import connect
from game.twist_engine import get_twist_by_title


def add_points(game_id, user_id, points):
    with connect() as conn:
        conn.execute(
            "UPDATE game_players SET score=score+? WHERE game_id=? AND user_id=?",
            (points, game_id, user_id),
        )


def complete_objective_if_matched(game_id, user_id, word):
    word = word.lower().strip(".,!?;:")
    with connect() as conn:
        objective = conn.execute(
            "SELECT keywords, completed FROM objectives WHERE game_id=? AND user_id=?",
            (game_id, user_id),
        ).fetchone()
        if not objective or objective["completed"]:
            return False

        keywords = [item.strip().lower() for item in objective["keywords"].split(",")]
        if word in keywords:
            conn.execute(
                "UPDATE objectives SET completed=1 WHERE game_id=? AND user_id=?",
                (game_id, user_id),
            )
            conn.execute(
                "UPDATE game_players SET score=score+50 WHERE game_id=? AND user_id=?",
                (game_id, user_id),
            )
            return True
    return False


def undo_player_word(game_id, user_id):
    with connect() as conn:
        game = conn.execute(
            "SELECT status,current_index FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not game or game["status"] != "active":
            return False, "There is no active game to undo a word in."

        players = conn.execute(
            "SELECT user_id FROM game_players WHERE game_id=? ORDER BY turn_order",
            (game_id,),
        ).fetchall()
        if not players:
            return False, "There are no players in this game."
        if players[game["current_index"] % len(players)]["user_id"] != user_id:
            return False, "You can only undo your own previous word when it is your turn."

        word = conn.execute(
            "SELECT id,position,word FROM story_words "
            "WHERE game_id=? AND user_id=? ORDER BY position DESC LIMIT 1",
            (game_id, user_id),
        ).fetchone()
        if not word:
            return False, "You haven't contributed a word to this game yet."

        conn.execute("DELETE FROM story_words WHERE id=?", (word["id"],))
        conn.execute(
            "UPDATE story_words SET position=position-1 WHERE game_id=? AND position>?",
            (game_id, word["position"]),
        )
        conn.execute(
            "DELETE FROM twist_history WHERE game_id=? "
            "AND activated_after_word IN (?,?)",
            (game_id, word["position"] - 1, word["position"]),
        )
        conn.execute(
            "UPDATE twist_history SET activated_after_word=activated_after_word-1 "
            "WHERE game_id=? AND activated_after_word>?",
            (game_id, word["position"]),
        )
        conn.execute(
            "UPDATE games SET story_word_count=story_word_count-1 WHERE game_id=?",
            (game_id,),
        )

        objectives = conn.execute(
            "SELECT user_id,keywords FROM objectives WHERE game_id=?",
            (game_id,),
        ).fetchall()
        story_words = conn.execute(
            "SELECT user_id,word,position FROM story_words WHERE game_id=? ORDER BY position",
            (game_id,),
        ).fetchall()
        twists = conn.execute(
            "SELECT twist_text,activated_after_word FROM twist_history WHERE game_id=?",
            (game_id,),
        ).fetchall()
        scores = {player["user_id"]: 0 for player in players}

        for objective in objectives:
            keywords = {
                item.strip().lower()
                for item in objective["keywords"].split(",")
                if item.strip()
            }
            completed = any(
                item["user_id"] == objective["user_id"]
                and item["word"].lower().strip(".,!?;:") in keywords
                for item in story_words
            )
            conn.execute(
                "UPDATE objectives SET completed=? WHERE game_id=? AND user_id=?",
                (int(completed), game_id, objective["user_id"]),
            )
            if completed:
                scores[objective["user_id"]] += 50

        for story_word in story_words:
            for active_twist in twists:
                if active_twist["activated_after_word"] != story_word["position"] - 1:
                    continue
                twist = get_twist_by_title(active_twist["twist_text"])
                if twist and story_word["word"].lower() in twist[2]:
                    scores[story_word["user_id"]] += 20

        box_rewards = conn.execute(
            "SELECT user_id,reward FROM mysterybox_claims WHERE game_id=?",
            (game_id,),
        ).fetchall()
        for box_reward in box_rewards:
            scores[box_reward["user_id"]] += box_reward["reward"]

        for player_id, score in scores.items():
            conn.execute(
                "UPDATE game_players SET score=? WHERE game_id=? AND user_id=?",
                (score, game_id, player_id),
            )

    return True, f"Removed your word “{word['word']}”. Your turn is still active."


def add_game_played(game_id):
    with connect() as conn:
        players = conn.execute(
            "SELECT user_id, score FROM game_players WHERE game_id=?",
            (game_id,),
        ).fetchall()
        if not players:
            return
        winner_id = max(players, key=lambda player: player["score"])["user_id"]
        for player in players:
            conn.execute(
                "UPDATE users SET games_played=games_played+1, total_points=total_points+? "
                "WHERE user_id=?",
                (player["score"], player["user_id"]),
            )
        conn.execute(
            "UPDATE users SET games_won=games_won+1 WHERE user_id=?",
            (winner_id,),
        )
        conn.execute("UPDATE games SET status='finished' WHERE game_id=?", (game_id,))
