"""
ヘルパー関数
共通で使用される便利な関数群

作成者: [Your Name]
作成日: 2025-07-31
"""

import discord
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import re
import asyncio

from database.database import mark_reminder_sent

logger = logging.getLogger(__name__)

# ------------------------------
# 音量設定の永続化関連
# ------------------------------
import json
from pathlib import Path

VOLUME_SETTINGS_FILE = Path(__file__).resolve().parent.parent / 'volume_settings.json'

def load_volume_setting(guild_id: int):
    """ギルドの音量設定を読み込む。存在しなければ None を返す"""
    try:
        if not VOLUME_SETTINGS_FILE.exists():
            return None
        with VOLUME_SETTINGS_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
        value = data.get(str(guild_id))
        if value is None:
            return None
        return float(value)
    except Exception as e:
        logger.error(f"音量設定読み込みエラー: {e}")
        return None

def save_volume_setting(guild_id: int, volume: float) -> None:
    """ギルドの音量設定を保存する"""
    try:
        if VOLUME_SETTINGS_FILE.exists():
            with VOLUME_SETTINGS_FILE.open('r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        data[str(guild_id)] = float(volume)
        with VOLUME_SETTINGS_FILE.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"音量設定保存エラー: {e}")


def parse_datetime_string(date_str: str, time_str: Optional[str] = None) -> Optional[datetime]:
    """
    日付・時間文字列をdatetimeオブジェクトに変換
    
    Args:
        date_str: 日付文字列 (例: "2025-07-31", "7/31", "明日")
        time_str: 時間文字列 (例: "14:30", "2:30PM")
    
    Returns:
        datetimeオブジェクト（解析に失敗した場合はNone）
    """
    try:
        now = datetime.now()
        
        # 相対的な日付の処理
        if date_str.lower() in ['今日', 'today']:
            target_date = now.date()
        elif date_str.lower() in ['明日', 'tomorrow']:
            target_date = (now + timedelta(days=1)).date()
        elif date_str.lower() in ['明後日']:
            target_date = (now + timedelta(days=2)).date()
        else:
            # 絶対的な日付の解析
            # YYYY-MM-DD形式
            if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str):
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            # MM/DD形式（今年として処理）
            elif re.match(r'^\d{1,2}/\d{1,2}$', date_str):
                month, day = map(int, date_str.split('/'))
                target_date = datetime(now.year, month, day).date()
                # 過去の日付の場合、来年として処理
                if target_date < now.date():
                    target_date = datetime(now.year + 1, month, day).date()
            # MM-DD形式
            elif re.match(r'^\d{1,2}-\d{1,2}$', date_str):
                month, day = map(int, date_str.split('-'))
                target_date = datetime(now.year, month, day).date()
                if target_date < now.date():
                    target_date = datetime(now.year + 1, month, day).date()
            else:
                logger.warning(f"不正な日付形式: {date_str}")
                return None
        
        # 時間の処理
        if time_str:
            # HH:MM形式
            if re.match(r'^\d{1,2}:\d{2}$', time_str):
                hour, minute = map(int, time_str.split(':'))
            # HH:MM AM/PM形式
            elif re.match(r'^\d{1,2}:\d{2}\s*(AM|PM)$', time_str.upper()):
                time_part, period = time_str.upper().split()
                hour, minute = map(int, time_part.split(':'))
                if period == 'PM' and hour != 12:
                    hour += 12
                elif period == 'AM' and hour == 12:
                    hour = 0
            # HH AM/PM形式
            elif re.match(r'^\d{1,2}\s*(AM|PM)$', time_str.upper()):
                hour_part, period = time_str.upper().split()
                hour = int(hour_part)
                minute = 0
                if period == 'PM' and hour != 12:
                    hour += 12
                elif period == 'AM' and hour == 12:
                    hour = 0
            else:
                logger.warning(f"不正な時間形式: {time_str}")
                return None
        else:
            # 時間が指定されていない場合はデフォルト（9:00）
            hour, minute = 9, 0
        
        return datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute))
        
    except Exception as e:
        logger.error(f"日時解析エラー: {e}")
        return None

def format_datetime_for_discord(dt: datetime) -> str:
    """
    Discordのタイムスタンプフォーマットでdatetimeを表示
    
    Args:
        dt: datetimeオブジェクト
    
    Returns:
        Discord形式のタイムスタンプ文字列
    """
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:F>"  # Full date & time

def format_relative_time_for_discord(dt: datetime) -> str:
    """
    Discord形式の相対時間表示
    
    Args:
        dt: datetimeオブジェクト
    
    Returns:
        Discord形式の相対時間文字列
    """
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:R>"  # Relative time (e.g., "in 2 hours")

def create_error_embed(title: str, description: str, color: int = 0xff0000) -> discord.Embed:
    """
    エラー用のEmbed作成
    
    Args:
        title: エラータイトル
        description: エラーの説明
        color: Embedの色（デフォルト：赤）
    
    Returns:
        エラー用Embedオブジェクト
    """
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=color
    )
    embed.set_footer(text="エラーが継続する場合は管理者にお問い合わせください")
    return embed

def create_success_embed(title: str, description: str, color: int = 0x00ff00) -> discord.Embed:
    """
    成功用のEmbed作成
    
    Args:
        title: タイトル
        description: 説明
        color: Embedの色（デフォルト：緑）
    
    Returns:
        成功用Embedオブジェクト
    """
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=color
    )
    return embed

def create_info_embed(title: str, description: str, color: int = 0x0099ff) -> discord.Embed:
    """
    情報用のEmbed作成
    
    Args:
        title: タイトル
        description: 説明
        color: Embedの色（デフォルト：青）
    
    Returns:
        情報用Embedオブジェクト
    """
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=color
    )
    return embed

def create_schedule_embed(schedule: 'Schedule', show_user: bool = True) -> discord.Embed:
    """
    予定用のEmbed作成
    
    Args:
        schedule: 予定オブジェクト
        show_user: ユーザー情報を表示するか
    
    Returns:
        予定用Embedオブジェクト
    """
    embed = discord.Embed(
        title=f"📅 {schedule.title}",
        color=0x00ff99
    )
    
    # 開始日時
    embed.add_field(
        name="開始日時",
        value=format_datetime_for_discord(schedule.start_datetime),
        inline=True
    )
    
    # 終了日時（あれば）
    if schedule.end_datetime:
        embed.add_field(
            name="終了日時",
            value=format_datetime_for_discord(schedule.end_datetime),
            inline=True
        )
    
    # 説明（あれば）
    if schedule.description:
        embed.add_field(
            name="詳細",
            value=schedule.description,
            inline=False
        )
    
    # ユーザー情報
    if show_user:
        embed.add_field(
            name="作成者",
            value=f"<@{schedule.user_id}>",
            inline=True
        )
    
    # 予定ID（小さく表示）
    embed.set_footer(text=f"予定ID: {schedule.id}")
    
    return embed

async def send_reminder(bot, reminder_data: Dict[str, Any]) -> bool:
    """
    リマインダーを送信
    
    Args:
        bot: BOTインスタンス
        reminder_data: リマインダーデータ
    
    Returns:
        送信成功の可否
    """
    try:
        # チャンネルの取得
        channel = bot.get_channel(int(reminder_data['channel_id']))
        if not channel:
            logger.error(f"チャンネルが見つかりません: {reminder_data['channel_id']}")
            return False
        
        # リマインダーEmbed作成
        embed = discord.Embed(
            title="🔔 予定のリマインダー",
            color=0xffa500
        )
        
        embed.add_field(
            name="予定",
            value=reminder_data['title'],
            inline=False
        )
        
        embed.add_field(
            name="開始時刻",
            value=format_datetime_for_discord(reminder_data['start_datetime']),
            inline=True
        )
        
        embed.add_field(
            name="残り時間",
            value=format_relative_time_for_discord(reminder_data['start_datetime']),
            inline=True
        )
        
        # カスタムメッセージがあれば追加
        if reminder_data.get('message'):
            embed.add_field(
                name="メッセージ",
                value=reminder_data['message'],
                inline=False
            )
        
        # ユーザーへのメンション
        content = f"<@{reminder_data['user_id']}>"
        
        # メッセージ送信
        await channel.send(content=content, embed=embed)
        
        # 送信済みにマーク
        await mark_reminder_sent(reminder_data['id'])
        
        logger.info(f"リマインダーを送信しました: {reminder_data['title']}")
        return True
        
    except Exception as e:
        logger.error(f"リマインダー送信エラー: {e}")
        return False

def parse_reminder_time(time_str: str) -> Optional[timedelta]:
    """
    リマインダー時間文字列を解析してtimedeltaに変換
    
    Args:
        time_str: 時間文字列 (例: "30分", "1時間", "1日")
    
    Returns:
        timedeltaオブジェクト（解析に失敗した場合はNone）
    """
    try:
        # 数値を抽出
        match = re.search(r'(\d+)', time_str)
        if not match:
            return None
        
        number = int(match.group(1))
        
        # 単位の判定
        if '分' in time_str or 'min' in time_str.lower():
            return timedelta(minutes=number)
        elif '時間' in time_str or 'hour' in time_str.lower() or 'h' in time_str.lower():
            return timedelta(hours=number)
        elif '日' in time_str or 'day' in time_str.lower() or 'd' in time_str.lower():
            return timedelta(days=number)
        else:
            return None
            
    except Exception as e:
        logger.error(f"リマインダー時間解析エラー: {e}")
        return None

def split_long_message(message: str, max_length: int = 2000) -> List[str]:
    """
    長いメッセージを分割
    
    Args:
        message: 分割するメッセージ
        max_length: 最大文字数
    
    Returns:
        分割されたメッセージのリスト
    """
    if len(message) <= max_length:
        return [message]
    
    parts = []
    current_part = ""
    
    for line in message.split('\n'):
        if len(current_part) + len(line) + 1 <= max_length:
            if current_part:
                current_part += '\n'
            current_part += line
        else:
            if current_part:
                parts.append(current_part)
            current_part = line
    
    if current_part:
        parts.append(current_part)
    
    return parts

def validate_youtube_url(url: str) -> bool:
    """
    YouTube URLの妥当性をチェック
    
    Args:
        url: チェックするURL
    
    Returns:
        有効なYouTube URLかどうか
    """
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+',
        r'https?://youtu\.be/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
    ]
    
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def get_user_display_name(user: discord.User) -> str:
    """
    ユーザーの表示名を取得（サーバーニックネーム優先）
    
    Args:
        user: ユーザーオブジェクト
    
    Returns:
        表示名
    """
    if hasattr(user, 'display_name'):
        return user.display_name
    return user.global_name or user.name

async def confirm_action(
    interaction: discord.Interaction,
    title: str,
    description: str,
    timeout: int = 30
) -> bool:
    """
    アクション実行の確認ダイアログ
    
    Args:
        interaction: インタラクション
        title: 確認タイトル
        description: 確認メッセージ
        timeout: タイムアウト時間（秒）
    
    Returns:
        ユーザーが確認したかどうか
    """
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=timeout)
            self.value = None
        
        @discord.ui.button(label='はい', style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = True
            self.stop()
        
        @discord.ui.button(label='いいえ', style=discord.ButtonStyle.red)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = False
            self.stop()
    
    embed = create_info_embed(title, description)
    view = ConfirmView()
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    # タイムアウト待ち
    await view.wait()
    
    return view.value or False
