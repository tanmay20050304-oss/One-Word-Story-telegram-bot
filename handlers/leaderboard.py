from telegram import Update
from telegram.ext import ContextTypes
from database.db import connect

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with connect() as conn:
        rows = conn.execute(
            "SELECT first_name,total_points,games_won FROM users "
            "ORDER BY total_points DESC LIMIT 10"
        ).fetchall()
    if not rows:
        await update.message.reply_text("No leaderboard data yet. Play a game first!")
        return
    text = "🏆 ONE WORD STORY — TOP PLAYERS\n\n"
    text += "\n".join(
        f"{i+1}. {r['first_name']} — {r['total_points']} points ({r['games_won']} wins)"
        for i, r in enumerate(rows)
    )
    await update.message.reply_text(text)
