"""
YouTube音楽再生機能のCog
yt-dlpとFFmpegを使用した音声ストリーミング

作成者: [Your Name]
作成日: 2025-07-31
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
import yt_dlp
from typing import Optional, Dict, Any, List
import re
from urllib.parse import urlparse
import functools

from utils.helpers import (
    create_error_embed,
    create_success_embed,
    create_info_embed,
    validate_youtube_url,
    load_volume_setting,
    save_volume_setting
)

logger = logging.getLogger(__name__)

# yt-dlpの設定
YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # IPV6対応
    'extractaudio': True,
    'audioformat': 'mp3',
    'audioquality': '192K',
}

# FFmpegの設定
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    """
    YouTube音声ソースクラス
    """
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')
        self.webpage_url = data.get('webpage_url')
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        """
        URLから音声ソースを作成
        
        Args:
            url: YouTube URL または検索キーワード
            loop: イベントループ
            stream: ストリーミング再生するか
        
        Returns:
            YTDLSourceオブジェクト
        """
        loop = loop or asyncio.get_event_loop()
        
        # yt-dlpでの情報取得を非同期で実行
        data = await loop.run_in_executor(
            None, 
            lambda: ytdl.extract_info(url, download=not stream)
        )
        
        if 'entries' in data:
            # プレイリストの場合は最初の動画を取得
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        
        # FFmpegソースの作成
        ffmpeg_source = discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS)
        
        return cls(ffmpeg_source, data=data)
    
    @classmethod  
    async def search(cls, search_term, *, loop=None):
        """
        検索キーワードから動画情報を取得
        
        Args:
            search_term: 検索キーワード
            loop: イベントループ
        
        Returns:
            検索結果のリスト
        """
        loop = loop or asyncio.get_event_loop()
        
        # 検索用の設定
        search_opts = YTDL_FORMAT_OPTIONS.copy()
        search_opts.update({
            'quiet': True,
            'extract_flat': 'discard_in_playlist',  # メタデータのみ取得
        })
        
        search_ytdl = yt_dlp.YoutubeDL(search_opts)
        
        # ytsearch5:<query> 形式で検索（上位5件）
        search_query = f"ytsearch5:{search_term}"
        
        try:
            data = await loop.run_in_executor(
                None,
                lambda: search_ytdl.extract_info(search_query, download=False)
            )
            
            if data and 'entries' in data:
                # 抽出された各エントリに webpage_url がない場合、動画URLを生成
                for entry in data['entries']:
                    if not entry.get('webpage_url') and entry.get('id'):
                        entry['webpage_url'] = f"https://www.youtube.com/watch?v={entry['id']}"
                return data['entries'][:5]
            return []
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            return []

class MusicPlayer:
    """
    音楽プレイヤークラス
    ギルドごとの再生状態を管理
    """
    
    def __init__(self, guild_id: int, initial_volume: float = 0.1):
        self.guild_id = guild_id
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current_source: Optional[YTDLSource] = None
        # 初期音量（0.0 - 1.0）
        self.volume = max(0.0, min(1.0, initial_volume))
        self.is_playing = False
        self.is_paused = False
        
        # 再生制御用のイベント
        self._stop_event = asyncio.Event()
    
    async def connect_to_channel(self, channel: discord.VoiceChannel) -> bool:
        """
        ボイスチャンネルに接続
        
        Args:
            channel: 接続先のボイスチャンネル
        
        Returns:
            接続成功の可否
        """
        try:
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.move_to(channel)
            else:
                self.voice_client = await channel.connect()
            
            logger.info(f"ボイスチャンネルに接続: {channel.name} (Guild: {self.guild_id})")
            return True
            
        except Exception as e:
            logger.error(f"ボイスチャンネル接続エラー: {e}")
            return False
    
    async def disconnect(self):
        """
        ボイスチャンネルから切断
        """
        if self.voice_client:
            if self.is_playing:
                self.voice_client.stop()
            
            await self.voice_client.disconnect()
            self.voice_client = None
            self.current_source = None
            self.is_playing = False
            self.is_paused = False
            
            logger.info(f"ボイスチャンネルから切断 (Guild: {self.guild_id})")
    
    async def play(self, source: YTDLSource) -> bool:
        """
        音楽を再生
        
        Args:
            source: 再生する音声ソース
        
        Returns:
            再生開始成功の可否
        """
        if not self.voice_client or not self.voice_client.is_connected():
            logger.error("ボイスチャンネルに接続していません")
            return False
        
        try:
            # 既に再生中の場合は停止
            if self.voice_client.is_playing():
                self.voice_client.stop()
            
            # 音量設定
            source.volume = self.volume
            
            # 再生開始
            self.voice_client.play(
                source,
                after=lambda e: logger.error(f'Player error: {e}') if e else None
            )
            
            self.current_source = source
            self.is_playing = True
            self.is_paused = False
            
            logger.info(f"再生開始: {source.title} (Guild: {self.guild_id})")
            return True
            
        except Exception as e:
            logger.error(f"再生エラー: {e}")
            return False
    
    def pause(self) -> bool:
        """
        再生を一時停止
        
        Returns:
            一時停止成功の可否
        """
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True
            logger.info(f"再生を一時停止 (Guild: {self.guild_id})")
            return True
        return False
    
    def resume(self) -> bool:
        """
        再生を再開
        
        Returns:
            再開成功の可否
        """
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused = False
            logger.info(f"再生を再開 (Guild: {self.guild_id})")
            return True
        return False
    
    def stop(self) -> bool:
        """
        再生を停止
        
        Returns:
            停止成功の可否
        """
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()
            self.current_source = None
            self.is_playing = False
            self.is_paused = False
            logger.info(f"再生を停止 (Guild: {self.guild_id})")
            return True
        return False
    
    def set_volume(self, volume: float) -> bool:
        """
        音量を設定
        
        Args:
            volume: 音量 (0.0 - 1.0)
        
        Returns:
            音量設定成功の可否
        """
        try:
            volume = max(0.0, min(1.0, volume))  # 0.0-1.0の範囲に制限
            self.volume = volume
            
            if self.current_source:
                self.current_source.volume = volume

            # 永続ストレージに保存
            try:
                save_volume_setting(self.guild_id, self.volume)
            except Exception:
                pass
            
            logger.info(f"音量を設定: {volume * 100:.0f}% (Guild: {self.guild_id})")
            return True
            
        except Exception as e:
            logger.error(f"音量設定エラー: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        現在の再生状態を取得
        
        Returns:
            再生状態の辞書
        """
        return {
            'is_connected': self.voice_client is not None and self.voice_client.is_connected(),
            'is_playing': self.is_playing and self.voice_client and self.voice_client.is_playing(),
            'is_paused': self.is_paused,
            'current_song': self.current_source.title if self.current_source else None,
            'volume': int(self.volume * 100),
            'channel': self.voice_client.channel.name if self.voice_client and self.voice_client.channel else None
        }

class MusicCog(commands.Cog):
    """
    YouTube音楽再生機能を提供するCog
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.players: Dict[int, MusicPlayer] = {}  # ギルドID -> MusicPlayer
        logger.info("音楽再生Cogを初期化しました")
    
    def get_player(self, guild_id: int) -> MusicPlayer:
        """
        ギルドのプレイヤーを取得（存在しない場合は作成）
        
        Args:
            guild_id: ギルドID
        
        Returns:
            MusicPlayerオブジェクト
        """
        if guild_id not in self.players:
            # 以前保存した音量を読み込み（なければデフォルト 0.1 = 10%）
            initial_volume = load_volume_setting(guild_id)
            if initial_volume is None:
                initial_volume = 0.1
            self.players[guild_id] = MusicPlayer(guild_id, initial_volume=initial_volume)
        return self.players[guild_id]
    
    async def cog_unload(self):
        """
        Cog終了時の処理
        """
        for player in self.players.values():
            await player.disconnect()
        self.players.clear()
        logger.info("音楽再生Cogを終了しました")
    
    @app_commands.command(name="play", description="YouTube音楽を再生します")
    @app_commands.describe(
        query="YouTube URL または 検索キーワード"
    )
    async def play(self, interaction: discord.Interaction, query: str):
        """音楽再生"""
        try:
            await interaction.response.defer()
            
            # ユーザーがボイスチャンネルにいるかチェック
            if not interaction.user.voice or not interaction.user.voice.channel:
                embed = create_error_embed(
                    "ボイスチャンネルエラー",
                    "まずボイスチャンネルに参加してください。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            channel = interaction.user.voice.channel
            player = self.get_player(interaction.guild.id)
            
            # ボイスチャンネルに接続
            if not await player.connect_to_channel(channel):
                embed = create_error_embed(
                    "接続エラー",
                    "ボイスチャンネルに接続できませんでした。"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # URLかどうかを判定
            is_url = validate_youtube_url(query)
            
            if not is_url:
                # 検索モード
                embed = create_info_embed(
                    "検索中...",
                    f"「{query}」を検索しています..."
                )
                search_msg = await interaction.followup.send(embed=embed)
                
                # 検索実行
                search_results = await YTDLSource.search(query)
                
                if not search_results:
                    embed = create_error_embed(
                        "検索結果なし",
                        "検索結果が見つかりませんでした。"
                    )
                    await search_msg.edit(embed=embed)
                    return
                
                # 最初の結果を選択
                selected = search_results[0]
                query = selected['webpage_url']
                
                embed = create_info_embed(
                    "検索完了",
                    f"**{selected['title']}** を選択しました。\n読み込み中..."
                )
                await search_msg.edit(embed=embed)
            else:
                # URL直接指定の場合
                embed = create_info_embed(
                    "読み込み中...",
                    "動画情報を取得しています..."
                )
                await interaction.followup.send(embed=embed)
            
            # 音声ソースの作成
            try:
                source = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            except Exception as e:
                logger.error(f"音声ソース作成エラー: {e}")
                embed = create_error_embed(
                    "読み込みエラー",
                    "動画の読み込みに失敗しました。\n"
                    "URLが正しいか、動画が利用可能か確認してください。"
                )
                await interaction.edit_original_response(embed=embed)
                return
            
            # 再生開始
            if await player.play(source):
                embed = discord.Embed(
                    title="🎵 再生開始",
                    description=f"**[{source.title}]({source.webpage_url})**",
                    color=0x00ff00
                )
                
                if source.duration:
                    # 秒を分:秒形式に変換
                    minutes, seconds = divmod(source.duration, 60)
                    duration_str = f"{int(minutes)}:{int(seconds):02d}"
                    embed.add_field(name="長さ", value=duration_str, inline=True)
                
                if source.uploader:
                    embed.add_field(name="アップロード者", value=source.uploader, inline=True)
                
                embed.add_field(name="音量", value=f"{int(player.volume * 100)}%", inline=True)
                
                if source.thumbnail:
                    embed.set_thumbnail(url=source.thumbnail)
                
                embed.set_footer(text=f"リクエスト: {interaction.user.display_name}")
                
                await interaction.edit_original_response(embed=embed)
                logger.info(f"再生開始: {source.title} (ユーザー: {interaction.user.id})")
            else:
                embed = create_error_embed(
                    "再生エラー",
                    "音楽の再生開始に失敗しました。"
                )
                await interaction.edit_original_response(embed=embed)
            
        except Exception as e:
            logger.error(f"再生コマンドエラー: {e}")
            embed = create_error_embed(
                "再生失敗",
                "音楽再生中にエラーが発生しました。"
            )
            try:
                await interaction.edit_original_response(embed=embed)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="pause", description="音楽を一時停止します")
    async def pause(self, interaction: discord.Interaction):
        """音楽一時停止"""
        try:
            player = self.get_player(interaction.guild.id)
            
            if player.pause():
                embed = create_success_embed(
                    "一時停止",
                    "音楽を一時停止しました。"
                )
            else:
                embed = create_error_embed(
                    "一時停止失敗",
                    "現在再生中の音楽がありません。"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"一時停止エラー: {e}")
            embed = create_error_embed(
                "一時停止失敗",
                "一時停止中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="resume", description="音楽を再開します")
    async def resume(self, interaction: discord.Interaction):
        """音楽再開"""
        try:
            player = self.get_player(interaction.guild.id)
            
            if player.resume():
                embed = create_success_embed(
                    "再開",
                    "音楽を再開しました。"
                )
            else:
                embed = create_error_embed(
                    "再開失敗",
                    "一時停止中の音楽がありません。"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"再開エラー: {e}")
            embed = create_error_embed(
                "再開失敗",
                "再開中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="stop", description="音楽を停止します")
    async def stop(self, interaction: discord.Interaction):
        """音楽停止"""
        try:
            player = self.get_player(interaction.guild.id)
            
            if player.stop():
                embed = create_success_embed(
                    "停止",
                    "音楽を停止しました。"
                )
            else:
                embed = create_error_embed(
                    "停止失敗",
                    "現在再生中の音楽がありません。"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"停止エラー: {e}")
            embed = create_error_embed(
                "停止失敗",
                "停止中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="volume", description="音量を調整します")
    @app_commands.describe(volume="音量 (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        """音量調整"""
        try:
            if not 0 <= volume <= 100:
                embed = create_error_embed(
                    "音量範囲エラー",
                    "音量は0から100の間で指定してください。"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            player = self.get_player(interaction.guild.id)
            volume_float = volume / 100.0
            
            if player.set_volume(volume_float):
                embed = create_success_embed(
                    "音量調整",
                    f"音量を {volume}% に設定しました。"
                )
            else:
                embed = create_error_embed(
                    "音量調整失敗",
                    "音量の調整に失敗しました。"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"音量調整エラー: {e}")
            embed = create_error_embed(
                "音量調整失敗",
                "音量調整中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="nowplaying", description="現在再生中の音楽情報を表示します")
    async def nowplaying(self, interaction: discord.Interaction):
        """現在再生中の情報"""
        try:
            player = self.get_player(interaction.guild.id)
            status = player.get_status()
            
            if not status['is_connected']:
                embed = create_info_embed(
                    "未接続",
                    "ボイスチャンネルに接続していません。"
                )
                await interaction.response.send_message(embed=embed)
                return
            
            if not status['current_song']:
                embed = create_info_embed(
                    "再生なし",
                    "現在再生中の音楽はありません。"
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # 現在再生中の情報を表示
            embed = discord.Embed(
                title="🎵 現在再生中",
                description=f"**[{player.current_source.title}]({player.current_source.webpage_url})**",
                color=0x00ff99
            )
            
            # 再生状態
            state = "⏸️ 一時停止中" if status['is_paused'] else "▶️ 再生中"
            embed.add_field(name="状態", value=state, inline=True)
            
            # 音量
            embed.add_field(name="音量", value=f"{status['volume']}%", inline=True)
            
            # チャンネル
            embed.add_field(name="チャンネル", value=status['channel'], inline=True)
            
            # 長さ
            if player.current_source.duration:
                minutes, seconds = divmod(player.current_source.duration, 60)
                duration_str = f"{int(minutes)}:{int(seconds):02d}"
                embed.add_field(name="長さ", value=duration_str, inline=True)
            
            # アップロード者
            if player.current_source.uploader:
                embed.add_field(name="アップロード者", value=player.current_source.uploader, inline=True)
            
            # サムネイル
            if player.current_source.thumbnail:
                embed.set_thumbnail(url=player.current_source.thumbnail)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"再生情報取得エラー: {e}")
            embed = create_error_embed(
                "情報取得失敗",
                "再生情報の取得中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="disconnect", description="ボイスチャンネルから切断します")
    async def disconnect(self, interaction: discord.Interaction):
        """ボイスチャンネル切断"""
        try:
            player = self.get_player(interaction.guild.id)
            
            if player.voice_client and player.voice_client.is_connected():
                await player.disconnect()
                embed = create_success_embed(
                    "切断完了",
                    "ボイスチャンネルから切断しました。"
                )
            else:
                embed = create_info_embed(
                    "未接続",
                    "ボイスチャンネルに接続していません。"
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"切断エラー: {e}")
            embed = create_error_embed(
                "切断失敗",
                "切断中にエラーが発生しました。"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    """Cogのセットアップ関数"""
    await bot.add_cog(MusicCog(bot))
    logger.info("音楽再生Cogをロードしました")
