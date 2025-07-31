
import subprocess
import sys

def test_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg動作確認OK")
            print(result.stdout.split('\n')[0])
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
