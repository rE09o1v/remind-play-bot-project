"""
Windows環境でのFFmpeg自動インストールスクリプト
静的バイナリをダウンロードしてPATHに追加

作成日: 2025-07-31
"""

import os
import sys
import zipfile
import urllib.request
import tempfile
import shutil
from pathlib import Path

def check_ffmpeg_installed():
    """FFmpegがインストール済みかチェック"""
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpegは既にインストールされています")
            version_line = result.stdout.split('\n')[0]
            print(f"📦 {version_line}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ FFmpegが見つかりません")
    return False

def download_ffmpeg():
    """FFmpeg Windows用バイナリをダウンロード"""
    print("📥 FFmpeg Windows用バイナリをダウンロード中...")
    
    # FFmpeg公式の静的ビルド (Windows 64bit)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # 一時ディレクトリにダウンロード
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "ffmpeg.zip")
    
    try:
        print(f"🌐 ダウンロード元: {ffmpeg_url}")
        urllib.request.urlretrieve(ffmpeg_url, zip_path)
        print("✅ ダウンロード完了")
        
        return zip_path, temp_dir
    
    except Exception as e:
        print(f"❌ ダウンロードエラー: {e}")
        return None, None

def extract_ffmpeg(zip_path, temp_dir):
    """FFmpegを展開"""
    print("📂 FFmpegを展開中...")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 展開されたディレクトリを探す
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path) and 'ffmpeg' in item.lower():
                bin_path = os.path.join(item_path, 'bin')
                if os.path.exists(bin_path):
                    print("✅ 展開完了")
                    return bin_path
        
        print("❌ FFmpegバイナリが見つかりません")
        return None
        
    except Exception as e:
        print(f"❌ 展開エラー: {e}")
        return None

def install_ffmpeg_locally(bin_path):
    """FFmpegをプロジェクトローカルにインストール"""
    print("📁 FFmpegをプロジェクトに配置中...")
    
    # プロジェクト内のffmpegディレクトリ
    project_ffmpeg = Path("ffmpeg")
    project_ffmpeg.mkdir(exist_ok=True)
    
    try:
        # 必要なファイルをコピー
        required_files = ['ffmpeg.exe', 'ffprobe.exe']
        
        for file_name in required_files:
            src = os.path.join(bin_path, file_name)
            dst = project_ffmpeg / file_name
            
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"✅ {file_name} をコピー")
            else:
                print(f"⚠️  {file_name} が見つかりません")
        
        # パス設定の説明を表示
        ffmpeg_path = project_ffmpeg.absolute()
        print(f"📍 FFmpegパス: {ffmpeg_path}")
        
        # 環境変数への追加方法を表示
        print("\n🔧 環境変数PATHへの追加方法:")
        print("1. Windowsキー + R で「ファイル名を指定して実行」")
        print("2. 'sysdm.cpl' と入力してEnter")
        print("3. 「詳細設定」タブ → 「環境変数」")
        print("4. 「Path」を選択 → 「編集」")
        print("5. 「新規」をクリック")
        print(f"6. このパスを追加: {ffmpeg_path}")
        print("7. OK → OK → OK でウィンドウを閉じる")
        print("8. コマンドプロンプトを再起動")
        
        return True
        
    except Exception as e:
        print(f"❌ インストールエラー: {e}")
        return False

def create_ffmpeg_test():
    """FFmpegテスト用スクリプト作成"""
    test_script = """
import subprocess
import sys

def test_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg動作確認OK")
            print(result.stdout.split('\\n')[0])
            return True
        else:
            print("❌ FFmpegエラー")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("❌ FFmpegが見つかりません")
        print("💡 環境変数PATHにFFmpegが追加されているか確認してください")
        return False
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        return False

if __name__ == "__main__":
    test_ffmpeg()
"""
    
    with open("test_ffmpeg.py", "w", encoding="utf-8") as f:
        f.write(test_script)
    
    print("📝 test_ffmpeg.py を作成しました")
    print("💡 python test_ffmpeg.py でFFmpegをテストできます")

def main():
    """メイン実行関数"""
    print("🛠️  Windows FFmpeg インストーラー")
    print("=" * 50)
    
    # 既存チェック
    if check_ffmpeg_installed():
        return
    
    print("\n📋 FFmpegをプロジェクトローカルにインストールします")
    response = input("続行しますか? (y/N): ")
    
    if response.lower() not in ['y', 'yes']:
        print("⏹️  インストールをキャンセルしました")
        return
    
    # ダウンロード
    zip_path, temp_dir = download_ffmpeg()
    if not zip_path:
        return
    
    # 展開
    bin_path = extract_ffmpeg(zip_path, temp_dir)
    if not bin_path:
        return
    
    # インストール
    if install_ffmpeg_locally(bin_path):
        print("✅ FFmpegインストール完了")
        create_ffmpeg_test()
    
    # 一時ファイル削除
    try:
        shutil.rmtree(temp_dir)
        print("🗑️  一時ファイルを削除")
    except:
        pass

if __name__ == "__main__":
    main()