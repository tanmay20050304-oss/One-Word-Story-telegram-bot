import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "one_word_story.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            private_started INTEGER DEFAULT 0,
            total_points INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            games_won INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            host_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting',
            current_index INTEGER DEFAULT 0,
            story_word_count INTEGER DEFAULT 0,
            target_players INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        DROP INDEX IF EXISTS one_active_game_per_chat;
        CREATE UNIQUE INDEX one_active_game_per_chat
        ON games(chat_id) WHERE status IN ('waiting', 'active', 'paused');

        CREATE TABLE IF NOT EXISTS game_players (
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            display_name TEXT,
            turn_order INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            missed_turns INTEGER DEFAULT 0,
            PRIMARY KEY (game_id, user_id),
            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS story_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS objectives (
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            objective_key TEXT NOT NULL,
            objective_text TEXT NOT NULL,
            keywords TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            PRIMARY KEY (game_id, user_id),
            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS twist_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            twist_text TEXT NOT NULL,
            activated_after_word INTEGER NOT NULL,
            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS mysterybox_claims (
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reward INTEGER NOT NULL,
            PRIMARY KEY (game_id, user_id),
            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS game_votes (
            game_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (game_id, user_id),
            FOREIGN KEY (game_id) REFERENCES games(game_id) ON DELETE CASCADE
        );
        """)
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(games)")
        }
        if "target_players" not in columns:
            conn.execute("ALTER TABLE games ADD COLUMN target_players INTEGER")
