"""
予定管理機能のCog
スラッシュコマンドによる予定のCRUD操作とカレンダー表示

作成者: [Your Name]
作成日: 2025-07-31
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timedelta
from typing import Optional, List
import asyncio
import json

from database.database import (
    create_schedule,
    get_schedule_by_id,
    get_schedules_by_user,
    get_schedules_by_guild,
    update_schedule,
    delete_schedule,
    create_reminder,
    create_bulk_schedules
)
from utils.helpers import (
    parse_datetime_string,
    create_error_embed,
    create_success_embed,
    create_info_embed,
    create_schedule_embed,
    parse_reminder_time,
    confirm_action
)
from utils.calendar_view import create_month_calendar, create_week_view

logger = logging.getLogger(__name__)

class ScheduleCog(commands.Cog):
    """
    予定管理機能を提供するCog
    """
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("予定管理Cogを初期化しました")
    
    @app_commands.command(name="schedule-add", description="新しい予定を追加します")
    @app_commands.describe(
        title="予定のタイトル",
        date="日付 (例: 2025-07-31, 7/31, 明日)",
        time="時間 (例: 14:30, 2:30PM) ※省略時は9:00",
        description="予定の詳細説明 (オプション)",
        end_time="終了時間 (オプション)"
    )
    async def add_schedule(
        self,
        interaction: discord.Interaction,
        title: str,
        date: str,
        time: Optional[str] = None,
        description: Optional[str] = None,
        end_time: Optional[str] = None
    ):
        """予定を追加"""
        try:
            await interaction.response.defer()
            
            # 日時の解析
            start_datetime = parse_datetime_string(date, time)
            if not start_datetime:
                embed = create_error_embed(
                    "日時解析エラー",
                    "日付・時間の形式が正しくありません。\n\n"
                    "**使用可能な形式:**\n"
                    "日付: `2025-07-31`, `7/31`, `明日`, `今日`\n"
                    "時間: `14:30`, `2:30PM`, `9AM`"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 終了時間の解析（指定されている場合）
            end_datetime = None
            if end_time:
                # 同じ日の終了時間として解析
                end_datetime = parse_datetime_string(date, end_time)
                if not end_datetime or end_datetime <= start_datetime:
                    embed = create_error_embed(
                        "終了時間エラー",
                        "終了時間は開始時間より後に設定してください。"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # 過去の日時チェック
            if start_datetime < datetime.now():
                embed = create_error_embed(
                    "日時エラー",
                    "過去の日時は指定できません。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 予定の作成
            schedule_id = await create_schedule(
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id),
                title=title,
                start_datetime=start_datetime,
                description=description,
                end_datetime=end_datetime
            )
            
            # 成功メッセージ
            embed = create_success_embed(
                "予定を追加しました",
                f"**{title}** の予定を追加しました。"
            )
            embed.add_field(
                name="開始日時",
                value=f"<t:{int(start_datetime.timestamp())}:F>",
                inline=True
            )
            if end_datetime:
                embed.add_field(
                    name="終了日時",
                    value=f"<t:{int(end_datetime.timestamp())}:F>",
                    inline=True
                )
            if description:
                embed.add_field(
                    name="詳細",
                    value=description,
                    inline=False
                )
            embed.set_footer(text=f"予定ID: {schedule_id}")
            
            await interaction.followup.send(embed=embed)
            logger.info(f"予定を追加: {title} (ユーザー: {interaction.user.id})")
            
        except Exception as e:
            logger.error(f"予定追加エラー: {e}")
            embed = create_error_embed(
                "予定追加失敗",
                "予定の追加中にエラーが発生しました。"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="schedule-list", description="予定一覧を表示します")
    @app_commands.describe(
        user="特定のユーザーの予定を表示 (オプション)",
        period="表示期間 (today, week, month)",
        show_all="全員の予定を表示するか"
    )
    @app_commands.choices(period=[
        app_commands.Choice(name="今日", value="today"),
        app_commands.Choice(name="今週", value="week"),
        app_commands.Choice(name="今月", value="month"),
        app_commands.Choice(name="全て", value="all")
    ])
    async def list_schedules(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        period: Optional[str] = "week",
        show_all: bool = False
    ):
        """予定一覧を表示"""
        try:
            await interaction.response.defer()
            
            # 対象ユーザーの決定
            target_user_id = str(user.id) if user else str(interaction.user.id)
            
            # 期間の計算
            now = datetime.now()
            start_date = None
            end_date = None
            
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1) - timedelta(seconds=1)
            elif period == "week":
                # 今週の月曜日から日曜日
                days_since_monday = now.weekday()
                start_date = now - timedelta(days=days_since_monday)
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7) - timedelta(seconds=1)
            elif period == "month":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
                end_date = next_month - timedelta(seconds=1)
            
            # 予定の取得
            if show_all:
                schedules = await get_schedules_by_guild(
                    str(interaction.guild.id),
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                schedules = await get_schedules_by_user(
                    target_user_id,
                    str(interaction.guild.id),
                    start_date=start_date,
                    end_date=end_date
                )
            
            # 結果の表示
            if not schedules:
                embed = create_info_embed(
                    "予定なし",
                    "指定された期間に予定はありません。"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 期間に応じた表示形式
            if period == "today":
                # 今日の予定をリスト表示
                embed = discord.Embed(
                    title="📅 今日の予定",
                    color=0x00ff99
                )
                
                for schedule in schedules:
                    embed.add_field(
                        name=f"{schedule.start_datetime.strftime('%H:%M')} {schedule.title}",
                        value=schedule.description or "詳細なし",
                        inline=False
                    )
            
            elif period == "week":
                # 週次ビュー
                embed = create_week_view(start_date, schedules)
            
            else:
                # 一覧表示
                embed = discord.Embed(
                    title=f"📅 予定一覧 ({len(schedules)}件)",
                    color=0x00ff99
                )
                
                for schedule in schedules[:10]:  # 最大10件表示
                    time_str = f"<t:{int(schedule.start_datetime.timestamp())}:F>"
                    embed.add_field(
                        name=schedule.title,
                        value=f"{time_str}\n{schedule.description or '詳細なし'}",
                        inline=False
                    )
                
                if len(schedules) > 10:
                    embed.set_footer(text=f"他に{len(schedules) - 10}件の予定があります")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"予定一覧エラー: {e}")
            embed = create_error_embed(
                "予定一覧取得失敗",
                "予定一覧の取得中にエラーが発生しました。"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="schedule-calendar", description="カレンダー形式で予定を表示します")
    @app_commands.describe(
        year="表示する年 (省略時は今年)",
        month="表示する月 (省略時は今月)",
        show_all="全員の予定を表示するか"
    )
    async def show_calendar(
        self,
        interaction: discord.Interaction,
        year: Optional[int] = None,
        month: Optional[int] = None,
        show_all: bool = False
    ):
        """カレンダー表示"""
        try:
            await interaction.response.defer()
            
            # デフォルト値の設定
            now = datetime.now()
            year = year or now.year
            month = month or now.month
            
            # 年月の妥当性チェック
            if not (2020 <= year <= 2030):
                embed = create_error_embed(
                    "年の範囲エラー",
                    "年は2020年から2030年の間で指定してください。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if not (1 <= month <= 12):
                embed = create_error_embed(
                    "月の範囲エラー",
                    "月は1から12の間で指定してください。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 月の開始・終了日時を計算
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            # 予定の取得
            if show_all:
                schedules = await get_schedules_by_guild(
                    str(interaction.guild.id),
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                schedules = await get_schedules_by_user(
                    str(interaction.user.id),
                    str(interaction.guild.id),
                    start_date=start_date,
                    end_date=end_date
                )
            
            # カレンダーの作成
            embed, view = create_month_calendar(
                year, month, schedules,
                str(interaction.user.id),
                str(interaction.guild.id),
                show_all
            )
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"カレンダー表示エラー: {e}")
            embed = create_error_embed(
                "カレンダー表示失敗",
                "カレンダーの表示中にエラーが発生しました。"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="schedule-edit", description="予定を編集します")
    @app_commands.describe(
        schedule_id="編集する予定のID",
        title="新しいタイトル (オプション)",
        date="新しい日付 (オプション)",
        time="新しい時間 (オプション)",
        description="新しい説明 (オプション)"
    )
    async def edit_schedule(
        self,
        interaction: discord.Interaction,
        schedule_id: int,
        title: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        description: Optional[str] = None
    ):
        """予定を編集"""
        try:
            await interaction.response.defer()
            
            # 予定の存在確認
            schedule = await get_schedule_by_id(schedule_id)
            if not schedule:
                embed = create_error_embed(
                    "予定が見つかりません",
                    f"ID {schedule_id} の予定は存在しません。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 権限チェック
            if schedule.user_id != str(interaction.user.id):
                embed = create_error_embed(
                    "権限エラー",
                    "他のユーザーの予定は編集できません。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 新しい日時の解析
            new_start_datetime = None
            if date or time:
                # 日付が指定されていない場合は元の日付を使用
                date_to_use = date or schedule.start_datetime.strftime('%Y-%m-%d')
                # 時間が指定されていない場合は元の時間を使用
                time_to_use = time or schedule.start_datetime.strftime('%H:%M')
                
                new_start_datetime = parse_datetime_string(date_to_use, time_to_use)
                if not new_start_datetime:
                    embed = create_error_embed(
                        "日時解析エラー",
                        "新しい日付・時間の形式が正しくありません。"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # 予定の更新
            success = await update_schedule(
                schedule_id=schedule_id,
                user_id=str(interaction.user.id),
                title=title,
                description=description,
                start_datetime=new_start_datetime
            )
            
            if success:
                embed = create_success_embed(
                    "予定を更新しました",
                    f"予定ID {schedule_id} を更新しました。"
                )
                await interaction.followup.send(embed=embed)
                logger.info(f"予定を更新: ID={schedule_id} (ユーザー: {interaction.user.id})")
            else:
                embed = create_error_embed(
                    "更新失敗",
                    "予定の更新に失敗しました。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"予定編集エラー: {e}")
            embed = create_error_embed(
                "予定編集失敗",
                "予定の編集中にエラーが発生しました。"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="schedule-delete", description="予定を削除します")
    @app_commands.describe(schedule_id="削除する予定のID")
    async def delete_schedule_cmd(
        self,
        interaction: discord.Interaction,
        schedule_id: int
    ):
        """予定を削除"""
        try:
            await interaction.response.defer()
            
            # 予定の存在確認
            schedule = await get_schedule_by_id(schedule_id)
            if not schedule:
                embed = create_error_embed(
                    "予定が見つかりません",
                    f"ID {schedule_id} の予定は存在しません。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 権限チェック
            if schedule.user_id != str(interaction.user.id):
                embed = create_error_embed(
                    "権限エラー",
                    "他のユーザーの予定は削除できません。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 削除確認
            confirm = await confirm_action(
                interaction,
                "予定削除の確認",
                f"**{schedule.title}** を削除してもよろしいですか？\n\n"
                f"開始日時: <t:{int(schedule.start_datetime.timestamp())}:F>"
            )
            
            if not confirm:
                embed = create_info_embed(
                    "削除キャンセル",
                    "予定の削除をキャンセルしました。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 予定の削除
            success = await delete_schedule(schedule_id, str(interaction.user.id))
            
            if success:
                embed = create_success_embed(
                    "予定を削除しました",
                    f"**{schedule.title}** を削除しました。"
                )
                await interaction.followup.send(embed=embed)
                logger.info(f"予定を削除: ID={schedule_id} (ユーザー: {interaction.user.id})")
            else:
                embed = create_error_embed(
                    "削除失敗",
                    "予定の削除に失敗しました。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"予定削除エラー: {e}")
            embed = create_error_embed(
                "予定削除失敗",
                "予定の削除中にエラーが発生しました。"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="schedule-remind", description="予定にリマインダーを設定します")
    @app_commands.describe(
        schedule_id="リマインダーを設定する予定のID",
        time_before="何分/時間/日前に通知するか (例: 30分, 1時間, 1日)",
        message="カスタムメッセージ (オプション)"
    )
    async def set_reminder(
        self,
        interaction: discord.Interaction,
        schedule_id: int,
        time_before: str,
        message: Optional[str] = None
    ):
        """リマインダー設定"""
        try:
            await interaction.response.defer()
            
            # 予定の存在確認
            schedule = await get_schedule_by_id(schedule_id)
            if not schedule:
                embed = create_error_embed(
                    "予定が見つかりません",
                    f"ID {schedule_id} の予定は存在しません。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 権限チェック
            if schedule.user_id != str(interaction.user.id):
                embed = create_error_embed(
                    "権限エラー",
                    "他のユーザーの予定にはリマインダーを設定できません。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 時間の解析
            time_delta = parse_reminder_time(time_before)
            if not time_delta:
                embed = create_error_embed(
                    "時間解析エラー",
                    "時間の形式が正しくありません。\n\n"
                    "**使用可能な形式:**\n"
                    "`30分`, `1時間`, `2日`, `30min`, `1hour`, `2days`"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # リマインダー時刻の計算
            remind_datetime = schedule.start_datetime - time_delta
            
            # 過去の時刻チェック
            if remind_datetime < datetime.now():
                embed = create_error_embed(
                    "時刻エラー",
                    "リマインダー時刻が過去になってしまいます。\n"
                    "もっと短い時間前に設定してください。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # リマインダーの作成
            reminder_id = await create_reminder(
                schedule_id=schedule_id,
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id),
                channel_id=str(interaction.channel.id),
                remind_datetime=remind_datetime,
                message=message
            )
            
            embed = create_success_embed(
                "リマインダーを設定しました",
                f"**{schedule.title}** のリマインダーを設定しました。"
            )
            embed.add_field(
                name="通知時刻",
                value=f"<t:{int(remind_datetime.timestamp())}:F>",
                inline=True
            )
            embed.add_field(
                name="予定開始まで",
                value=f"<t:{int(remind_datetime.timestamp())}:R>",
                inline=True
            )
            if message:
                embed.add_field(
                    name="カスタムメッセージ",
                    value=message,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"リマインダーを設定: 予定ID={schedule_id}, リマインダーID={reminder_id}")
            
        except Exception as e:
            logger.error(f"リマインダー設定エラー: {e}")
            embed = create_error_embed(
                "リマインダー設定失敗",
                "リマインダーの設定中にエラーが発生しました。"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="schedule-bulk", description="複数の予定を一括追加します")
    @app_commands.describe(
        json_data="JSON形式の予定データ"
    )
    async def bulk_add_schedules(
        self,
        interaction: discord.Interaction,
        json_data: str
    ):
        """一括予定追加"""
        try:
            await interaction.response.defer()
            
            # JSONの解析
            try:
                schedules_data = json.loads(json_data)
            except json.JSONDecodeError:
                embed = create_error_embed(
                    "JSON解析エラー",
                    "JSON形式が正しくありません。\n\n"
                    "**例:**\n"
                    "```json\n"
                    "[\n"
                    "  {\n"
                    "    \"title\": \"会議1\",\n"
                    "    \"date\": \"2025-08-01\",\n"
                    "    \"time\": \"10:00\",\n"
                    "    \"description\": \"重要な会議\"\n"
                    "  }\n"
                    "]\n"
                    "```"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if not isinstance(schedules_data, list):
                embed = create_error_embed(
                    "データ形式エラー",
                    "データは配列形式で指定してください。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # 一括作成用データの準備
            processed_schedules = []
            
            for i, schedule_data in enumerate(schedules_data):
                if not isinstance(schedule_data, dict):
                    embed = create_error_embed(
                        "データ形式エラー",
                        f"{i+1}番目のデータが辞書形式ではありません。"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # 必須フィールドのチェック
                if 'title' not in schedule_data or 'date' not in schedule_data:
                    embed = create_error_embed(
                        "必須フィールドエラー",
                        f"{i+1}番目のデータに title または date が不足しています。"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # 日時の解析
                start_datetime = parse_datetime_string(
                    schedule_data['date'],
                    schedule_data.get('time')
                )
                if not start_datetime:
                    embed = create_error_embed(
                        "日時解析エラー",
                        f"{i+1}番目のデータの日時解析に失敗しました。"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                processed_schedules.append({
                    'user_id': str(interaction.user.id),
                    'guild_id': str(interaction.guild.id),
                    'title': schedule_data['title'],
                    'description': schedule_data.get('description'),
                    'start_datetime': start_datetime,
                    'end_datetime': None  # 一括追加では終了時間は未対応
                })
            
            # 一括作成実行
            created_ids = await create_bulk_schedules(processed_schedules)
            
            if created_ids:
                embed = create_success_embed(
                    "一括追加完了",
                    f"{len(created_ids)}件の予定を追加しました。"
                )
                embed.set_footer(text=f"作成された予定ID: {', '.join(map(str, created_ids))}")
                await interaction.followup.send(embed=embed)
                logger.info(f"一括予定追加: {len(created_ids)}件 (ユーザー: {interaction.user.id})")
            else:
                embed = create_error_embed(
                    "一括追加失敗",
                    "予定の一括追加に失敗しました。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"一括予定追加エラー: {e}")
            embed = create_error_embed(
                "一括追加失敗",
                "一括追加中にエラーが発生しました。"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    """Cogのセットアップ関数"""
    await bot.add_cog(ScheduleCog(bot))
    logger.info("予定管理Cogをロードしました")
