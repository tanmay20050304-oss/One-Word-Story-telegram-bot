import asyncio
import logging
from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
from database.db import init_db
from handlers.start import start, help_command, help_button, profile
from handlers.game_handler import create_game, join_game, start_game, end_game, status
from handlers.story_handler import submit_word, submit_word_command, skip_turn
from handlers.leaderboard import leaderboard
from handlers.player_commands import hint, mission, myword, mystats, rank, rules, undo
from handlers.extended_commands import (
    addplayer,
    achievements,
    aijudge,
    announce,
    missions,
    mysterybox,
    pause,
    removeplayer,
    rematch,
    resume,
    setplayers,
    story,
    twist,
    vote,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def log_error(update, context):
    logger.error(
        "Unhandled error while processing Telegram update %r",
        update,
        exc_info=context.error,
    )

async def run_bot():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Add it to your .env file.")

    init_db()
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .get_updates_connect_timeout(30)
        .get_updates_read_timeout(30)
        .get_updates_write_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("create", create_game))
    app.add_handler(CommandHandler("startgame", start_game))
    app.add_handler(CommandHandler("endgame", end_game))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("skip", skip_turn))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("word", submit_word_command))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("mission", mission))
    app.add_handler(CommandHandler("myword", myword))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("hint", hint))
    app.add_handler(CommandHandler("undo", undo))
    app.add_handler(CommandHandler("addplayer", addplayer))
    app.add_handler(CommandHandler("story", story))
    app.add_handler(CommandHandler("mysterybox", mysterybox))
    app.add_handler(CommandHandler("rematch", rematch))
    app.add_handler(CommandHandler("setplayers", setplayers))
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("vote", vote))
    app.add_handler(CommandHandler("twist", twist))
    app.add_handler(CommandHandler("achievements", achievements))
    app.add_handler(CommandHandler("missions", missions))
    app.add_handler(CommandHandler("removeplayer", removeplayer))
    app.add_handler(CommandHandler("aijudge", aijudge))
    app.add_handler(CallbackQueryHandler(help_button, pattern=r"^help_unused$"))
    app.add_handler(CallbackQueryHandler(join_game, pattern=r"^join:"))

    # Group messages are interpreted as story words while a game is active.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, submit_word))
    app.add_error_handler(log_error)

    initialized = False
    started = False
    polling = False
    try:
        await app.initialize()
        initialized = True
        command_list = [
            BotCommand("start", "Register and show welcome"),
            BotCommand("help", "Show game instructions"),
            BotCommand("rules", "Show game rules"),
            BotCommand("create", "Create a group game room"),
            BotCommand("startgame", "Start the waiting game"),
            BotCommand("word", "Submit one word on your turn"),
            BotCommand("status", "Show the story and current turn"),
            BotCommand("skip", "Skip the current turn (host only)"),
            BotCommand("endgame", "End game or cancel waiting room"),
            BotCommand("mission", "Show your secret mission privately"),
            BotCommand("hint", "Get a private mission hint"),
            BotCommand("myword", "Show your latest story word"),
            BotCommand("undo", "Undo your previous word on your turn"),
            BotCommand("addplayer", "Host adds a registered player to a waiting room"),
            BotCommand("removeplayer", "Host removes a player from a waiting room"),
            BotCommand("setplayers", "Set exact player target before starting"),
            BotCommand("story", "Show the complete story"),
            BotCommand("mysterybox", "Open your one-use game bonus"),
            BotCommand("rematch", "Create a rematch with the previous players"),
            BotCommand("announce", "Host sends a group announcement"),
            BotCommand("pause", "Host pauses the active game"),
            BotCommand("resume", "Host resumes a paused game"),
            BotCommand("vote", "Vote to skip the current turn"),
            BotCommand("twist", "Host adds an extra twist challenge"),
            BotCommand("achievements", "Show your earned achievements"),
            BotCommand("missions", "Show your active missions privately"),
            BotCommand("aijudge", "Show deterministic rule-based game scoring"),
            BotCommand("rank", "Show your global rank"),
            BotCommand("profile", "Show your player profile"),
            BotCommand("mystats", "Show your player stats"),
            BotCommand("leaderboard", "Show top players"),
        ]
        await app.bot.set_my_commands(
            command_list,
            scope=BotCommandScopeAllGroupChats(),
        )
        await app.bot.set_my_commands(
            command_list,
            scope=BotCommandScopeAllPrivateChats(),
        )
        await app.start()
        started = True
        await app.updater.start_polling(allowed_updates=["message", "callback_query"])
        polling = True
        logger.info("One Word Story bot is running...")
        await asyncio.Event().wait()
    finally:
        if polling:
            await app.updater.stop()
        if started:
            await app.stop()
        if initialized:
            await app.shutdown()


def main():
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
