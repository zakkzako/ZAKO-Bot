import discord
from discord import SyncWebhook
from discord.ext import tasks, commands
import importlib
import os
import datetime
import pytz
from dotenv import load_dotenv
import core_system
import updater
import jst
import logging
import views.EconomyApplication as EconomyApplicationViews

load_dotenv()
JST = jst.get_jst()

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,  # ログレベルを DEBUG に設定
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        # logging.FileHandler('bot.log', encoding='utf-8'),  # ファイルにログを記録    検討中🤔 - ファイルサイズが大きくなりそうなんよね | Yamatomato
        logging.StreamHandler()  # コンソールに出力
    ]
)
logger = logging.getLogger(__name__)

def check_required_files():
    """必須ファイルの存在と形式をチェック"""
    required_files = {
        "config.json": {},
        "users.json": {},
        "economy_data.json": {"total_supply": 0},
        "blackjack_data.json": {}
    }

    log_text = ""
    not_found_files = []
    invalid_format_files = []

    for file, default_content in required_files.items():
        if not os.path.exists(file):
            logger.critical(f"必須ファイル '{file}' が存在しません。ファイルを作成してください。")
            not_found_files.append(file)
            continue
        if file.endswith(".json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError:
                logger.critical(f"必須ファイル '{file}' の形式が不正です。正しい JSON 形式にしてください。")
                invalid_format_files.append(file)
                continue

    if not_found_files != []:
        if log_text != "":
            log_text += "\n"
        log_text += "見つからなかった必須ファイル："
        for f in not_found_files:
            log_text += f"\n  - {f}"
    if invalid_format_files != []:
        if log_text != "":
            log_text += "\n"
        log_text += "形式が不正な必須ファイル："
        for f in invalid_format_files:
            log_text += f"\n  - {f}"
    if log_text != "":
        logger.critical(log_text)
        raise SystemExit("必須ファイルの問題が検出されました。Botの起動を中断しました。詳細はログを確認してください。")

class ZAKO_Bot(commands.Bot):
    def __init__(self):
        """リアクション検知を含む全てのインテントを有効化"""
        super().__init__(command_prefix='/', intents=discord.Intents.all())

    async def setup_hook(self):
        """起動時の初期化とコマンド同期をcore_systemに委譲"""
        await updater.perform_full_update()
        core_system.register_to_tree(self)
        await core_system.init_system(self)
        await self.tree.sync()
        self.check_timer_loop.start()
        self.reload_core_system_loop.start()

    @tasks.loop(seconds=30)
    async def check_timer_loop(self):
        """リマインダーチェック"""
        try:
            # ここに await を追加しました！
            await core_system.check_reminders(self)
        except Exception as e:
            logger.error(f"Loop Error: {e}")


    @tasks.loop(minutes=5)
    async def reload_core_system_loop(self):
        """core_systemのリロード"""
        importlib.reload(core_system)

    async def on_message(self, message):
        """メッセージ受信イベントをcore_systemへ転送"""
        if message.author == self.user:
            return
        try:
            """importlib.reload(core_system)"""
            await core_system.process_message_event(self, message)
        except Exception as e:
            logger.error(f"Message Processing Error: {e}")

    async def on_message_edit(self, before, after):
        """メッセージ編集イベントをcore_systemへ転送"""
        if after.author == self.user:
            return
        try:
            """importlib.reload(core_system)"""
            await core_system.process_message_event(self, after)
        except Exception as e:
            logger.error(f"Message Edit Processing Error: {e}")

    # --- 経済システム（換金・購入承認）用の追加 ---
    async def on_raw_reaction_add(self, payload):
        """リアクション追加イベントをcore_systemへ転送"""
        importlib.reload(core_system)
        await core_system.handle_reaction_event(self, payload)

logging_data = {
    'roles': {
        'DEBUG'   :  '<@&1461192008214249696>',
        'INFO'    :  '<@&1461178511367602189>',
        'WARNING' :  '<@&1461192066326597727>',
        'ERROR'   :  '<@&1461178572164038810>',
        'CRITICAL':  '<@&1461192196735766651>',
    },
    'webhooks': {
        'ALL'     :  os.getenv('DISCORD_LOG_WEBHOOK_URL_ALL'),
        'DEBUG'   :  os.getenv('DISCORD_LOG_WEBHOOK_URL_DEBUG'),
        'INFO'    :  os.getenv('DISCORD_LOG_WEBHOOK_URL_INFO'),
        'WARNING' :  os.getenv('DISCORD_LOG_WEBHOOK_URL_WARNING'),
        'ERROR'   :  os.getenv('DISCORD_LOG_WEBHOOK_URL_ERROR'),
        'CRITICAL':  os.getenv('DISCORD_LOG_WEBHOOK_URL_CRITICAL'),
    }
}

class DiscordBotLogger(logging.Handler):
    def __init__(self):
        super().__init__()
        self.webhook = {
            'ALL'     :  SyncWebhook.from_url(logging_data['webhooks']['ALL']),
            'DEBUG'   :  SyncWebhook.from_url(logging_data['webhooks']['DEBUG']),
            'INFO'    :  SyncWebhook.from_url(logging_data['webhooks']['INFO']),
            'WARNING' :  SyncWebhook.from_url(logging_data['webhooks']['WARNING']),
            'ERROR'   :  SyncWebhook.from_url(logging_data['webhooks']['ERROR']),
            'CRITICAL':  SyncWebhook.from_url(logging_data['webhooks']['CRITICAL']),
        }

    def emit(self, record):
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
        role_mention = logging_data.get('roles', {}).get(level, '')
        message = f"{role_mention}\n{log_entry}" if role_mention else log_entry
        
        """Webhook にログを送信"""
        try:
            message = message.encode('utf-8').decode('utf-8')
            # All に送信
            self.webhook['ALL'].send(message)
            # レベル別に送信
            if level in self.webhook:
                self.webhook[level].send(message)
        except Exception as e:
            print(f"[Webhook Logging Error] Failed to send log via webhook: {e}")

bot = ZAKO_Bot()

@bot.event
async def on_ready():
    # 交換申請のビューを追加
    bot.add_view(EconomyApplicationViews.TC_to_EC())
    bot.add_view(EconomyApplicationViews.EC_to_TC())

    # ログイン成功メッセージ
    now = jst.now().strftime('%Y/%m/%d %H:%M:%S')
    logger.info(f"【{now}】{bot.user.name} としてログインしました")

discord_bot_logger = DiscordBotLogger()
logger.addHandler(discord_bot_logger)
logging.getLogger('discord').addHandler(discord_bot_logger)

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


# --- 起動 ---
token = os.getenv('DISCORD_TOKEN')

if not token:
    logger.critical("DISCORD_TOKEN が環境変数に設定されていません。Botを起動できません。")
    raise SystemExit("環境変数DISCORD_TOKEN が設定されていません。Botの起動を中断しました。")

check_required_files()