"""
Discord BOTトークンのデバッグ用スクリプト
トークンの形式や設定を詳細チェック

作成日: 2025-07-31
"""

import os
import re
from dotenv import load_dotenv

def check_token_format():
    """トークンの形式をチェック"""
    print("🔐 Discord BOTトークンの詳細チェック")
    print("=" * 50)
    
    # 環境変数の読み込み
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("❌ DISCORD_TOKENが設定されていません")
        print("💡 .envファイルを確認してください")
        return False
    
    # トークンの基本情報
    print(f"📏 トークン長: {len(token)} 文字")
    print(f"🔤 開始文字: {token[:10]}...")
    print(f"🔤 終了文字: ...{token[-10:]}")
    
    # トークンの形式チェック
    # Discord BOTトークンの一般的な形式:
    # - 古い形式: 24文字.6文字.27文字
    # - 新しい形式: "Bot " + base64エンコードされた文字列
    
    # 一般的なパターンをチェック
    patterns = [
        r'^[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}$',  # 古い形式
        r'^[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{38}$',  # 新しい形式
        r'^Bot [A-Za-z0-9_-]+$',  # Bot プレフィックス付き
    ]
    
    format_valid = False
    for i, pattern in enumerate(patterns):
        if re.match(pattern, token):
            format_valid = True
            print(f"✅ トークン形式: パターン{i+1}にマッチ")
            break
    
    if not format_valid:
        print("⚠️  トークン形式が一般的なパターンにマッチしません")
        print("💡 Discord Developer Portalからコピーし直してください")
    
    # 空白文字や改行のチェック
    if token != token.strip():
        print("❌ トークンに余分な空白や改行が含まれています")
        print("💡 .envファイルでトークンをもう一度確認してください")
        return False
    
    # 特殊文字のチェック
    if any(c in token for c in [' ', '\n', '\r', '\t']) and not token.startswith('Bot '):
        print("❌ トークンに無効な文字が含まれています")
        print("💡 Discord Developer Portalからコピーし直してください")
        return False
    
    print("✅ トークン形式の基本チェックOK")
    
    # 接続テスト用のサンプルコード表示
    print("\n🧪 接続テスト用コード:")
    print("-" * 30)
    print("import discord")
    print("import asyncio")
    print("")
    print("async def test_connection():")
    print("    try:")
    print("        client = discord.Client(intents=discord.Intents.default())")
    print("        await client.login(token)")
    print("        print('✅ 接続成功')")
    print("        await client.close()")
    print("    except discord.LoginFailure:")
    print("        print('❌ 認証失敗 - トークンが無効です')")
    print("    except Exception as e:")
    print("        print(f'❌ エラー: {e}')")
    print("")
    print("# asyncio.run(test_connection())")
    
    return True

def check_env_file():
    """環境変数ファイルの詳細チェック"""
    print("\n📁 .envファイルの詳細チェック")
    print("-" * 30)
    
    env_path = ".env"
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 ファイルサイズ: {len(content)} バイト")
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'DISCORD_TOKEN' in line:
                if line.startswith('#'):
                    print(f"⚠️  行{i}: DISCORD_TOKENがコメントアウトされています")
                elif '=' not in line:
                    print(f"❌ 行{i}: =が見つかりません")
                else:
                    key, value = line.split('=', 1)
                    if not value or value.strip() == 'your_discord_bot_token_here':
                        print(f"❌ 行{i}: トークンが設定されていません")
                    else:
                        print(f"✅ 行{i}: DISCORD_TOKEN設定OK")
    
    except FileNotFoundError:
        print("❌ .envファイルが見つかりません")
        return False
    except Exception as e:
        print(f"❌ .envファイル読み取りエラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_env_file()
    check_token_format()
    
    print("\n" + "=" * 50)
    print("🔧 トラブルシューティング")
    print("1. Discord Developer Portal でBOTトークンを再生成")
    print("2. 新しいトークンを.envファイルにコピー")
    print("3. BOTに必要な権限（Intents）が有効になっているか確認")
    print("4. BOTがサーバーに招待されているか確認")