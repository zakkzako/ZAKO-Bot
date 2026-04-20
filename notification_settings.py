import discord
from discord import app_commands
import logging
import database

logger = logging.getLogger(__name__)

class NotificationSettingsView(discord.ui.View):
    """通知設定用のUI"""

    def __init__(self, user_id: int, current_settings: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.settings = current_settings.copy()
        self.is_modified = False

    @staticmethod
    async def load_settings(user_id: int) -> dict:
        """ユーザーの通知設定をDBから読み込む"""
        row = await database.fetch_one("SELECT * FROM notification_settings WHERE user_id = ?", (user_id,))

        if row:
            return {
                'work': bool(row['work']),
                'external_work': bool(row['external_work']),
                'unemployment_insurance': bool(row['unemployment_insurance']),
                'steal': bool(row['steal'])
            }
        else:
            # データがない場合はすべてTrue(ON)を返す
            return {
                'work': True,
                'external_work': True,
                'unemployment_insurance': True,
                'steal': True
            }

    @staticmethod
    async def save_settings(user_id: int, settings: dict):
        """ユーザーの通知設定をDBに保存"""
        query = """
            INSERT OR REPLACE INTO notification_settings
            (user_id, work, external_work, unemployment_insurance, steal)
            VALUES (?, ?, ?, ?, ?)
        """
        await database.execute_query(query, (
            user_id,
            int(settings['work']),
            int(settings['external_work']),
            int(settings['unemployment_insurance']),
            int(settings['steal']),
        ))

    def create_embed(self) -> discord.Embed:
        """現在の設定を表示するEmbedを作成"""
        embed = discord.Embed(
            title="通知設定",
            description="各通知機能のON/OFFを切り替えます",
            color=0x3498db
        )

        status_symbols = {
            True: "✅ ON",
            False: "❌ OFF"
        }

        embed.add_field(
            name="ZAKO-Bot Work通知",
            value=status_symbols[self.settings['work']],
            inline=True
        )
        embed.add_field(
            name="TakasumiBot work通知",
            value=status_symbols[self.settings['external_work']],
            inline=True
        )
        embed.add_field(
            name="失業保険通知",
            value=status_symbols[self.settings['unemployment_insurance']],
            inline=True
        )
        embed.add_field(
            name="steal通知",
            value=status_symbols[self.settings['steal']],
            inline=True
        )

        if self.is_modified:
            embed.set_footer(text=" 「変更を保存」ボタンを押して変更を保存してください")
        else:
            embed.set_footer(text="ボタンをクリックしてON/OFFを切り替えてください")

        return embed

    @discord.ui.button(label="ZAKO-Bot Work通知", style=discord.ButtonStyle.primary, custom_id="notify:toggle:work")
    async def work_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return

        self.settings['work'] = not self.settings['work']
        self.is_modified = True
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="TakasumiBot work通知", style=discord.ButtonStyle.primary, custom_id="notify:toggle:external_work")
    async def external_work_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return

        self.settings['external_work'] = not self.settings['external_work']
        self.is_modified = True
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="失業保険通知", style=discord.ButtonStyle.primary, custom_id="notify:toggle:unemployment")
    async def unemployment_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return

        self.settings['unemployment_insurance'] = not self.settings['unemployment_insurance']
        self.is_modified = True
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="steal通知", style=discord.ButtonStyle.primary, custom_id="notify:toggle:steal")
    async def steal_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return

        self.settings['steal'] = not self.settings['steal']
        self.is_modified = True
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="変更を保存", style=discord.ButtonStyle.success, custom_id="notify:commit")
    async def commit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return

        await NotificationSettingsView.save_settings(self.user_id, self.settings)
        self.is_modified = False

        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        logger.info(f"ユーザー {self.user_id} が通知設定を保存しました: {self.settings}")

@app_commands.command(name="notification", description="通知機能のON/OFFを設定します")
async def notification_settings(interaction: discord.Interaction):
    """通知設定コマンド"""
    user_id = interaction.user.id
    settings = await NotificationSettingsView.load_settings(user_id)
    view = NotificationSettingsView(user_id, settings)

    await interaction.response.send_message(
        embed=view.create_embed(),
        view=view,
        ephemeral=True
    )

def setup_notification_commands(bot):
    """Botにコマンドを登録"""
    existing = [cmd.name for cmd in bot.tree.get_commands()]
    cmds = [notification_settings]
    for cmd in cmds:
        if cmd.name not in existing:
            bot.tree.add_command(cmd)
