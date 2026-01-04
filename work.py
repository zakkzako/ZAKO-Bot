import discord
import datetime
import pytz
import requests
import json
import os

JST = pytz.timezone('Asia/Tokyo')

# 職業とクールタイムの定義
JOB_MAP = {
    "none": {"name": "無職", "time": 10},
    "gambler": {"name": "ギャンブラー", "time": 10},
    "chick_taxonomist": {"name": "ひよこ鑑定士", "time": 10},
    "freeter": {"name": "フリーター", "time": 15},
    "farmer": {"name": "農家", "time": 20},
    "influencer": {"name": "インフルエンサー", "time": 5},
    "architect": {"name": "建築家", "time": 45},
    "investor": {"name": "投資家", "time": 30},
    "engineer": {"name": "エンジニア", "time": 60},
    "doctor": {"name": "医師", "time": 60}
}

async def handle_work_detection(bot, message, embed):
    """work検知時のメインロジック"""
    now = datetime.datetime.now(JST)
    
    # ユーザー特定（Interaction または メンション）
    user_id = None
    if message.interaction:
        user_id = message
