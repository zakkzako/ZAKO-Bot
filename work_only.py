import discord
from discord.ext import tasks
import os
import datetime
import pytz
from dotenv import load_dotenv
import logging
import json
import asyncio
import aiohttp
import sys
from pathlib import Path

load_dotenv()

JST = pytz.timezone('Asia/Tokyo')
REMINDERS_FILE = Path('reminders.json')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

JOBS = {
    "unknown": {"name": "不明", "time": 60, "base": 0, "bonus": 0},
    "none": {"name": "無職", "time": 10, "base": 100, "bonus": 0},
    "gambler": {"name": "ギャンブラー", "time": 10, "base": 80, "bonus": 0.8},
    "chick_taxonomist": {"name": "ひよこ鑑定士", "time": 10, "base": 300, "bonus": 0},
    "freeter": {"name": "フリーター", "time": 15, "base": 500, "bonus": 0.1},
    "farmer": {"name": "農家", "time": 20, "base": 1000, "bonus": 0.1},
    "influencer": {"name": "インフルエンサー", "time": 5, "base": 300, "bonus": 0.3},
    "architect": {"name": "建築家", "time": 45, "base": 3000, "bonus": 0.1},
    "investor": {"name": "投資家", "time": 30, "base": 3000, "bonus": 0.5},
    "engineer": {"name": "エンジニア", "time": 60, "base": 10000, "bonus": 0.3},
    "doctor": {"name": "医師", "time": 60, "base": 12000, "bonus": 0.1}
}

intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True

client = discord.Client(intents=intents)

http_session: aiohttp.ClientSession | None = None
is_enabled = False
is_shutting_down = False

async def network_check() -> bool:
    if http_session is None:
        return False
    try:
        async with http_session.get('https://www.google.com/generate_204', timeout=5) as resp:
            return resp.status == 204
    except Exception:
        return False

async def load_reminders() -> list[dict]:
    if not REMINDERS_FILE.exists():
        return []
    try:
        return json.loads(REMINDERS_FILE.read_text(encoding='utf-8'))
    except Exception as e:
        logger.error(f"Failed to load reminders: {e}")
        return []

async def save_reminders(reminders: list[dict]):
    try:
        REMINDERS_FILE.write_text(
            json.dumps(reminders, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    except Exception as e:
        logger.error(f"Failed to save reminders: {e}")

async def shutdown_bot():
    global is_shutting_down
    is_shutting_down = True
    
    if http_session is not None:
        await http_session.close()
    
    logger.info("The Bot has been shut down.")
    logger.info("Stopping the process...")
    await asyncio.sleep(0.5)
    sys.exit(0)

def enable_bot():
    global is_enabled
    is_enabled = True

def disable_bot():
    global is_enabled
    is_enabled = False

@tasks.loop(seconds=15)
async def check_reminders_task():
    if is_shutting_down:
        return

    now_ts = datetime.datetime.now(JST).timestamp()
    reminders = await load_reminders()
    updated = []

    for r in reminders:
        target_ts = datetime.datetime.fromisoformat(r['target_time']).timestamp()
        if now_ts >= target_ts:
            if not is_enabled:
                continue
            try:
                channel = await client.fetch_channel(r['channel_id'])
                user_mention = f"<@{r['user_id']}>"
                embed = discord.Embed(
                    color=0x42bcf4,
                    description=(
                        f"最後の `/work` から **{r.get('cooldown_min', 60)} 分** が経過しました！\n"
                        "</work:1132868147519692871> を実行できます！"
                    )
                )
                await channel.send(content=user_mention, embed=embed)
                logger.debug(f"Reminder sent: user: {r['user_id']}")
            except Exception as e:
                logger.error(f"Failed to send: {e}")
                updated.append(r)
        else:
            updated.append(r)

    if len(updated) != len(reminders):
        await save_reminders(updated)

async def detect_work_message(message: discord.Message):
    if not message.embeds:
        return
    if not message.author.bot:
        return
    if message.author.id != 981314695543783484:
        return

    embed = message.embeds[0]
    if not embed.author or not embed.description:
        return
    if not embed.author.name.endswith('コインを手に入れました'):
        return
    if not embed.description.startswith('給料: '):
        return

    logger.debug(f"message.interaction_metadata.name: {message.interaction_metadata.get('name', 'N/A')}")

    user = None
    if hasattr(message, 'interaction_metadata') and message.interaction_metadata:
        user = message.interaction_metadata.user

    if user is None:
        logger.warning("Failed to identify user from interaction metadata.")
        return

    job = JOBS["unknown"]
    if await network_check():
        try:
            async with http_session.get(f"https://api.takasumibot.com/v3/profile/{user.id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    job_key = data.get('jobType', 'unknown')
                    job = JOBS.get(job_key, JOBS["unknown"])
        except Exception as e:
            logger.error(f"Failed to get job information: {e}")

    cooldown_min = job["time"]
    remind_at = datetime.datetime.now(JST) + datetime.timedelta(minutes=cooldown_min)

    reminder = {
        "user_id": user.id,
        "channel_id": message.channel.id,
        "target_time": remind_at.isoformat(),
        "cooldown_min": cooldown_min,
        "notification_type": "external_work"
    }

    reminders = await load_reminders()
    reminders.append(reminder)
    await save_reminders(reminders)

    embed = discord.Embed(
        color=0x42bcf4,
        description=f"`/work` を検知しました\n{cooldown_min}分後に通知します"
    )
    embed.set_author(name=user.name, icon_url=user.display_avatar.url)
    await message.reply(content=f"<@{user.id}>", embed=embed, mention_author=False)

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.author.id == 1160453651660288041:
        if message.content.strip() == '!shutdown -y':
            if is_shutting_down:
                await message.reply("Shutdown is already in progress.", mention_author=False)
                return
            await message.reply("Shutdown initiated.\nThe bot will go offline and process will stop shortly.", mention_author=False)
            await shutdown_bot()
        elif message.content.strip() == '!bot enable':
            if is_enabled:
                await message.reply("Bot is already enabled.", mention_author=False)
                return
            enable_bot()
            await message.reply("Bot has been enabled.", mention_author=False)
        elif message.content.strip() == '!bot disable':
            if not is_enabled:
                await message.reply("Bot is already disabled.", mention_author=False)
                return
            disable_bot()
            await message.reply("Bot has been disabled.", mention_author=False)
        return

    if message.author.bot and message.author.id == 981314695543783484:
        if not is_enabled:
            return
        await detect_work_message(message)

@client.event
async def on_message_edit(before, after):
    if after.author.bot and after.author.id == 981314695543783484:
        if not is_enabled:
            return
        await detect_work_message(after)

@client.event
async def on_ready():
    global http_session
    http_session = aiohttp.ClientSession()
    check_reminders_task.start()
    logger.info(f"Bot is Ready! Logged in as: {client.user}")

async def main():
    global http_session
    try:
        await client.start(os.getenv('DISCORD_BOT_TOKEN'))
    finally:
        if http_session is not None:
            await http_session.close()
        if check_reminders_task.is_running():
            check_reminders_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
