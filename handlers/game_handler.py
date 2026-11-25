from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import LOGO_PATH, MIN_PLAYERS, MAX_PLAYERS
from game.game_manager import (
    create_room, get_active_game, get_game, get_players, join_room,
    start_room, current_player, get_objective, get_group_for_game,
    finish_game, cancel_waiting_room
)
from game.story_builder import get_story

async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Please create the game inside a Telegram group.")
        return
    existing = get_active_game(update.effective_chat.id)
    if existing:
        await update.message.reply_text(
            f"An unfinished room already exists: Game #{existing['game_id']}."
        )
        return
    game_id = create_room(update.effective_chat.id, update.effective_user)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Join Game", callback_data=f"join:{game_id}")]
    ])
    with LOGO_PATH.open("rb") as logo:
        await update.message.reply_photo(
            photo=logo,
            caption=(
                f"🎮 ONE WORD STORY\n\nRoom ID: #{game_id}\n\n"
                f"👥 Players joined: 1/{MAX_PLAYERS}\n"
                f"Host: {update.effective_user.first_name}\n\n"
                "Friends: tap Join Game to enter.\n"
                f"The host can use /startgame@{context.bot.username} when everyone is ready."
            ),
            reply_markup=keyboard,
        )

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game_id = int(query.data.split(":")[1])
    if query.message.chat.type == "private":
        await query.answer()
        await query.edit_message_text("Join from the Telegram group where the game room was created.")
        return
    ok, message = join_room(game_id, query.from_user)
    if not ok:
        await query.answer(message, show_alert=True)
        return
    await query.answer()
    players = get_players(game_id)
    game = get_game(game_id)
    target = game["target_players"] or MAX_PLAYERS
    names = "\n".join(f"{i+1}. {p['display_name']}" for i, p in enumerate(players))
    await query.message.reply_text(
        f"✅ {query.from_user.first_name} joined!\n\n👥 Players ({len(players)}/{target})\n{names}\n\n"
        "Remember: open the bot privately and press /start before the host starts."
    )

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Use /startgame in the group where the room was created.")
        return
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("No waiting room found. Create one using /create.")
        return
    ok, message = start_room(game["game_id"], update.effective_user.id)
    if not ok:
        await update.message.reply_text(message)
        return
    players = get_players(game["game_id"])
    await update.message.reply_text(
        "🚀 THE GAME HAS STARTED!\n\n"
        + "\n".join(f"{i+1}. {p['display_name']}" for i, p in enumerate(players))
        + "\n\n📖 First player: " + players[0]["display_name"]
        + f"\nOn your turn, send one word or use /word@{context.bot.username} moon."
    )
    # Send each secret objective privately.
    for p in players:
        obj = get_objective(game["game_id"], p["user_id"])
        try:
            await context.bot.send_message(
                chat_id=p["user_id"],
                text=f"🔐 YOUR SECRET OBJECTIVE\n\n{obj['objective_text']}\n\n"
                     "Complete it by contributing a matching word. Do not reveal your mission!"
            )
        except Exception:
            await update.message.reply_text(
                f"⚠️ Could not send a private mission to {p['display_name']}. "
                "They must press /start in the bot's private chat."
            )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("There is no active room in this chat.")
        return
    players = get_players(game["game_id"])
    story = get_story(game["game_id"]) or "(The story has not started yet.)"
    current = current_player(game["game_id"]) if game["status"] in ("active", "paused") else None
    await update.message.reply_text(
        f"📖 STORY SO FAR\n\n{story}\n\n"
        f"👥 Players: {len(players)}\n"
        f"📝 Words: {game['story_word_count']}/40\n"
        + (f"🎯 Current turn: {current['display_name']}" if current else "Waiting for host to start.")
        + ("\n⏸️ Game is paused." if game["status"] == "paused" else "")
    )

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = get_active_game(update.effective_chat.id)
    if not game:
        await update.message.reply_text("There is no active game.")
        return
    if game["host_id"] != update.effective_user.id:
        await update.message.reply_text("Only the host can end the game.")
        return
    if game["status"] == "waiting":
        _, message = cancel_waiting_room(game["game_id"], update.effective_user.id)
        await update.message.reply_text(message)
        return
    await publish_results(update, context, game["game_id"])

async def publish_results(update, context, game_id):
    rows = finish_game(game_id)
    story = get_story(game_id)
    if not rows:
        await update.effective_message.reply_text("Game ended.")
        return
    winner = rows[0]
    leaderboard = "\n".join(
        f"{i+1}. {r['display_name']} — {r['score']} points"
        for i, r in enumerate(rows)
    )
    missions = "\n".join(
        f"{r['display_name']}: {'✅ Completed' if r['completed'] else '❌ Not completed'}"
        for r in rows
    )
    await context.bot.send_message(
        chat_id=get_group_for_game(game_id),
        text=f"🏁 GAME OVER!\n\n📖 FINAL STORY:\n\n{story or '(No words submitted)'}\n\n"
             f"🏆 FINAL SCORES\n{leaderboard}\n\n🎯 SECRET MISSIONS\n{missions}\n\n"
             f"🥇 WINNER: {winner['display_name']}!"
    )
