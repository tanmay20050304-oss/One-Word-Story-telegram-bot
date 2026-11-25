from telegram import Update
from telegram.ext import ContextTypes

from database.db import connect
from game.game_manager import get_active_game
from game.scoring import undo_player_word
from handlers.start import help_command, profile


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command(update, context)


async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await profile(update, context)


async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with connect() as conn:
        row = conn.execute(
            "SELECT total_points, games_played, games_won FROM users WHERE user_id=?",
            (user.id,),
        ).fetchone()
        if row is None:
            await update.message.reply_text("Use /start or /profile to create your profile first.")
            return
        position = conn.execute(
            "SELECT COUNT(*) + 1 AS position FROM users WHERE total_points > ?",
            (row["total_points"],),
        ).fetchone()["position"]

    await update.message.reply_text(
        f"🏅 YOUR RANK: #{position}\n"
        f"⭐ Points: {row['total_points']}\n"
        f"🎮 Games played: {row['games_played']}\n"
        f"🏆 Wins: {row['games_won']}"
    )


def _active_player_game(user_id: int):
    with connect() as conn:
        return conn.execute(
            "SELECT g.game_id,g.chat_id,g.status FROM games g "
            "JOIN game_players gp ON gp.game_id=g.game_id "
            "WHERE gp.user_id=? AND g.status IN ('active','paused') "
            "ORDER BY g.game_id DESC LIMIT 1",
            (user_id,),
        ).fetchone()


async def mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private":
        await update.message.reply_text("For privacy, open my private chat and use /mission there.")
        return

    game = _active_player_game(user.id)
    if not game or game["status"] != "active":
        await update.message.reply_text("You don't have an active game mission right now.")
        return

    with connect() as conn:
        objective = conn.execute(
            "SELECT objective_text,completed FROM objectives WHERE game_id=? AND user_id=?",
            (game["game_id"], user.id),
        ).fetchone()
    if objective is None:
        await update.message.reply_text("Your mission hasn't been assigned yet.")
        return

    state = "✅ Completed" if objective["completed"] else "⏳ Not completed"
    await update.message.reply_text(f"🎯 YOUR SECRET MISSION\n\n{objective['objective_text']}\n\n{state}")


async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type != "private":
        await update.message.reply_text("For privacy, open my private chat and use /hint there.")
        return

    game = _active_player_game(user.id)
    if not game or game["status"] != "active":
        await update.message.reply_text("Hints are available during an active game.")
        return

    with connect() as conn:
        objective = conn.execute(
            "SELECT keywords,completed FROM objectives WHERE game_id=? AND user_id=?",
            (game["game_id"], user.id),
        ).fetchone()
    if objective is None:
        await update.message.reply_text("Your mission hasn't been assigned yet.")
        return
    if objective["completed"]:
        await update.message.reply_text("You've already completed your mission. No hint needed!")
        return

    keyword = next(
        (item.strip() for item in objective["keywords"].split(",") if item.strip()),
        None,
    )
    if keyword is None:
        await update.message.reply_text("No hint is available for this mission.")
        return
    await update.message.reply_text(
        f"🔎 Hint: a matching word starts with “{keyword[0].upper()}”."
    )


async def myword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type == "private":
        game = _active_player_game(user.id)
    else:
        game = get_active_game(update.effective_chat.id)

    if not game:
        await update.message.reply_text("You don't have a current game.")
        return
    with connect() as conn:
        word = conn.execute(
            "SELECT word,position FROM story_words WHERE game_id=? AND user_id=? "
            "ORDER BY position DESC LIMIT 1",
            (game["game_id"], user.id),
        ).fetchone()
    if word is None:
        await update.message.reply_text("You haven't added a word to this story yet.")
        return
    await update.message.reply_text(
        f"📝 Your latest word: {word['word']} (story word {word['position']})"
    )


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Use /undo in the group where your game is active.")
        return
    game = get_active_game(update.effective_chat.id)
    if not game or game["status"] != "active":
        await update.message.reply_text("There is no active game to undo a word in.")
        return

    ok, message = undo_player_word(game["game_id"], update.effective_user.id)
    await update.message.reply_text(message)
