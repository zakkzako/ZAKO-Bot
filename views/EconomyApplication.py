import discord
import core_system


"""TC = TakasumiBOT Coin"""


class TC_to_EC(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    # TC -> EC
    @discord.ui.button(custom_id="ec-application:exchange:to_ec:approve", label="承認", style=discord.ButtonStyle.green)
    async def ec_application_exchange_to_ec_approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await core_system.handle_economy_application_exchange_ec(self.bot, interaction, approved=True)
    @discord.ui.button(custom_id="ec-application:exchange:to_ec:reject", label="却下", style=discord.ButtonStyle.red)
    async def ec_application_exchange_to_ec_reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await core_system.handle_economy_application_exchange_ec(self.bot, interaction, approved=False)


class EC_to_TC(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    # EC -> TC
    @discord.ui.button(custom_id="ec-application:exchange:to_tc:approve", label="承認", style=discord.ButtonStyle.green)
    async def ec_application_exchange_to_tc_approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await core_system.handle_economy_application_exchange_tc(self.bot, interaction, approved=True)
    @discord.ui.button(custom_id="ec-application:exchange:to_tc:reject", label="却下", style=discord.ButtonStyle.red)
    async def ec_application_exchange_to_tc_reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await core_system.handle_economy_application_exchange_tc(self.bot, interaction, approved=False)
