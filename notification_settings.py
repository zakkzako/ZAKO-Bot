import discord
from discord import app_commands
import json
import os
import logging

logger = logging.getLogger(__name__)

NOTIFICATION_SETTINGS_FILE = "notification_settings.json"

class NotificationSettingsView(discord.ui.View):
    """通知設定用のUI"""
    
    def __init__(self, user_id: int, current_settings: dict):
        super().__init__(timeout=300)  # 5分でタイムアウト
        self.user_id = user_id
        self.settings = current_settings.copy()
        self.is_modified = False
    
    def load_settings(user_id: int) -> dict:
        """ユーザーの通知設定を読み込む"""
        if not os.path.exists(NOTIFICATION_SETTINGS_FILE):
            return {
                'work': True,
                'external_work': True,
                'unemployment_insurance': True,
                'steal': True
            }
        
        with open(NOTIFICATION_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            try:
                all_settings = json.load(f)
                user_settings = all_settings.get(str(user_id), {})
                # デフォルト値で埋める
                return {
                    'work': user_settings.get('work', True),
                    'external_work': user_settings.get('external_work', True),
                    'unemployment_insurance': user_settings.get('unemployment_insurance', True),
                    'steal': user_settings.get('steal', True)
                }
            except json.JSONDecodeError:
                return {
                    'work': True,
                    'external_work': True,
                    'unemployment_insurance': True,
                    'steal': True
                }
    
    def save_settings(user_id: int, settings: dict):
        """ユーザーの通知設定を保存"""
        all_settings = {}
        if os.path.exists(NOTIFICATION_SETTINGS_FILE):
            with open(NOTIFICATION_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                try:
                    all_settings = json.load(f)
                except json.JSONDecodeError:
                    all_settings = {}
        
        all_settings[str(user_id)] = settings
        
        with open(NOTIFICATION_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_settings, f, indent=4, ensure_ascii=False)
    
    def create_embed(self) -> discord.Embed:
        """現在の設定を表示するEmbedを作成"""
        embed = discord.Embed(
            title="📋 通知設定",
            description="各通知機能のON/OFFを切り替えます",
            color=0x3498db
        )
        
        status_symbols = {
            True: "✅ ON",
            False: "❌ OFF"
        }
        
        embed.add_field(
            name="👷 ZAKO-Bot Work通知",
            value=status_symbols[self.settings['work']],
            inline=True
        )
        embed.add_field(
            name="🔔 TakasumiBot work通知",
            value=status_symbols[self.settings['external_work']],
            inline=True
        )
        embed.add_field(
            name="💼 失業保険通知",
            value=status_symbols[self.settings['unemployment_insurance']],
            inline=True
        )
        embed.add_field(
            name="💰 steal通知",
            value=status_symbols[self.settings['steal']],
            inline=True
        )
        
        if self.is_modified:
            embed.set_footer(text="⚠️ コミットボタンで変更を保存してください")
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
    
    @discord.ui.button(label="💼 失業保険通知", style=discord.ButtonStyle.primary, custom_id="notify:toggle:unemployment")
    async def unemployment_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return
        
        self.settings['unemployment_insurance'] = not self.settings['unemployment_insurance']
        self.is_modified = True
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="💰 steal通知", style=discord.ButtonStyle.primary, custom_id="notify:toggle:steal")
    async def steal_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return
        
        self.settings['steal'] = not self.settings['steal']
        self.is_modified = True
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="💾 コミット", style=discord.ButtonStyle.success, custom_id="notify:commit")
    async def commit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("このボタンはあなたは操作できません", ephemeral=True)
            return
        
        NotificationSettingsView.save_settings(self.user_id, self.settings)
        self.is_modified = False
        
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        logger.info(f"ユーザー {self.user_id} が通知設定を保存しました: {self.settings}")

@app_commands.command(name="notification", description="通知機能のON/OFFを設定します")
async def notification_settings(interaction: discord.Interaction):
    """通知設定コマンド"""
    user_id = interaction.user.id
    settings = NotificationSettingsView.load_settings(user_id)
    view = NotificationSettingsView(user_id, settings)
    
    await interaction.response.send_message(
        embed=view.create_embed(),
        view=view,
        ephemeral=True
    )

def setup_notification_commands(bot):
    """Botにコマンドを登録"""
    bot.tree.add_command(notification_settings)