import discord
from discord.ext import tasks, commands
import importlib
import os
import httpx
import asyncio
from dotenv import load_dotenv
import core_system
import economy
import jst
import logging
import views.EconomyApplication as EconomyApplicationViews
import device_monitor
import database as db


load_dotenv()
JST = jst.get_jst()

# 共通のフォーマットを定義
log_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

# ターミナル（コンソール）出力用の設定
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)

# ログの基本設定（handlersにconsole_handlerを指定）
logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler]
)
logger = logging.getLogger(__name__)


class TakasumiAuxiliaryBot(commands.Bot):
    def __init__(self):
        """リアクション検知を含む全てのインテントを有効化"""
        super().__init__(command_prefix='/', intents=discord.Intents.all())

    async def setup_hook(self):
        """起動時の初期化"""
        await db.init_db()
        await core_system.register_to_tree(self)
        await self.tree.sync()
        # ループを開始
        self.update_rate.start()
        self.check_timer_loop.start()
        self.reload_core_system_loop.start()
        if "com.termux" in os.environ.get("PREFIX", ""):
            try:
                await device_monitor.update_device_status(self)
            except Exception as e:
                logger.error(f"Initial Status Update Error: {e}")
            self.device_status_loop.start() # 1回目完了後に定期実行を開始

    @tasks.loop(minutes=10)
    async def device_status_loop(self):
        """スマホのステータス情報チャンネルを更新"""
        await asyncio.to_thread(importlib.reload, device_monitor)  # 非同期でリロード
        await device_monitor.update_device_status(self)

    @tasks.loop(minutes=1)
    async def check_timer_loop(self):
        """リマインダーチェック"""
        try:
            await core_system.check_reminders(self)
        except Exception as e:
            logger.error(f"Loop Error: {e}")

    @tasks.loop(minutes=5)
    async def reload_core_system_loop(self):
        """core_systemのリロード"""
        await asyncio.to_thread(importlib.reload, core_system)  # 非同期でリロード

    @tasks.loop(minutes=5)
    async def update_rate(self):
        """レートの更新"""
        rate = await economy.get_current_rate()
        await db.execute_query("UPDATE system_config SET value = ? WHERE key = 'rate'", (rate,))

    async def on_message(self, message):
        """メッセージ受信イベントをcore_systemへ転送"""
        if message.author == self.user:
            return
        try:
            await core_system.process_message_event(self, message)
        except Exception as e:
            logger.error(f"Message Processing Error: {e}")

    # --- 経済システム（換金・購入承認）用の追加 ---
    async def on_raw_reaction_add(self, payload):
        """リアクション追加イベントをcore_systemへ転送"""
        await asyncio.to_thread(importlib.reload, core_system)  # 非同期でリロード
        await core_system.handle_reaction_event(self, payload)


class DiscordBotLogger(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logging_data = {
            'levels': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            'roles': {
                'DEBUG'   :  '<@&1461192008214249696>',
                'INFO'    :  '<@&1461178511367602189>',
                'WARNING' :  '<@&1461192066326597727>',
                'ERROR'   :  '<@&1461178572164038810>',
                'CRITICAL':  '<@&1461192196735766651>',
            },
            'webhook': {
                'ALL'     :  os.getenv('DISCORD_LOG_WEBHOOK_URL_ALL'),
                'DEBUG'   :  os.getenv('DISCORD_LOG_WEBHOOK_URL_DEBUG'),
                'INFO'    :  os.getenv('DISCORD_LOG_WEBHOOK_URL_INFO'),
                'WARNING' :  os.getenv('DISCORD_LOG_WEBHOOK_URL_WARNING'),
                'ERROR'   :  os.getenv('DISCORD_LOG_WEBHOOK_URL_ERROR'),
                'CRITICAL':  os.getenv('DISCORD_LOG_WEBHOOK_URL_CRITICAL'),
            }
        }

    def emit(self, record):
        if record.name.startswith(('httpx', 'httpcore', 'requests', 'urllib3', 'discord.http', 'discord.gateway')):
            return
        log_entry = self.format(record)
        if log_entry.startswith('【20'):
            log_entry = f"```js\n{log_entry}\n```"
        else:
            log_entry = f"```py\n{log_entry}"
            if len(log_entry) > 1900:
                log_entry = log_entry[:1900] + '  ...\n```\n［詳細はコンソールを参照してください］'
            else:
                log_entry += '\n```'
        level = record.levelname
        role_mention = self.logging_data.get('roles', {}).get(level, '')
        message = f"{role_mention}\n{log_entry}" if role_mention else log_entry

        """Webhook にログを送信"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._send_webhook(message, level))
        except Exception as e:
            print(f"[Webhook Logging Error] Failed to schedule webhook: {e}")

    async def _send_webhook(self, message, level):
        try:
            webhook_config = self.logging_data.get('webhook', {})
            async with httpx.AsyncClient() as client:
                # ALL に送信
                all_webhook_url = webhook_config.get('ALL')
                if all_webhook_url:
                    await client.post(all_webhook_url, json={"content": message})
                # レベル別に送信
                level_webhook_url = webhook_config.get(level)
                if level_webhook_url:
                    await client.post(level_webhook_url, json={"content": message})
        except Exception as e:
            print(f"[Webhook Logging Error] Failed to send log via webhook: {e}")


bot = TakasumiAuxiliaryBot()

discord_bot_logger = DiscordBotLogger()
discord_bot_logger.setFormatter(log_format)
logging.getLogger().addHandler(discord_bot_logger)

@bot.event
async def on_ready():
    # 交換申請のビューを追加
    bot.add_view(EconomyApplicationViews.TC_to_EC(bot))
    bot.add_view(EconomyApplicationViews.EC_to_TC(bot))

    # ログイン成功メッセージ
    now = jst.now().strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f"【{now}】{bot.user.name} としてログインしました")

@bot.event
async def on_error(event_method, *args, **kwargs):
    """一般的なエラー処理"""
    logger.error(f"Error in {event_method}", exc_info=True)

@bot.event
async def on_command_error(ctx, error):
    """コマンドエラー処理"""
    if isinstance(error, commands.CommandNotFound):
        return
    logger.error(f"Command Error: {error}")

@bot.event
async def on_message_edit(before, after):
    if after.author == bot.user:
        return
    await core_system.process_message_event(bot, after)

# --- 起動 ---
token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    logger.critical("DISCORD_TOKEN is not set in environment variables.")
