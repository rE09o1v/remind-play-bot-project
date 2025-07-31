"""
カレンダー表示機能
予定をカレンダー形式で表示するためのユーティリティ

作成者: [Your Name]
作成日: 2025-07-31
"""

import discord
import calendar
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from database.models import Schedule
from .helpers import format_datetime_for_discord, get_user_display_name

logger = logging.getLogger(__name__)

class CalendarView:
    """
    カレンダー表示用のクラス
    """
    
    def __init__(self, year: int, month: int, schedules: List[Schedule]):
        self.year = year
        self.month = month
        self.schedules = schedules
        self.schedule_map = self._create_schedule_map()
    
    def _create_schedule_map(self) -> Dict[int, List[Schedule]]:
        """
        日付ごとの予定マップを作成
        
        Returns:
            {日: [予定リスト]} の辞書
        """
        schedule_map = {}
        
        for schedule in self.schedules:
            # 該当月の予定のみ処理
            if (schedule.start_datetime.year == self.year and 
                schedule.start_datetime.month == self.month):
                
                day = schedule.start_datetime.day
                if day not in schedule_map:
                    schedule_map[day] = []
                schedule_map[day].append(schedule)
        
        return schedule_map
    
    def create_embed(self, show_details: bool = True) -> discord.Embed:
        """
        カレンダーEmbedを作成
        
        Args:
            show_details: 詳細な予定情報を表示するか
        
        Returns:
            カレンダーEmbed
        """
        # 月名の取得
        month_names = [
            "1月", "2月", "3月", "4月", "5月", "6月",
            "7月", "8月", "9月", "10月", "11月", "12月"
        ]
        
        embed = discord.Embed(
            title=f"📅 {self.year}年 {month_names[self.month - 1]} のカレンダー",
            color=0x00ff99
        )
        
        # カレンダーグリッドの作成
        calendar_text = self._create_calendar_grid()
        embed.add_field(
            name="カレンダー",
            value=f"```\n{calendar_text}\n```",
            inline=False
        )
        
        # 予定の詳細表示
        if show_details and self.schedules:
            details_text = self._create_schedule_details()
            
            # 長すぎる場合は分割
            if len(details_text) > 1024:
                details_parts = self._split_schedule_details(details_text)
                for i, part in enumerate(details_parts):
                    field_name = "予定詳細" if i == 0 else f"予定詳細 (続き{i})"
                    embed.add_field(
                        name=field_name,
                        value=part,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="予定詳細",
                    value=details_text,
                    inline=False
                )
        
        # 統計情報
        total_schedules = len(self.schedules)
        scheduled_days = len(self.schedule_map)
        
        embed.set_footer(
            text=f"総予定数: {total_schedules}件 | 予定のある日: {scheduled_days}日"
        )
        
        return embed
    
    def _create_calendar_grid(self) -> str:
        """
        カレンダーグリッドのテキストを作成
        
        Returns:
            カレンダーグリッドの文字列
        """
        # 曜日ヘッダー
        header = "日 月 火 水 木 金 土"
        lines = [header, "=" * len(header)]
        
        # カレンダーの生成
        cal = calendar.monthcalendar(self.year, self.month)
        
        for week in cal:
            week_line = ""
            for day in week:
                if day == 0:
                    # 前月/次月の日付
                    week_line += "   "
                else:
                    # 予定がある日にはマーク付き
                    if day in self.schedule_map:
                        week_line += f"{day:2}*"
                    else:
                        week_line += f"{day:2} "
            lines.append(week_line)
        
        lines.append("")
        lines.append("* 予定のある日")
        
        return "\n".join(lines)
    
    def _create_schedule_details(self) -> str:
        """
        予定詳細のテキストを作成
        
        Returns:
            予定詳細の文字列
        """
        details = []
        
        # 日付順にソート
        sorted_days = sorted(self.schedule_map.keys())
        
        for day in sorted_days:
            day_schedules = sorted(
                self.schedule_map[day],
                key=lambda s: s.start_datetime
            )
            
            details.append(f"**{day}日**")
            
            for schedule in day_schedules:
                # 時間表示
                time_str = schedule.start_datetime.strftime("%H:%M")
                if schedule.end_datetime:
                    end_time_str = schedule.end_datetime.strftime("%H:%M")
                    time_str += f"-{end_time_str}"
                
                # 予定の詳細
                detail_line = f"  {time_str} {schedule.title}"
                
                # 長すぎる場合は省略
                if len(detail_line) > 80:
                    detail_line = detail_line[:77] + "..."
                
                details.append(detail_line)
            
            details.append("")  # 空行
        
        return "\n".join(details)
    
    def _split_schedule_details(self, details: str) -> List[str]:
        """
        予定詳細を複数のフィールドに分割
        
        Args:
            details: 分割する詳細文字列
        
        Returns:
            分割された詳細文字列のリスト
        """
        lines = details.split('\n')
        parts = []
        current_part = ""
        
        for line in lines:
            if len(current_part) + len(line) + 1 <= 1024:
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

class CalendarNavigationView(discord.ui.View):
    """
    カレンダーナビゲーション用のView
    """
    
    def __init__(self, user_id: str, guild_id: str, year: int, month: int, show_all: bool = False):
        super().__init__(timeout=300)  # 5分でタイムアウト
        self.user_id = user_id
        self.guild_id = guild_id
        self.year = year
        self.month = month
        self.show_all = show_all  # 全員の予定を表示するか
        
        # 現在の月に基づいてボタンの無効化
        current_date = datetime.now()
        if (year == current_date.year - 1 and month == 1) or year < current_date.year - 1:
            self.prev_button.disabled = True
        if (year == current_date.year + 1 and month == 12) or year > current_date.year + 1:
            self.next_button.disabled = True
    
    @discord.ui.button(label='◀ 前月', style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """前月に移動"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
            return
        
        # 前月の計算
        if self.month == 1:
            self.year -= 1
            self.month = 12
        else:
            self.month -= 1
        
        await self._update_calendar(interaction)
    
    @discord.ui.button(label='今月', style=discord.ButtonStyle.primary)
    async def current_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """今月に移動"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
            return
        
        current_date = datetime.now()
        self.year = current_date.year
        self.month = current_date.month
        
        await self._update_calendar(interaction)
    
    @discord.ui.button(label='次月 ▶', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """次月に移動"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
            return
        
        # 次月の計算
        if self.month == 12:
            self.year += 1
            self.month = 1
        else:
            self.month += 1
        
        await self._update_calendar(interaction)
    
    @discord.ui.button(label='表示切替', style=discord.ButtonStyle.success)
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """表示切替（個人/全員）"""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message("このボタンは使用できません。", ephemeral=True)
            return
        
        self.show_all = not self.show_all
        await self._update_calendar(interaction)
    
    async def _update_calendar(self, interaction: discord.Interaction):
        """カレンダー表示を更新"""
        try:
            from database.database import get_schedules_by_user, get_schedules_by_guild
            
            # 月の開始・終了日時を計算
            start_date = datetime(self.year, self.month, 1)
            if self.month == 12:
                end_date = datetime(self.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(self.year, self.month + 1, 1) - timedelta(seconds=1)
            
            # 予定の取得
            if self.show_all:
                schedules = await get_schedules_by_guild(
                    self.guild_id,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                schedules = await get_schedules_by_user(
                    self.user_id,
                    self.guild_id,
                    start_date=start_date,
                    end_date=end_date
                )
            
            # カレンダービューの作成
            calendar_view = CalendarView(self.year, self.month, schedules)
            embed = calendar_view.create_embed()
            
            # 表示モードの表示
            mode_text = "全員の予定" if self.show_all else "あなたの予定"
            embed.description = f"表示モード: {mode_text}"
            
            # ボタンの更新
            current_date = datetime.now()
            self.prev_button.disabled = (
                (self.year == current_date.year - 1 and self.month == 1) or 
                self.year < current_date.year - 1
            )
            self.next_button.disabled = (
                (self.year == current_date.year + 1 and self.month == 12) or 
                self.year > current_date.year + 1
            )
            
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"カレンダー更新エラー: {e}")
            await interaction.response.send_message(
                "カレンダーの更新中にエラーが発生しました。",
                ephemeral=True
            )

def create_month_calendar(
    year: int,
    month: int,
    schedules: List[Schedule],
    user_id: str,
    guild_id: str,
    show_all: bool = False
) -> tuple[discord.Embed, CalendarNavigationView]:
    """
    月次カレンダーの作成
    
    Args:
        year: 年
        month: 月
        schedules: 予定リスト
        user_id: ユーザーID
        guild_id: サーバーID
        show_all: 全員の予定を表示するか
    
    Returns:
        (Embed, View)のタプル
    """
    # カレンダービューの作成
    calendar_view = CalendarView(year, month, schedules)
    embed = calendar_view.create_embed()
    
    # 表示モードの表示
    mode_text = "全員の予定" if show_all else "あなたの予定"
    embed.description = f"表示モード: {mode_text}"
    
    # ナビゲーションビューの作成
    nav_view = CalendarNavigationView(user_id, guild_id, year, month, show_all)
    
    return embed, nav_view

def create_week_view(
    start_date: datetime,
    schedules: List[Schedule]
) -> discord.Embed:
    """
    週次ビューの作成
    
    Args:
        start_date: 週の開始日（月曜日）
        schedules: 予定リスト
    
    Returns:
        週次ビュー用のEmbed
    """
    # 週の終了日を計算
    end_date = start_date + timedelta(days=6)
    
    embed = discord.Embed(
        title=f"📅 週次予定 ({start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')})",
        color=0x00ff99
    )
    
    # 週の各日をチェック
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_schedules = [
            s for s in schedules
            if s.start_datetime.date() == current_date.date()
        ]
        
        # 日付とスケジュール
        day_title = f"{weekdays[i]}曜日 ({current_date.strftime('%m/%d')})"
        
        if day_schedules:
            # 時間順にソート
            day_schedules.sort(key=lambda s: s.start_datetime)
            
            schedule_list = []
            for schedule in day_schedules:
                time_str = schedule.start_datetime.strftime("%H:%M")
                if schedule.end_datetime:
                    end_time_str = schedule.end_datetime.strftime("%H:%M")
                    time_str += f"-{end_time_str}"
                
                schedule_list.append(f"{time_str} {schedule.title}")
            
            embed.add_field(
                name=day_title,
                value="\n".join(schedule_list),
                inline=True
            )
        else:
            embed.add_field(
                name=day_title,
                value="予定なし",
                inline=True
            )
    
    return embed
