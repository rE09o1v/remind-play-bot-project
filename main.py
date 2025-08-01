"""
Discord BOT メインファイル
予定管理とYouTube再生機能を持つBOT

作成者: [Your Name]
作成日: 2025-07-31
"""

import os
import asyncio
import logging
from datetime import datetime
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from aiohttp import web
import threading

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScheduleBot(commands.Bot):
    """
    予定管理とYouTube再生機能を持つDiscord BOT
    """
    
    def __init__(self):
        # BOTの基本設定
        intents = discord.Intents.default()
        intents.message_content = True  # メッセージ内容の取得を許可
        intents.voice_states = True     # ボイスチャンネル状態の取得を許可
        
        super().__init__(
            command_prefix='!',  # プレフィックス（スラッシュコマンド優先）
            intents=intents,
            help_command=None    # デフォルトのhelpコマンドを無効化
        )
        
    async def setup_hook(self):
        """
        BOT起動時の初期化処理
        """
        logger.info("BOTの初期化を開始...")
        
        # データベースの初期化
        from database.database import init_database
        await init_database()
        logger.info("データベースの初期化完了")
        
        # Cogsの読み込み
        cogs_to_load = [
            'cogs.schedule',  # 予定管理機能
            'cogs.music',     # YouTube再生機能
            'cogs.help',      # ヘルプ機能
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog '{cog}' を読み込みました")
            except Exception as e:
                logger.error(f"Cog '{cog}' の読み込みに失敗: {e}")
        
        # スラッシュコマンドの同期
        try:
            synced = await self.tree.sync()
            logger.info(f"{len(synced)}個のスラッシュコマンドを同期しました")
        except Exception as e:
            logger.error(f"スラッシュコマンドの同期に失敗: {e}")
        
        # 定期実行タスクの開始
        self.reminder_task.start()
        logger.info("リマインダータスクを開始しました")
    
    async def on_ready(self):
        """
        BOTがDiscordに接続完了した時の処理
        """
        logger.info(f'{self.user} としてログインしました')
        logger.info(f'BOT ID: {self.user.id}')
        logger.info(f'接続サーバー数: {len(self.guilds)}')
        
        # BOTのステータス設定
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="予定とYouTube | /help"
        )
        await self.change_presence(activity=activity)
        
    async def on_guild_join(self, guild):
        """
        新しいサーバーに追加された時の処理
        """
        logger.info(f"新しいサーバーに参加しました: {guild.name} (ID: {guild.id})")
        
        # ウェルカムメッセージの送信
        if guild.system_channel:
            embed = discord.Embed(
                title="🎉 Schedule Bot へようこそ！",
                description=(
                    "予定管理とYouTube再生機能を提供します！\n\n"
                    "**主な機能:**\n"
                    "📅 予定の管理・共有\n"
                    "🎵 YouTube音声再生\n\n"
                    "コマンド一覧: `/help`"
                ),
                color=0x00ff00
            )
            embed.set_footer(text="Schedule Bot | 使い方がわからない場合は /help をお試しください")
            
            try:
                await guild.system_channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"サーバー {guild.name} でウェルカムメッセージの送信に失敗（権限不足）")
    
    @tasks.loop(minutes=1)
    async def reminder_task(self):
        """
        リマインダーの定期チェック（1分間隔）
        """
        try:
            from database.database import get_pending_reminders
            from utils.helpers import send_reminder
            
            # 通知が必要なリマインダーを取得
            reminders = await get_pending_reminders()
            
            for reminder in reminders:
                try:
                    await send_reminder(self, reminder)
                    logger.info(f"リマインダーを送信: {reminder['title']}")
                except Exception as e:
                    logger.error(f"リマインダー送信エラー: {e}")
                    
        except Exception as e:
            logger.error(f"リマインダータスクでエラー: {e}")
    
    @reminder_task.before_loop
    async def before_reminder_task(self):
        """
        リマインダータスク開始前の待機
        """
        await self.wait_until_ready()

async def create_health_server():
    """
    Render用のヘルスチェックHTTPサーバーを作成
    """
    async def health_check(request):
        return web.json_response({
            "status": "healthy",
            "service": "discord-schedule-bot",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def bot_status(request):
        return web.json_response({
            "status": "running",
            "type": "discord-bot"
        })
    
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', bot_status)
    
    # Renderから提供されるPORT環境変数を使用
    port = int(os.getenv('PORT', 10000))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"HTTPサーバーがポート {port} で起動しました (Render対応)")
    return runner

async def main():
    """
    BOTのメイン実行関数 (Render対応版)
    """
    # Discord BOTトークンの確認
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKENが設定されていません。.envファイルを確認してください。")
        logger.error("💡 .envファイルでDISCORD_TOKENを設定してください")
        return
    
    # トークンの基本チェック（デバッグ用）
    logger.info(f"トークン長: {len(token)} 文字")
    if token == 'your_discord_bot_token_here':
        logger.error("デフォルトのトークンが設定されています。実際のBOTトークンに変更してください。")
        return
    
    # Render用HTTPサーバーの起動
    logger.info("Render用HTTPサーバーを起動中...")
    http_runner = await create_health_server()
    
    # BOTインスタンスの作成と起動
    bot = ScheduleBot()
    
    try:
        logger.info("Discord BOTに接続を試行中...")
        await bot.start(token)
    except discord.LoginFailure as e:
        logger.error(f"認証失敗: {e}")
        logger.error("💡 BOTトークンが正しいか確認してください")
        logger.error("💡 Discord Developer Portalでトークンを再生成してみてください")
        await bot.close()
        await http_runner.cleanup()
    except discord.HTTPException as e:
        logger.error(f"Discord API エラー: {e}")
        logger.error("💡 インターネット接続を確認してください")
        await bot.close()
        await http_runner.cleanup()
    except KeyboardInterrupt:
        logger.info("BOTを停止しています...")
        await bot.close()
        await http_runner.cleanup()
    except Exception as e:
        logger.error(f"BOT実行中にエラーが発生: {e}")
        logger.error(f"エラータイプ: {type(e).__name__}")
        import traceback
        logger.error(f"詳細エラー:\n{traceback.format_exc()}")
        await bot.close()
        await http_runner.cleanup()

if __name__ == '__main__':
    # Windowsでのイベントループポリシー設定（必要に応じて）
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # BOTの実行
    asyncio.run(main())
