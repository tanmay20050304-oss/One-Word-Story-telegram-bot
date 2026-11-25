# One Word Story — Telegram Multiplayer Bot

A turn-based Telegram group game. Players contribute one word at a time, receive private secret objectives, encounter random story twists, and compete for points.

## Features in this version

- Create a game room in a Telegram group.
- Join with an inline button (2–10 players).
- Host starts the game.
- Private secret objectives (one per player).
- One-word turns with input validation.
- A random twist every five story words.
- Objective completion: +50 points.
- Matching the next twist challenge: +20 points.
- Story ends after 40 words.
- Final scores, winner, missions and leaderboard.
- SQLite persistence for users and game records.
- The supplied logo appears in the private welcome and group game-room message.

## 1. Create your Telegram bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Send `/newbot`.
3. Follow the instructions and copy the bot token.
4. Add the bot to your Telegram group as a member.
5. For group word messages to reach the bot, open BotFather, use `/setprivacy`, select your bot, and choose **Disable**. Then remove and re-add the bot to the group if Telegram asks you to.
6. To use the same image as the bot's Telegram profile picture, set it separately with BotFather. The game also sends the logo in its welcome and room messages.

Keep the token private. Never upload `.env` to GitHub.

## 2. Install Python

Use Python 3.10 or newer. Check:

```bash
python --version
```

## 3. Set up the project

Open the project folder in VS Code terminal.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Open `.env` and replace the example value:

```env
BOT_TOKEN=YOUR_REAL_BOT_TOKEN
```

## 4. Run the bot

```bash
python bot.py
```

Keep the terminal running while you test.

## 5. Play the game

1. Each player opens the bot's private chat and presses **Start** or sends `/start`. This is required because Telegram bots cannot start private conversations themselves.
2. Add the bot to a Telegram group. Disable BotFather privacy mode as described above so it can read ordinary group messages.
3. In the group, send `/create@OneWordStory_bot` (replace the username with your bot's username if different).
4. Other players tap **Join Game**.
5. The host sends `/startgame@OneWordStory_bot`.
6. Each player receives their secret objective privately.
7. With privacy mode enabled, address group commands to the bot: `/create@OneWordStory_bot`, `/startgame@OneWordStory_bot`, and `/word@OneWordStory_bot moon` (replace `OneWordStory_bot` with your bot's actual username). Or disable privacy mode in BotFather and re-add the bot to send ordinary words.
8. A twist appears every five accepted words. The next player's matching word earns 20 bonus points.
9. The game ends at 40 words, or the host can use `/endgame`.

## Commands

| Command | Where | Purpose |
|---|---|---|
| `/start` | Private chat | Register and enable private missions |
| `/help` | Anywhere | Show rules |
| `/create@YourBot` | Group | Create a room |
| `/word@YourBot <word>` | Group | Submit a word on your turn |
| `/startgame@YourBot` | Group | Host starts the game |
| `/undo@YourBot` | Group | Remove your latest contribution when your turn comes around |
| `/story@YourBot` | Group | Show the full story |
| `/status@YourBot` | Group | Show story and current turn |
| `/skip@YourBot` | Group | Host skips the current player |
| `/endgame@YourBot` | Group | Host ends the active game or cancels a waiting room |
| `/addplayer@YourBot` | Group | Host adds a registered player by replying to them or using their ID/username |
| `/removeplayer@YourBot` | Group | Host removes a player from a waiting room |
| `/setplayers@YourBot <count>` | Group | Set an exact room size before starting (2–10) |
| `/pause@YourBot` | Group | Host pauses an active game |
| `/resume@YourBot` | Group | Host resumes a paused game |
| `/vote@YourBot` | Group | Vote to skip the current turn; a majority is required |
| `/twist@YourBot` | Group | Host adds an extra twist challenge for the next word |
| `/mysterybox@YourBot` | Group | Open a one-time random bonus box during a game |
| `/announce@YourBot <message>` | Group | Host sends an announcement |
| `/rematch@YourBot` | Group | Previous host creates a new waiting room with the same players |
| `/aijudge@YourBot` | Group | Show the deterministic rule-based score audit (not an AI verdict) |
| `/profile` | Anywhere | Create your profile or show personal stats |
| `/mystats` | Anywhere | Alias for `/profile` |
| `/rank` | Anywhere | Show your global points rank |
| `/leaderboard` | Anywhere | Show top players |
| `/achievements` | Anywhere | Show earned milestones |
| `/rules` | Anywhere | Alias for `/help` |
| `/mission` | Private chat | Show your secret mission privately |
| `/missions` | Private chat | Show all your active missions privately |
| `/hint` | Private chat | Get a private hint for your mission |
| `/myword` | Group or private chat | Show your latest word in the active game |

## Project structure

```text
one-word-story/
├── bot.py
├── config.py
├── assets/
│   └── one_word_story_logo.png
├── handlers/
│   ├── start.py
│   ├── game_handler.py
│   ├── story_handler.py
│   ├── leaderboard.py
│   ├── player_commands.py
│   └── extended_commands.py
├── game/
│   ├── game_manager.py
│   ├── story_builder.py
│   ├── objective_engine.py
│   ├── twist_engine.py
│   └── scoring.py
├── database/
│   └── db.py
├── requirements.txt
└── .env
```

## Rules and implementation notes

- A valid word contains letters and may include an apostrophe or hyphen.
- The game currently checks objectives by matching a contributed word against the objective's keyword list. This keeps the MVP deterministic and avoids needing an AI API.
- `/undo` is available to the player whose turn is active and removes that player's latest contribution. The bot recalculates mission and twist points after the removal.
- `/setplayers N` makes the waiting room require exactly N players before it can start. Hosts can add/remove players only before starting; added players must have opened the bot privately.
- `/pause` and `/resume` preserve the current game and turn. `/vote` needs more than half of the players to agree before skipping a turn.
- Each player can open one mystery box per game for a random 5–20 point bonus. Extra `/twist` challenges apply to the next contributed word.
- `/aijudge` is a transparent rule-based score report; it does not call an AI provider or assess story coherence.
- Twists are announced after every five words. The next player's word earns the twist bonus if it matches one of that twist's keywords.
- The 30-second turn duration is announced in the game, but this starter version does not automatically skip on timeout. The host can use `/skip`. Automatic timeout scheduling is a sensible next enhancement.
- Games are scoped to the Telegram group chat. Do not run multiple copies of the bot with polling against the same token.
- SQLite is suitable for local testing and a small prototype. For multi-instance production hosting, migrate to PostgreSQL and use a single worker or a webhook-based deployment.

## Troubleshooting

**Bot does not respond to normal words in the group**
- Disable privacy mode with BotFather `/setprivacy`.
- Remove and re-add the bot to the group.
- Ensure the bot is allowed to read messages.
- If you cannot disable privacy mode, address the command to the bot, e.g. `/word@OneWordStory_bot moon`; Telegram delivers commands addressed to the bot even when normal group messages are hidden.
- With privacy mode enabled, address the command to the bot explicitly: `/word@OneWordStory_bot moon` (replace `OneWordStory_bot` with the actual bot username).

**A player does not receive a secret mission**
- The player must open the bot privately and press Start or send `/start` before the host starts the game.

**`BOT_TOKEN is missing`**
- Ensure `.env` is in the same folder as `bot.py` and contains `BOT_TOKEN=...`.

**`No error but bot does not start`**
- Check that another bot process is not already polling with the same token.
