from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from game.game_manager import register_user
from database.db import connect
from config import LOGO_PATH

def bot_command(name: str, bot_username: str | None) -> str:
    return f"/{name}@{bot_username}" if bot_username else f"/{name}"

def help_text(bot_username: str | None = None) -> str:
    word_command = f"{bot_command('word', bot_username)} moon"
    return (
        "📖 HOW TO PLAY — ONE WORD STORY\n\n"
        f"• A host creates a room using {bot_command('create', bot_username)}.\n"
        "• Friends tap Join Game.\n"
        f"• Host starts with {bot_command('startgame', bot_username)} (minimum 2 players).\n"
        f"• On your turn, send one word or use {word_command}.\n"
        "• Your secret mission is sent privately by the bot.\n"
        "• A random twist appears every 5 story words.\n"
        "• The story ends at 40 words. Highest score wins.\n\n"
        f"Commands:\n{bot_command('create', bot_username)} — create a room\n"
        f"{bot_command('startgame', bot_username)} — start (host only)\n"
        f"{bot_command('word', bot_username)} <word> — submit your turn\n"
        f"{bot_command('status', bot_username)} — show game status\n"
        f"{bot_command('skip', bot_username)} — skip current turn\n"
        f"{bot_command('endgame', bot_username)} — end or cancel (host only)\n"
        f"{bot_command('profile', bot_username)} — your stats\n"
        f"{bot_command('mystats', bot_username)} — your stats\n"
        f"{bot_command('rank', bot_username)} — your global rank\n"
        f"{bot_command('leaderboard', bot_username)} — top players\n"
        f"{bot_command('rules', bot_username)} — show these rules\n"
        f"{bot_command('mission', bot_username)} — show your private mission\n"
        f"{bot_command('missions', bot_username)} — show all active missions privately\n"
        f"{bot_command('hint', bot_username)} — get a private mission hint\n"
        f"{bot_command('myword', bot_username)} — show your latest story word\n"
        f"{bot_command('undo', bot_username)} — undo your previous word on your turn\n"
        f"{bot_command('story', bot_username)} — show the full story\n"
        f"{bot_command('mysterybox', bot_username)} — open your one-use bonus box\n"
        f"{bot_command('vote', bot_username)} — vote to skip the current turn\n"
        f"{bot_command('achievements', bot_username)} — show your achievements\n"
        f"{bot_command('addplayer', bot_username)} — host adds a player to a waiting room\n"
        f"{bot_command('removeplayer', bot_username)} — host removes a waiting-room player\n"
        f"{bot_command('setplayers', bot_username)} <count> — set the waiting-room target\n"
        f"{bot_command('announce', bot_username)} <message> — host announcement\n"
        f"{bot_command('pause', bot_username)} / {bot_command('resume', bot_username)} "
        "— host pauses or resumes\n"
        f"{bot_command('twist', bot_username)} — host adds an extra twist\n"
        f"{bot_command('rematch', bot_username)} — previous host rematches\n"
        f"{bot_command('aijudge', bot_username)} — show rule-based scoring (not AI)"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user, private_started=1 if update.effective_chat.type == "private" else None)
    if update.effective_chat.type == "private":
        text = (
            "🎮 ONE WORD STORY\n\n"
            "Every great story starts with one word. What happens next is up to you!\n\n"
            "To play:\n"
            "1. Open a Telegram group and add this bot.\n"
            f"2. Use {bot_command('create', context.bot.username)} in the group.\n"
            "3. Friends join with the Join Game button.\n"
            "4. Everyone privately starts this bot to receive a secret mission.\n\n"
            f"In groups, use {bot_command('word', context.bot.username)} moon on your turn "
            "if ordinary words are not received.\n\n"
            f"Commands: {bot_command('help', context.bot.username)} "
            f"{bot_command('rules', context.bot.username)} "
            f"{bot_command('profile', context.bot.username)} "
            f"{bot_command('mystats', context.bot.username)} "
            f"{bot_command('rank', context.bot.username)} "
            f"{bot_command('leaderboard', context.bot.username)}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 How to Play", callback_data="help_unused")]
        ])
        with LOGO_PATH.open("rb") as logo:
            await update.message.reply_photo(
                photo=logo,
                caption=text,
                reply_markup=keyboard,
            )
    else:
        await update.message.reply_text(
            f"Hello! To create a game, use {bot_command('create', context.bot.username)}. "
            "Players must also open me privately and press /start to receive secret missions."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(help_text(context.bot.username))

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(
        caption=help_text(context.bot.username),
        reply_markup=None,
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user.id,)).fetchone()
    await update.message.reply_text(
        f"👤 PROFILE: {row['first_name']}\n\n"
        f"⭐ Total points: {row['total_points']}\n"
        f"🎮 Games played: {row['games_played']}\n"
        f"🏆 Games won: {row['games_won']}"
    )
