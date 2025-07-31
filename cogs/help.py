"""
ヘルプコマンドのCog
BOTの使用方法を表示

作成者: [Your Name]
作成日: 2025-07-31
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils.helpers import create_info_embed, create_error_embed

logger = logging.getLogger(__name__)

class HelpCog(commands.Cog):
    """
    ヘルプ機能を提供するCog
    """
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("ヘルプCogを初期化しました")
    
    @app_commands.command(name="help", description="BOTの使用方法を表示します")
    async def help_command(self, interaction: discord.Interaction):
        """ヘルプ表示"""
        try:
            embed = discord.Embed(
                title="📚 Schedule Bot ヘルプ",
                description="予定管理とYouTube音楽再生機能を提供するBOTです",
                color=0x00ff99
            )
            
            # 予定管理コマンド
            schedule_commands = [
                "`/schedule-add <タイトル> <日付> [時間]` - 予定を追加",
                "`/schedule-list [期間]` - 予定一覧を表示",
                "`/schedule-calendar [年] [月]` - カレンダー形式で表示",
                "`/schedule-edit <ID> [項目]` - 予定を編集",
                "`/schedule-delete <ID>` - 予定を削除",
                "`/schedule-remind <ID> <時間前>` - リマインダー設定",
                "`/schedule-bulk <JSON>` - 複数予定を一括追加"
            ]
            
            embed.add_field(
                name="📅 予定管理コマンド",
                value="\n".join(schedule_commands),
                inline=False
            )
            
            # 音楽再生コマンド
            music_commands = [
                "`/play <URL/検索語>` - YouTube音楽を再生",
                "`/pause` - 一時停止",
                "`/resume` - 再開",
                "`/stop` - 停止",
                "`/volume <0-100>` - 音量調整",
                "`/nowplaying` - 現在再生中の情報",
                "`/disconnect` - ボイスチャンネルから切断"
            ]
            
            embed.add_field(
                name="🎵 音楽再生コマンド",
                value="\n".join(music_commands),
                inline=False
            )
            
            # 使用例
            examples = [
                "**予定追加**: `/schedule-add title:会議 date:明日 time:14:30`",
                "**音楽再生**: `/play query:Official髭男dism Pretender`",
                "**カレンダー**: `/schedule-calendar show_all:True`"
            ]
            
            embed.add_field(
                name="💡 使用例",
                value="\n".join(examples),
                inline=False
            )
            
            # 日付・時間の形式
            datetime_formats = [
                "**日付**: `2025-07-31`, `7/31`, `明日`, `今日`, `明後日`",
                "**時間**: `14:30`, `2:30PM`, `9AM` (省略時は9:00)",
                "**期間**: `30分`, `1時間`, `2日` (リマインダー用)"
            ]
            
            embed.add_field(
                name="📝 日付・時間の形式",
                value="\n".join(datetime_formats),
                inline=False
            )
            
            # フッター情報
            embed.set_footer(
                text="困ったときは管理者にお問い合わせください | " + 
                     f"サーバー数: {len(self.bot.guilds)}"
            )
            
            # サムネイル設定
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"ヘルプコマンドエラー: {e}")
            embed = create_error_embed(
                "ヘルプ表示失敗",
                "ヘルプの表示中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="info", description="BOTの情報を表示します")
    async def info_command(self, interaction: discord.Interaction):
        """BOT情報表示"""
        try:
            embed = discord.Embed(
                title="🤖 Schedule Bot 情報",
                color=0x0099ff
            )
            
            # 基本情報
            embed.add_field(
                name="バージョン",
                value="v1.0.0",
                inline=True
            )
            
            embed.add_field(
                name="開発言語",
                value="Python",
                inline=True
            )
            
            embed.add_field(
                name="ライブラリ",
                value="discord.py",
                inline=True
            )
            
            # 統計情報
            embed.add_field(
                name="接続サーバー数",
                value=f"{len(self.bot.guilds)}サーバー",
                inline=True
            )
            
            # 総ユーザー数を計算
            total_users = sum(guild.member_count for guild in self.bot.guilds)
            embed.add_field(
                name="総ユーザー数",
                value=f"{total_users:,}人",
                inline=True
            )
            
            embed.add_field(
                name="レイテンシ",
                value=f"{self.bot.latency * 1000:.1f}ms",
                inline=True
            )
            
            # 機能
            features = [
                "📅 予定管理・共有",
                "🗓️ カレンダー表示",
                "⏰ リマインダー通知",
                "🎵 YouTube音楽再生",
                "🔄 一括予定操作"
            ]
            
            embed.add_field(
                name="主な機能",
                value="\n".join(features),
                inline=False
            )
            
            # 作成者情報
            embed.add_field(
                name="作成者",
                value="[Your Name]",
                inline=True
            )
            
            embed.add_field(
                name="作成日",
                value="2025年7月31日",
                inline=True
            )
            
            # ホスティング情報
            embed.add_field(
                name="ホスティング",
                value="Render",
                inline=True
            )
            
            # BOTのアバター
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            
            embed.set_footer(text="Schedule Bot | 24時間稼働中")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"情報コマンドエラー: {e}")
            embed = create_error_embed(
                "情報表示失敗",
                "BOT情報の表示中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="ping", description="BOTの応答速度を測定します")
    async def ping_command(self, interaction: discord.Interaction):
        """Ping測定"""
        try:
            # レイテンシの測定
            latency = self.bot.latency * 1000
            
            embed = discord.Embed(
                title="🏓 Pong!",
                color=0x00ff00 if latency < 100 else 0xffa500 if latency < 300 else 0xff0000
            )
            
            embed.add_field(
                name="レイテンシ",
                value=f"{latency:.1f}ms",
                inline=True
            )
            
            # レイテンシの評価
            if latency < 100:
                status = "🟢 非常に良好"
            elif latency < 200:
                status = "🟡 良好"
            elif latency < 300:
                status = "🟠 普通"
            else:
                status = "🔴 遅延あり"
            
            embed.add_field(
                name="状態",
                value=status,
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Pingコマンドエラー: {e}")
            embed = create_error_embed(
                "Ping測定失敗",
                "応答速度の測定中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Cogのセットアップ関数"""
    await bot.add_cog(HelpCog(bot))
    logger.info("ヘルプCogをロードしました")
