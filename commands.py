import discord
from discord import app_commands
import json
import os
import importlib
import work

# 管理者IDの取得
admin_id_env = os.getenv('ADMIN_ID')
ADMIN_IDS = [int(admin_id_env)] if admin_id_env else []

class AdminCommands(app_commands.Group):
    def __init__(self, name="admin", description="管理者用コマンド"):
        super().__init__(name=name, description=description)

    @app_commands.command(name="reload", description="各モジュールを再読み込みします")
    async def reload(self, interaction: discord.Interaction):
        if interaction.user.id not in ADMIN_IDS:
            await interaction.response.send_message("権限がありません", ephemeral=True)
            return
        
        importlib.reload(work)
        # 他のモジュールも必要に応じてリロード
        await interaction.response.send_message("モジュールの再読み込みが完了しました", ephemeral=True)

    @app_commands.command(name="jikoku", description="時報を送るチャンネルを現在のチャンネルに設定します")
    async def jikoku(self, interaction: discord.Interaction):
        if interaction.user.id not in ADMIN_IDS:
            await interaction.response.send_message("権限がありません", ephemeral=True)
            return

        config = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                try: config = json.load(f)
                except: config = {}

        config["announcement_channel"] = interaction.channel_id

        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

        await interaction.response.send_message(f"このチャンネル({interaction.channel.name})を時報チャンネルに設定しました", ephemeral=True)

def setup_admin_commands(bot):
    """Adminコマンドグループを登録"""
    # 既存のadminコマンドと重複しないように登録
    if not any(cmd.name == "admin" for cmd in bot.tree.get_commands()):
        bot.tree.add_command(AdminCommands())
