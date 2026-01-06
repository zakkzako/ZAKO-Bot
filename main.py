import discord
from discord.ext import commands
import os
import core_system
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（DISCORD_TOKEN, ADMIN_IDなど）
load_dotenv()

# インテントの設定
intents = discord.Intents.default()
intents.message_content = True # メッセージ内容の取得に必要
intents.members = True         # メンバー情報の取得に必要
intents.reactions = True       # リアクション（✅）の検知に必須

# Botのインスタンス作成
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    """Botが起動した際の処理"""
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    
    # スラッシュコマンドの登録と同期
    core_system.register_to_tree(bot)
    await core_system.init_system(bot)
    
    print("--- Bot is ready ---")

@bot.event
async def on_message(message):
    """メッセージを受信した際の処理"""
    # work検知などのイベント処理
    await core_system.process_message_event(bot, message)
    
    # 通常のコマンド処理
    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    """リアクションが追加された際の処理（換金・購入の承認用）"""
    # core_system側の経済確定ロジックを呼び出す
    await core_system.handle_reaction_event(bot, payload)

# Botの起動
token = os.getenv('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("Error: DISCORD_TOKEN が設定されていません。")
