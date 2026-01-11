import discord
from discord import app_commands
import blackjack
import economy
import datetime
import pytz

JST = pytz.timezone('Asia/Tokyo')

class BlackjackView(discord.ui.View):
    def __init__(self, user, amount, deck, p_hand, d_hand):
        super().__init__(timeout=120)
        self.user = user
        self.amount = amount
        self.deck = deck
        self.hands = [p_hand]  # 手札のリスト（スプリットで増える）
        self.current_hand_index = 0
        self.dealer_hand = d_hand
        self.is_finished = False
        self.is_doubled = [False] # 手札ごとのダブルダウンフラグ
        
        # 初期ボタン状態の更新
        self.update_buttons()

    def update_buttons(self):
        # スプリット可能か（初手2枚が同じ数字、かつ所持金がある）
        can_split = (len(self.hands) == 1 and len(self.hands[0]) == 2 and 
                     self.hands[0][0]['rank'] == self.hands[0][1]['rank'])
        self.split_button.disabled = not can_split
        # ダブルダウンは各手の初手のみ
        self.double_button.disabled = len(self.hands[self.current_hand_index]) != 2

    def create_embed(self):
        embed = discord.Embed(title="♠️ ブラックジャック", color=0x2ecc71)
        
        for i, hand in enumerate(self.hands):
            score = blackjack.calculate_score(hand)
            prefix = "▶️ " if i == self.current_hand_index and not self.is_finished else ""
            status = " (バースト)" if score > 21 else ""
            embed.add_field(
                name=f"{prefix}あなたの手札 {i+1 if len(self.hands)>1 else ''} ({score}){status}",
                value=blackjack.format_hand(hand), inline=False
            )

        d_score = blackjack.calculate_score(self.dealer_hand)
        d_val = blackjack.format_hand(self.dealer_hand) if self.is_finished else f"{blackjack.format_hand([self.dealer_hand[0]])} `??`"
        d_label = f"({d_score})" if self.is_finished else ""
        embed.add_field(name=f"ディーラーの手札 {d_label}", value=d_val, inline=False)
        
        if not self.is_finished:
            embed.set_footer(text=f"賭け金: {self.amount} EC / 操作を選択してください")
        return embed

    async def finish_all(self, interaction):
        self.is_finished = True
        # ディーラーのターン（全手がバーストしていない場合のみ）
        if any(blackjack.calculate_score(h) <= 21 for h in self.hands):
            while blackjack.calculate_score(self.dealer_hand) < 17:
                self.dealer_hand.append(self.deck.pop())
        
        d_score = blackjack.calculate_score(self.dealer_hand)
        total_change = 0
        results = []

        users = economy.load_json("users.json", {})
        
        for i, hand in enumerate(self.hands):
            p_score = blackjack.calculate_score(hand)
            bet = self.amount * (2 if self.is_doubled[i] else 1)
            
            if p_score > 21:
                res, change, r_type = "敗北 (バースト)", -bet, 'loss'
            elif d_score > 21 or p_score > d_score:
                res, change, r_type = "勝利！", bet, 'win'
            elif p_score < d_score:
                res, change, r_type = "敗北", -bet, 'loss'
            else:
                res, change, r_type = "引き分け", 0, 'draw'
            
            total_change += change
            results.append(f"手札{i+1}: {res}")
            blackjack.save_result(self.user.id, r_type, change)

        users[str(self.user.id)]["balance"] += total_change
        economy.save_json("users.json", users)

        embed = self.create_embed()
        embed.description = "\n".join(results) + f"\n\n**トータル収支: {total_change:+.2f} EC**"
        embed.color = 0xe74c3c if total_change < 0 else 0xf1c40f if total_change > 0 else 0x95a5a6
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id: return
        
        hand = self.hands[self.current_hand_index]
        hand.append(self.deck.pop())
        
        if blackjack.calculate_score(hand) >= 21:
            await self.next_hand(interaction)
        else:
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id: return
        await self.next_hand(interaction)

    @discord.ui.button(label="Double", style=discord.ButtonStyle.danger)
    async def double_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id: return
        
        # 資金チェック（追加分が必要）
        users = economy.load_json("users.json", {})
        if users.get(str(self.user.id), {}).get("balance", 0) < self.amount:
            return await interaction.response.send_message("ダブルダウン用の追加ECが足りません。", ephemeral=True)
        
        self.is_doubled[self.current_hand_index] = True
        self.hands[self.current_hand_index].append(self.deck.pop())
        await self.next_hand(interaction)

    @discord.ui.button(label="Split", style=discord.ButtonStyle.success)
    async def split_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id: return
        
        users = economy.load_json("users.json", {})
        if users.get(str(self.user.id), {}).get("balance", 0) < self.amount:
            return await interaction.response.send_message("スプリット用の追加ECが足りません。", ephemeral=True)

        # 手札を分割
        card = self.hands[0].pop()
        self.hands.append([card])
        self.is_doubled.append(False)
        # それぞれに1枚ずつ補充
        self.hands[0].append(self.deck.pop())
        self.hands[1].append(self.deck.pop())
        
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def next_hand(self, interaction):
        self.current_hand_index += 1
        if self.current_hand_index >= len(self.hands):
            await self.finish_all(interaction)
        else:
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

@app_commands.command(name="blackjack", description="ECを賭けてブラックジャックをプレイします")
async def bj_start(interaction: discord.Interaction, amount: float):
    if amount <= 0: return await interaction.response.send_message("金額が正しくありません。", ephemeral=True)
    
    users = economy.load_json("users.json", {})
    balance = users.get(str(interaction.user.id), {}).get("balance", 0.0)
    if balance < amount:
        return await interaction.response.send_message("ECが足りません。", ephemeral=True)

    deck = blackjack.get_deck()
    p_hand = [deck.pop(), deck.pop()]
    d_hand = [deck.pop(), deck.pop()]
    
    view = BlackjackView(interaction.user, amount, deck, p_hand, d_hand)
    await interaction.response.send_message(embed=view.create_embed(), view=view)

def setup_gambling_commands(bot):
    bot.tree.add_command(bj_start)
