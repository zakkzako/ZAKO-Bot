import discord
import os
import sys
import asyncio
import jst
import logging

logger = logging.getLogger(__name__)

JST = jst.get_jst()

class RestartConfirmation(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.message: discord.Message = None

    async def on_timeout(self):
        if self.message:
            if self.children:
                for item in self.children:
                    item.disabled = True
            await self.message.edit(content="~~本当に再起動しますか？~~\n-# タイムアウトしました。再度コマンドを実行してください。", view=self)

    @discord.ui.button(label="続行", style=discord.ButtonStyle.red, custom_id="admin_restart_continue")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.edit_original_response("再起動を開始しました\n-# このプロセスは終了しますが、ホスト環境によっては自動で再起動されない場合があります。その場合は手動で再起動してください。", ephemeral=True)
        try:
            await interaction.client.close()
        except Exception as e:
            logger.error(f"An error occurred while closing the client, but the restart will continue.\nError: {e}")
        asyncio.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.gray, custom_id="admin_restart_cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.detede_original_response()
        self.stop()
