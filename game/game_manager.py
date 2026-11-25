import sqlite3

from database.db import connect
from game.objective_engine import assign_objectives
from config import MAX_PLAYERS, MIN_PLAYERS

def register_user(user, private_started=None):
    with connect() as conn:
        existing = conn.execute("SELECT private_started FROM users WHERE user_id=?", (user.id,)).fetchone()
        started = private_started if private_started is not None else (existing["private_started"] if existing else 0)
        conn.execute("""
            INSERT INTO users(user_id, username, first_name, private_started)
            VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
              username=excluded.username,
              first_name=excluded.first_name,
              private_started=MAX(users.private_started, excluded.private_started)
        """, (user.id, user.username or "", user.first_name or "Player", started))

def has_private_started(user_id):
    with connect() as conn:
        row = conn.execute("SELECT private_started FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row and row["private_started"])

def create_room(chat_id, host):
    register_user(host)
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO games(chat_id,host_id,status) VALUES(?,?,'waiting')",
            (chat_id, host.id)
        )
        game_id = cur.lastrowid
        conn.execute(
            "INSERT INTO game_players(game_id,user_id,display_name,turn_order) VALUES(?,?,?,0)",
            (game_id, host.id, host.first_name or "Host")
        )
    return game_id

def get_active_game(chat_id):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM games WHERE chat_id=? AND status IN ('waiting','active','paused') ORDER BY game_id DESC LIMIT 1",
            (chat_id,)
        ).fetchone()

def get_game(game_id):
    with connect() as conn:
        return conn.execute("SELECT * FROM games WHERE game_id=?", (game_id,)).fetchone()

def get_players(game_id):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM game_players WHERE game_id=? ORDER BY turn_order",
            (game_id,)
        ).fetchall()

def join_room(game_id, user):
    register_user(user)
    with connect() as conn:
        game = conn.execute("SELECT status FROM games WHERE game_id=?", (game_id,)).fetchone()
        if not game or game["status"] != "waiting":
            return False, "This room is no longer accepting players."
        existing = conn.execute(
            "SELECT 1 FROM game_players WHERE game_id=? AND user_id=?",
            (game_id, user.id)
        ).fetchone()
        if existing:
            return False, "You have already joined this room."
        count = conn.execute("SELECT COUNT(*) AS n FROM game_players WHERE game_id=?", (game_id,)).fetchone()["n"]
        game = conn.execute(
            "SELECT target_players FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        limit = game["target_players"] or MAX_PLAYERS
        if count >= limit:
            return False, f"This room is full (maximum {limit} players)."
        conn.execute(
            "INSERT INTO game_players(game_id,user_id,display_name,turn_order) VALUES(?,?,?,?)",
            (game_id, user.id, user.first_name or "Player", count)
        )
    return True, "You joined the room!"

def cancel_waiting_room(game_id, host_id):
    with connect() as conn:
        game = conn.execute(
            "SELECT host_id,status FROM games WHERE game_id=?",
            (game_id,)
        ).fetchone()
        if not game:
            return False, "Game not found."
        if game["host_id"] != host_id:
            return False, "Only the host can cancel this room."
        if game["status"] != "waiting":
            return False, "Only a waiting room can be cancelled."
        conn.execute("DELETE FROM games WHERE game_id=?", (game_id,))
    return True, "Waiting room cancelled."

def start_room(game_id, host_id):
    with connect() as conn:
        game = conn.execute("SELECT * FROM games WHERE game_id=?", (game_id,)).fetchone()
        if not game:
            return False, "Game not found."
        if game["host_id"] != host_id:
            return False, "Only the host can start the game."
        if game["status"] != "waiting":
            return False, "This game has already started or ended."
        players = conn.execute(
            "SELECT user_id, turn_order FROM game_players WHERE game_id=? ORDER BY turn_order",
            (game_id,)
        ).fetchall()
        if len(players) < MIN_PLAYERS:
            return False, f"At least {MIN_PLAYERS} players are required."
        if len(players) > MAX_PLAYERS:
            return False, f"A game can have at most {MAX_PLAYERS} players."
        if game["target_players"] and len(players) != game["target_players"]:
            return False, (
                f"This room is set for exactly {game['target_players']} players; "
                f"{len(players)} have joined."
            )
        not_started = [p["user_id"] for p in players if not has_private_started(p["user_id"])]
        if not_started:
            return False, "Every player must open the bot privately and press /start before the game begins. Missing private setup for: " + ", ".join(map(str, not_started))
        objectives = assign_objectives([p["user_id"] for p in players])
        for uid, (key, description, keywords) in objectives.items():
            conn.execute(
                "INSERT OR REPLACE INTO objectives(game_id,user_id,objective_key,objective_text,keywords,completed) VALUES(?,?,?,?,?,0)",
                (game_id, uid, key, description, ",".join(keywords))
            )
        conn.execute("UPDATE games SET status='active',current_index=0,story_word_count=0 WHERE game_id=?", (game_id,))
    return True, "started"

def current_player(game_id):
    players = get_players(game_id)
    game = get_game(game_id)
    if not players or not game:
        return None
    index = game["current_index"] % len(players)
    return players[index]

def next_turn(game_id):
    with connect() as conn:
        game = conn.execute("SELECT current_index FROM games WHERE game_id=?", (game_id,)).fetchone()
        count = conn.execute("SELECT COUNT(*) AS n FROM game_players WHERE game_id=?", (game_id,)).fetchone()["n"]
        if game and count:
            conn.execute(
                "UPDATE games SET current_index=? WHERE game_id=?",
                ((game["current_index"] + 1) % count, game_id)
            )
    return current_player(game_id)


def set_player_target(game_id, host_id, target):
    with connect() as conn:
        game = conn.execute(
            "SELECT host_id,status FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not game or game["status"] != "waiting":
            return False, "Player target can only be changed before the game starts."
        if game["host_id"] != host_id:
            return False, "Only the host can change the player target."
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM game_players WHERE game_id=?",
            (game_id,),
        ).fetchone()["n"]
        if target < count:
            return False, f"There are already {count} players in this room."
        conn.execute(
            "UPDATE games SET target_players=? WHERE game_id=?",
            (target, game_id),
        )
    return True, f"Room target set to exactly {target} players."


def add_registered_player(game_id, host_id, target_user_id):
    with connect() as conn:
        game = conn.execute(
            "SELECT host_id,status,target_players FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not game or game["status"] != "waiting":
            return False, "Players can only be added before the game starts."
        if game["host_id"] != host_id:
            return False, "Only the host can add players."
        user = conn.execute(
            "SELECT first_name FROM users WHERE user_id=?",
            (target_user_id,),
        ).fetchone()
        if not user:
            return False, "That player has not started the bot yet. Ask them to send /start."
        existing = conn.execute(
            "SELECT 1 FROM game_players WHERE game_id=? AND user_id=?",
            (game_id, target_user_id),
        ).fetchone()
        if existing:
            return False, "That player is already in this room."
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM game_players WHERE game_id=?",
            (game_id,),
        ).fetchone()["n"]
        limit = game["target_players"] or MAX_PLAYERS
        if count >= limit:
            return False, f"This room is full (maximum {limit} players)."
        conn.execute(
            "INSERT INTO game_players(game_id,user_id,display_name,turn_order) "
            "VALUES(?,?,?,?)",
            (game_id, target_user_id, user["first_name"], count),
        )
    return True, f"Added {user['first_name']} to the room."


def remove_waiting_player(game_id, host_id, target_user_id):
    with connect() as conn:
        game = conn.execute(
            "SELECT host_id,status FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not game or game["status"] != "waiting":
            return False, "Players can only be removed before the game starts."
        if game["host_id"] != host_id:
            return False, "Only the host can remove players."
        if target_user_id == host_id:
            return False, "The host cannot be removed from their own room."
        player = conn.execute(
            "SELECT turn_order FROM game_players WHERE game_id=? AND user_id=?",
            (game_id, target_user_id),
        ).fetchone()
        if not player:
            return False, "That user is not in this room."
        conn.execute(
            "DELETE FROM game_players WHERE game_id=? AND user_id=?",
            (game_id, target_user_id),
        )
        conn.execute(
            "UPDATE game_players SET turn_order=turn_order-1 "
            "WHERE game_id=? AND turn_order>?",
            (game_id, player["turn_order"]),
        )
    return True, "Player removed from the waiting room."


def set_game_status(game_id, host_id, expected_status, new_status):
    with connect() as conn:
        game = conn.execute(
            "SELECT host_id,status FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not game or game["status"] != expected_status:
            return False, f"The game is not {expected_status}."
        if game["host_id"] != host_id:
            return False, "Only the host can change the game state."
        conn.execute(
            "UPDATE games SET status=? WHERE game_id=?",
            (new_status, game_id),
        )
        conn.execute("DELETE FROM game_votes WHERE game_id=?", (game_id,))
    return True, f"Game {new_status}."


def create_rematch(game_id, host_id):
    with connect() as conn:
        old_game = conn.execute(
            "SELECT * FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not old_game or old_game["status"] != "finished":
            return False, "A rematch is only available after the previous game ends."
        if old_game["host_id"] != host_id:
            return False, "Only the previous host can start a rematch."
        players = conn.execute(
            "SELECT user_id,display_name,turn_order FROM game_players "
            "WHERE game_id=? ORDER BY turn_order",
            (game_id,),
        ).fetchall()
        cur = conn.execute(
            "INSERT INTO games(chat_id,host_id,status,target_players) "
            "VALUES(?,?,'waiting',?)",
            (
                old_game["chat_id"],
                host_id,
                old_game["target_players"],
            ),
        )
        new_game_id = cur.lastrowid
        for player in players:
            conn.execute(
                "INSERT INTO game_players(game_id,user_id,display_name,turn_order) "
                "VALUES(?,?,?,?)",
                (
                    new_game_id,
                    player["user_id"],
                    player["display_name"],
                    player["turn_order"],
                ),
            )
    return True, new_game_id


def vote_to_skip(game_id, user_id):
    with connect() as conn:
        game = conn.execute(
            "SELECT status,current_index FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not game or game["status"] != "active":
            return False, "Voting is only available during an active game."
        players = conn.execute(
            "SELECT user_id FROM game_players WHERE game_id=? ORDER BY turn_order",
            (game_id,),
        ).fetchall()
        if not any(player["user_id"] == user_id for player in players):
            return False, "Only players in this game can vote."
        try:
            conn.execute(
                "INSERT INTO game_votes(game_id,user_id) VALUES(?,?)",
                (game_id, user_id),
            )
        except sqlite3.IntegrityError:
            return False, "You have already voted to skip this turn."
        votes = conn.execute(
            "SELECT COUNT(*) AS n FROM game_votes WHERE game_id=?",
            (game_id,),
        ).fetchone()["n"]
        needed = len(players) // 2 + 1
        if votes < needed:
            return True, f"Vote recorded ({votes}/{needed} votes needed to skip)."

        current = players[game["current_index"] % len(players)]
        conn.execute(
            "UPDATE game_players SET missed_turns=missed_turns+1 "
            "WHERE game_id=? AND user_id=?",
            (game_id, current["user_id"]),
        )
        conn.execute("DELETE FROM game_votes WHERE game_id=?", (game_id,))
        conn.execute(
            "UPDATE games SET current_index=? WHERE game_id=?",
            ((game["current_index"] + 1) % len(players), game_id),
        )
        next_player = players[(game["current_index"] + 1) % len(players)]
    return True, f"Majority reached. Turn skipped; next player: {next_player['user_id']}."


def claim_mystery_box(game_id, user_id, reward):
    with connect() as conn:
        game = conn.execute(
            "SELECT status FROM games WHERE game_id=?",
            (game_id,),
        ).fetchone()
        if not game or game["status"] != "active":
            return False, "Mystery boxes are available during an active game."
        is_player = conn.execute(
            "SELECT 1 FROM game_players WHERE game_id=? AND user_id=?",
            (game_id, user_id),
        ).fetchone()
        if not is_player:
            return False, "Only players in this game can open a mystery box."
        try:
            conn.execute(
                "INSERT INTO mysterybox_claims(game_id,user_id,reward) VALUES(?,?,?)",
                (game_id, user_id, reward),
            )
        except sqlite3.IntegrityError:
            return False, "You already opened your mystery box for this game."
        conn.execute(
            "UPDATE game_players SET score=score+? WHERE game_id=? AND user_id=?",
            (reward, game_id, user_id),
        )
    return True, f"You found a +{reward} point bonus!"

def activate_twist(game_id, text, position):
    with connect() as conn:
        conn.execute(
            "INSERT INTO twist_history(game_id,twist_text,activated_after_word) VALUES(?,?,?)",
            (game_id, text, position)
        )

def get_twist_after_word(game_id, position):
    with connect() as conn:
        row = conn.execute(
            "SELECT twist_text FROM twist_history "
            "WHERE game_id=? AND activated_after_word=? ORDER BY id DESC LIMIT 1",
            (game_id, position)
        ).fetchone()
    return row["twist_text"] if row else None

def finish_game(game_id):
    with connect() as conn:
        game = conn.execute(
            "SELECT status FROM games WHERE game_id=?",
            (game_id,)
        ).fetchone()
        if not game:
            return []

        if game["status"] != "finished":
            players = conn.execute(
                "SELECT user_id,score FROM game_players WHERE game_id=? ORDER BY score DESC,turn_order",
                (game_id,)
            ).fetchall()
            if players:
                for player in players:
                    conn.execute(
                        "UPDATE users SET games_played=games_played+1,total_points=total_points+? "
                        "WHERE user_id=?",
                        (player["score"], player["user_id"])
                    )
                conn.execute(
                    "UPDATE users SET games_won=games_won+1 WHERE user_id=?",
                    (players[0]["user_id"],)
                )
            conn.execute("UPDATE games SET status='finished' WHERE game_id=?", (game_id,))

        return conn.execute(
            "SELECT gp.user_id,gp.display_name,gp.score,o.objective_text,o.completed "
            "FROM game_players gp LEFT JOIN objectives o ON gp.game_id=o.game_id AND gp.user_id=o.user_id "
            "WHERE gp.game_id=? ORDER BY gp.score DESC,gp.turn_order",
            (game_id,)
        ).fetchall()

def get_objective(game_id, user_id):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM objectives WHERE game_id=? AND user_id=?",
            (game_id, user_id)
        ).fetchone()

def get_group_for_game(game_id):
    game = get_game(game_id)
    return game["chat_id"] if game else None
