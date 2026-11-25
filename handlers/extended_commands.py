import random

from telegram import Update
from telegram.ext import ContextTypes

from config import MAX_PLAYERS
from database.db import connect
from game.game_manager import (
    add_registered_player,
    claim_mystery_box,
    create_rematch,
    get_active_game,
    get_players,
    current_player,
    activate_twist,
    get_twist_after_word,
    remove_waiting_player,
    set_game_status,
    set_player_target,
    vote_to_skip,
)
from game.story_builder import get_story
from game.twist_engine import choose_twist


async def _require_group(update: Update) -> bool:
    if update.effective_chat.type == "private":
        await update.message.reply_text("Use this command in the game group.")
        return False
    return True


async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game or game["status"] == "waiting":
        await update.message.reply_text("There is no story in progress in this group.")
        return
    text = get_story(game["game_id"]) or "(The story has not started yet.)"
    await update.message.reply_text(
        f"📖 STORY ({game['story_word_count']} words)\n\n{text}"
    )


def _resolve_player_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        return update.message.reply_to_message.from_user.id
    if len(context.args) != 1:
        return None
    value = context.args[0]
    with connect() as conn:
        if value.startswith("@"):
            row = conn.execute(
                "SELECT user_id FROM users WHERE lower(username)=lower(?)",
                (value[1:],),
            ).fetchone()
        elif value.isdecimal():
            row = conn.execute(
                "SELECT user_id FROM users WHERE user_id=?",
                (int(value),),
            ).fetchone()
        else:
            row = None
    return row["user_id"] if row else None


async def addplayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("Create a waiting room before adding players.")
        return
    user_id = _resolve_player_id(update, context)
    if user_id is None:
        await update.message.reply_text(
            "Reply to a player's message, or use /addplayer <registered user ID or @username>."
        )
        return
    ok, message = add_registered_player(
        game["game_id"], update.effective_user.id, user_id
    )
    await update.message.reply_text(message)
    if ok:
        players = get_players(game["game_id"])
        target = game["target_players"] or MAX_PLAYERS
        await update.message.reply_text(
            f"Players: {len(players)}/{target}\n"
            + "\n".join(f"{i + 1}. {player['display_name']}" for i, player in enumerate(players))
        )


async def removeplayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("There is no waiting room in this group.")
        return
    user_id = _resolve_player_id(update, context)
    if user_id is None:
        await update.message.reply_text(
            "Reply to a player's message, or use /removeplayer <registered user ID or @username>."
        )
        return
    _, message = remove_waiting_player(
        game["game_id"], update.effective_user.id, user_id
    )
    await update.message.reply_text(message)


async def setplayers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("Create a waiting room before setting its player target.")
        return
    if len(context.args) != 1 or not context.args[0].isdecimal():
        await update.message.reply_text(f"Usage: /setplayers <2-{MAX_PLAYERS}>")
        return
    target = int(context.args[0])
    if not 2 <= target <= MAX_PLAYERS:
        await update.message.reply_text(f"Choose a target between 2 and {MAX_PLAYERS}.")
        return
    _, message = set_player_target(game["game_id"], update.effective_user.id, target)
    await update.message.reply_text(message)


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("There is no game room in this group.")
        return
    if game["host_id"] != update.effective_user.id:
        await update.message.reply_text("Only the host can make a game announcement.")
        return
    message = " ".join(context.args).strip()
    if not message:
        await update.message.reply_text("Usage: /announce <message>")
        return
    if len(message) > 4000:
        await update.message.reply_text("Announcements must be 4,000 characters or fewer.")
        return
    await update.message.reply_text(f"📣 HOST ANNOUNCEMENT\n\n{message}")


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("There is no game to pause.")
        return
    _, message = set_game_status(
        game["game_id"], update.effective_user.id, "active", "paused"
    )
    await update.message.reply_text(message)


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("There is no paused game to resume.")
        return
    _, message = set_game_status(
        game["game_id"], update.effective_user.id, "paused", "active"
    )
    await update.message.reply_text(message)


async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("There is no active game to vote in.")
        return
    ok, message = vote_to_skip(
        game["game_id"], update.effective_user.id
    )
    if ok and message.startswith("Majority reached."):
        next_player = current_player(game["game_id"])
        message = (
            "Majority reached. The current turn was skipped."
            + (f" Next player: {next_player['display_name']}." if next_player else "")
        )
    await update.message.reply_text(message)


async def twist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game or game["status"] != "active":
        await update.message.reply_text("A host can trigger a twist during an active game.")
        return
    if game["host_id"] != update.effective_user.id:
        await update.message.reply_text("Only the host can trigger an extra twist.")
        return
    position = game["story_word_count"]
    if get_twist_after_word(game["game_id"], position):
        await update.message.reply_text("A twist challenge is already waiting for the next word.")
        return
    selected_twist = choose_twist()
    activate_twist(game["game_id"], selected_twist[0], position)
    await update.message.reply_text(
        f"🚨 EXTRA TWIST: {selected_twist[0]}\n\n{selected_twist[1]}\n"
        "The next player's matching word earns +20 points."
    )


async def mysterybox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("Mystery boxes are available during an active game.")
        return
    reward = random.choice((5, 10, 15, 20))
    ok, message = claim_mystery_box(
        game["game_id"], update.effective_user.id, reward
    )
    await update.message.reply_text(f"🎁 {message}" if ok else message)


async def rematch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    active_game = get_active_game(update.effective_chat.id)
    if active_game:
        await update.message.reply_text(
            "Finish or cancel the current room before creating a rematch."
        )
        return
    with connect() as conn:
        previous_game = conn.execute(
            "SELECT game_id FROM games WHERE chat_id=? AND status='finished' "
            "ORDER BY game_id DESC LIMIT 1",
            (update.effective_chat.id,),
        ).fetchone()
    if not previous_game:
        await update.message.reply_text("There is no finished game to rematch.")
        return
    ok, result = create_rematch(
        previous_game["game_id"], update.effective_user.id
    )
    if not ok:
        await update.message.reply_text(result)
        return
    await update.message.reply_text(
        f"🔁 Rematch room #{result} created with the previous players. "
        "The host can start it with /startgame."
    )


async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with connect() as conn:
        user = conn.execute(
            "SELECT games_played,games_won,total_points FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        word_count = conn.execute(
            "SELECT COUNT(*) AS n FROM story_words WHERE user_id=?",
            (user_id,),
        ).fetchone()["n"]
    if not user:
        await update.message.reply_text("Use /start to create your profile first.")
        return
    earned = []
    milestones = (
        (user["games_played"] >= 1, "🎮 First Game"),
        (user["games_won"] >= 1, "🏆 First Win"),
        (user["games_won"] >= 10, "👑 Ten Wins"),
        (word_count >= 100, "✍️ Wordsmith (100 words)"),
        (user["total_points"] >= 500, "⭐ 500 Career Points"),
    )
    earned.extend(title for achieved, title in milestones if achieved)
    await update.message.reply_text(
        "🏅 YOUR ACHIEVEMENTS\n\n"
        + ("\n".join(earned) if earned else "No achievements yet. Join a game to begin!")
    )


async def missions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("For privacy, open my private chat and use /missions there.")
        return
    with connect() as conn:
        rows = conn.execute(
            "SELECT g.game_id,o.objective_text,o.completed FROM games g "
            "JOIN objectives o ON o.game_id=g.game_id "
            "WHERE o.user_id=? AND g.status IN ('active','paused') "
            "ORDER BY g.game_id DESC LIMIT 20",
            (update.effective_user.id,),
        ).fetchall()
    if not rows:
        await update.message.reply_text("You have no active missions.")
        return
    await update.message.reply_text(
        "🔐 YOUR PRIVATE MISSIONS\n\n"
        + "\n\n".join(
            f"Game #{row['game_id']} — {'✅' if row['completed'] else '⏳'} "
            f"{row['objective_text']}"
            for row in rows
        )
    )


async def aijudge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_group(update):
        return
    game = get_active_game(update.effective_chat.id)
    if not game or game["status"] == "waiting":
        await update.message.reply_text("There is no story to judge yet.")
        return
    with connect() as conn:
        rows = conn.execute(
            "SELECT display_name,score FROM game_players WHERE game_id=? "
            "ORDER BY score DESC,turn_order",
            (game["game_id"],),
        ).fetchall()
        completed = conn.execute(
            "SELECT COUNT(*) AS n FROM objectives WHERE game_id=? AND completed=1",
            (game["game_id"],),
        ).fetchone()["n"]
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM objectives WHERE game_id=?",
            (game["game_id"],),
        ).fetchone()["n"]
    score_lines = "\n".join(
        f"{i + 1}. {row['display_name']} — {row['score']} points"
        for i, row in enumerate(rows)
    )
    await update.message.reply_text(
        "⚖️ RULE-BASED STORY JUDGMENT\n\n"
        "This command does not use an AI service or judge story coherence. "
        "It reports only the game's configured word-match scoring.\n\n"
        f"Missions completed: {completed}/{total}\n"
        f"Story words: {game['story_word_count']}\n\n{score_lines}"
    )
