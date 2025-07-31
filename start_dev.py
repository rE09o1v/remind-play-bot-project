"""
開発環境用のBOT起動スクリプト
必要な依存関係と設定をチェックしてからBOTを起動

作成日: 2025-07-31
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Pythonバージョンをチェック"""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9以上が必要です")
        print(f"現在のバージョン: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True

def check_env_file():
    """環境変数ファイルをチェック"""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if not env_path.exists():
        print("❌ .envファイルが見つかりません")
        if env_example_path.exists():
            print("💡 .env.exampleを.envにコピーして、DISCORD_TOKENを設定してください")
            print("   1. .env.exampleを.envにコピー")
            print("   2. .envファイルでDISCORD_TOKENを実際のトークンに変更")
        return False
    
    # 環境変数の読み込みテスト
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    if not token or token == 'your_discord_bot_token_here':
        print("❌ DISCORD_TOKENが正しく設定されていません")
        print("💡 .envファイルでDISCORD_TOKENを実際のBOTトークンに設定してください")
        return False
    
    print("✅ .envファイルの設定OK")
    return True

def check_dependencies():
    """必要な依存関係をチェック"""
    try:
        import discord
        print(f"✅ discord.py {discord.__version__}")
    except ImportError:
        print("❌ discord.pyがインストールされていません")
        print("💡 pip install -r requirements.txt を実行してください")
        return False
    
    try:
        import nacl
        print(f"✅ PyNaCl (音声機能対応)")
    except ImportError:
        print("⚠️  PyNaClがインストールされていません（音声機能が利用できません）")
        print("💡 pip install PyNaCl で音声機能を有効化できます")
    
    try:
        import yt_dlp
        print(f"✅ yt-dlp (YouTube機能対応)")
    except ImportError:
        print("❌ yt-dlpがインストールされていません")
        print("💡 pip install yt-dlp を実行してください")
        return False
    
    return True

def check_ffmpeg():
    """FFmpegの存在をチェック"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg (音声処理対応)")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("⚠️  FFmpegが見つかりません（音楽再生機能が利用できません）")
    print("💡 FFmpegをインストールしてPATHに追加してください")
    return False

def main():
    """メイン実行関数"""
    print("🤖 Schedule Bot - 開発環境チェック")
    print("=" * 50)
    
    # 各種チェックの実行
    checks = [
        ("Pythonバージョン", check_python_version()),
        ("環境変数設定", check_env_file()),
        ("Python依存関係", check_dependencies()),
        ("FFmpeg", check_ffmpeg()),
    ]
    
    # 結果表示
    print("\n📋 チェック結果")
    print("-" * 30)
    all_passed = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed and name in ["環境変数設定", "Python依存関係"]:
            all_passed = False
    
    print("-" * 30)
    
    if all_passed:
        print("🚀 BOTを起動します...")
        print()
        
        # main.pyを実行
        try:
            subprocess.run([sys.executable, "main.py"], check=True)
        except KeyboardInterrupt:
            print("\n👋 BOTを停止しました")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ BOT実行中にエラーが発生: {e}")
    else:
        print("❌ 必須設定が不足しています。上記の問題を解決してから再実行してください。")

if __name__ == "__main__":
    main()