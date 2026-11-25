import re
from telegram import Update
from telegram.ext import ContextTypes
from config import MAX_STORY_WORDS, TWIST_EVERY_WORDS
from database.db import connect
from game.game_manager import (
    get_active_game, current_player, next_turn, activate_twist,
    get_twist_after_word
)
from game.story_builder import add_word, get_story
from game.scoring import complete_objective_if_matched, add_points
from game.twist_engine import choose_twist, get_twist_by_title
from handlers.game_handler import publish_results

WORD_PATTERN = re.compile(r"^[A-Za-z]+(?:['’-][A-Za-z]+)?$")

async def submit_word_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            f"Use /word@{context.bot.username} followed by exactly one word, "
            f"for example: /word@{context.bot.username} moon"
        )
        return
    await submit_word(update, context, context.args[0])

async def submit_word(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    submitted_word: str | None = None,
):
    if update.effective_chat.type == "private":
        if submitted_word is not None:
            await update.message.reply_text("Submit /word in the Telegram group where the game is active.")
        return
    game = get_active_game(update.effective_chat.id)
    if not game or game["status"] != "active":
        if submitted_word is not None:
            if game and game["status"] == "paused":
                await update.message.reply_text("The game is paused. The host can use /resume.")
            else:
                await update.message.reply_text("There is no active game in this group. Use /create to open a room.")
        return
    player = current_player(game["game_id"])
    if not player:
        if submitted_word is not None:
            await update.message.reply_text("I could not find the current player. Ask the host to check /status.")
        return
    user = update.effective_user
    if user.id != player["user_id"]:
        await update.message.reply_text(f"⏳ It is {player['display_name']}'s turn. Please wait.")
        return
    word = (submitted_word if submitted_word is not None else update.message.text).strip()
    if not WORD_PATTERN.fullmatch(word):
        await update.message.reply_text("❌ Please send exactly ONE word using letters only.")
        return

    position = add_word(game["game_id"], user.id, word)
    if position is None:
        return

    with connect() as conn:
        conn.execute("DELETE FROM game_votes WHERE game_id=?", (game["game_id"],))

    completed = complete_objective_if_matched(game["game_id"], user.id, word)
    if completed:
        await context.bot.send_message(
            chat_id=user.id,
            text="🎯 Secret objective completed! You earned 50 points."
        )
        await update.message.reply_text("🎉 A player completed a secret mission! (+50 points)")

    # Read the pending twist from SQLite so it survives a bot restart.
    twist_title = get_twist_after_word(game["game_id"], position - 1)
    twist = get_twist_by_title(twist_title) if twist_title else None
    if twist:
        _, _, keywords = twist
        if word.lower() in keywords:
            add_points(game["game_id"], user.id, 20)
            await update.message.reply_text("🌟 Twist challenge completed! +20 points.")

    story = get_story(game["game_id"])
    await update.message.reply_text(f"📖 STORY SO FAR:\n\n{story}")

    if position >= MAX_STORY_WORDS:
        await publish_results(update, context, game["game_id"])
        return

    if position % TWIST_EVERY_WORDS == 0:
        twist = choose_twist()
        activate_twist(game["game_id"], twist[0], position)
        await update.message.reply_text(
            f"🚨 UNEXPECTED TWIST: {twist[0]}\n\n{twist[1]}\n"
            "The next player's word can earn +20 bonus points if it matches the twist."
        )

    next_player = next_turn(game["game_id"])
    if next_player:
        await update.message.reply_text(
            f"🎯 NEXT TURN: {next_player['display_name']}\n"
            f"Send one word, or use /word@{context.bot.username} moon."
        )

async def skip_turn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return
    game = get_active_game(update.effective_chat.id)
    if not game or game["status"] != "active":
        await update.message.reply_text("There is no active game.")
        return
    if game["host_id"] != update.effective_user.id:
        await update.message.reply_text("Only the host can skip a turn.")
        return
    player = current_player(game["game_id"])
    if not player:
        await update.message.reply_text("No current player was found for this game.")
        return
    with connect() as conn:
        conn.execute("DELETE FROM game_votes WHERE game_id=?", (game["game_id"],))
        conn.execute(
            "UPDATE game_players SET missed_turns=missed_turns+1 WHERE game_id=? AND user_id=?",
            (game["game_id"], player["user_id"])
        )
    next_player = next_turn(game["game_id"])
    await update.message.reply_text(
        f"⏭️ {player['display_name']}'s turn was skipped. "
        f"Next: {next_player['display_name']}."
    )
