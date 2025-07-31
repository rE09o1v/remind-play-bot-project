# Schedule Bot 🤖

予定管理とYouTube音楽再生機能を持つDiscord BOTです。

## 機能 ✨

### 📅 予定管理
- 予定の追加・編集・削除
- カレンダー形式での表示
- リマインダー機能
- 一括予定追加
- サーバーメンバーとの予定共有

### 🎵 YouTube音楽再生
- YouTube URL または検索による音楽再生
- 基本的な再生制御（再生・一時停止・停止・音量調整）
- 現在再生中の楽曲情報表示

## セットアップ 🚀

### 1. Discordアプリケーションの作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリックして新しいアプリケーションを作成
3. 左側メニューから「Bot」を選択
4. 「Add Bot」をクリックしてBOTを作成
5. BOTトークンをコピー（後で使用）

### 2. BOT権限の設定

「OAuth2」→「URL Generator」から以下の権限を選択：

**Bot Permissions:**
- Send Messages
- Use Slash Commands
- Connect (ボイスチャンネル)
- Speak (ボイスチャンネル)
- Read Message History
- Add Reactions

**Scopes:**
- bot
- applications.commands

生成されたURLをブラウザで開き、BOTをサーバーに招待します。

### 3. ローカル開発環境のセットアップ

```bash
# リポジトリのクローン
git clone <repository-url>
cd discord_bot

# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化
# Windows
venv\\Scripts\\activate

# Mac/Linux
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数ファイルの作成
cp .env.example .env
```

### 4. 環境変数の設定

`.env` ファイルを編集し、BOTトークンを設定：

```env
DISCORD_TOKEN=your_discord_bot_token_here
```

### 5. FFmpegのインストール

音楽再生機能を使用するためにFFmpegが必要です：

**Windows:**
1. [FFmpeg公式サイト](https://ffmpeg.org/download.html) からダウンロード
2. 実行ファイルを `C:\\ffmpeg\\bin` に配置
3. システムのPATH環境変数に `C:\\ffmpeg\\bin` を追加

**Mac:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 6. BOTの起動

```bash
python main.py
```

## Renderでのデプロイ 🌐

### 1. GitHubリポジトリの準備

1. コードをGitHubリポジトリにプッシュ
2. `.env` ファイルは含めない（`.gitignore` に追加）

### 2. Renderでのサービス作成

1. [Render](https://render.com) にアクセスしてアカウント作成
2. 「New」→「Web Service」を選択
3. GitHubリポジトリを接続
4. 以下の設定を行う：

**Basic Settings:**
- Name: `schedule-bot`
- Environment: `Python 3`
- Build Command: `./build.sh`
- Start Command: `python main.py`

**Environment Variables:**
- `DISCORD_TOKEN`: あなたのBOTトークン

### 3. デプロイ

「Create Web Service」をクリックしてデプロイを開始します。
初回デプロイには数分かかる場合があります。

## コマンド一覧 📝

### 予定管理

| コマンド | 説明 | 例 |
|----------|------|---|
| `/schedule-add` | 予定を追加 | `/schedule-add title:会議 date:明日 time:14:30` |
| `/schedule-list` | 予定一覧を表示 | `/schedule-list period:week` |
| `/schedule-calendar` | カレンダー表示 | `/schedule-calendar show_all:True` |
| `/schedule-edit` | 予定を編集 | `/schedule-edit schedule_id:1 title:新しいタイトル` |
| `/schedule-delete` | 予定を削除 | `/schedule-delete schedule_id:1` |
| `/schedule-remind` | リマインダー設定 | `/schedule-remind schedule_id:1 time_before:30分` |
| `/schedule-bulk` | 一括予定追加 | JSON形式で複数予定を追加 |

### 音楽再生

| コマンド | 説明 | 例 |
|----------|------|---|
| `/play` | 音楽を再生 | `/play query:Official髭男dism Pretender` |
| `/pause` | 一時停止 | `/pause` |
| `/resume` | 再開 | `/resume` |
| `/stop` | 停止 | `/stop` |
| `/volume` | 音量調整 | `/volume volume:50` |
| `/nowplaying` | 再生中の情報 | `/nowplaying` |
| `/disconnect` | 接続を切断 | `/disconnect` |

### その他

| コマンド | 説明 |
|----------|------|
| `/help` | ヘルプを表示 |
| `/info` | BOT情報を表示 |
| `/ping` | 応答速度を測定 |

## 日付・時間の形式 📅

### 日付
- `2025-07-31` (YYYY-MM-DD形式)
- `7/31` (MM/DD形式、今年として扱う)
- `明日`, `今日`, `明後日`

### 時間
- `14:30` (24時間形式)
- `2:30PM` (12時間形式)
- `9AM` (時のみ指定)
- 省略時は 9:00 として扱う

### リマインダー期間
- `30分`, `1時間`, `2日`
- `30min`, `1hour`, `2days` (英語形式も可)

## トラブルシューティング 🔧

### よくある問題

**1. BOTがコマンドに反応しない**
- BOTがサーバーに招待されているか確認
- 適切な権限が付与されているか確認
- スラッシュコマンドの同期が完了するまで数分待つ

**2. 音楽が再生されない**
- ボイスチャンネルに参加しているか確認
- FFmpegがインストールされているか確認
- BOTにボイスチャンネルの権限があるか確認

**3. 予定が保存されない**
- データベースファイルの書き込み権限を確認
- ログファイルでエラーメッセージを確認

**4. Renderでのデプロイが失敗する**
- 環境変数が正しく設定されているか確認
- `build.sh` に実行権限があるか確認

### ログの確認

BOTの動作ログは `bot.log` ファイルに出力されます。
問題が発生した場合は、このファイルを確認してください。

## 開発者向け情報 👩‍💻

### プロジェクト構造

```
discord_bot/
├── main.py              # メインファイル
├── requirements.txt     # 依存関係
├── build.sh            # Render用ビルドスクリプト
├── .env.example        # 環境変数サンプル
├── database/           # データベース関連
│   ├── __init__.py
│   ├── models.py       # データモデル
│   └── database.py     # データベース操作
├── cogs/               # BOT機能モジュール
│   ├── __init__.py
│   ├── schedule.py     # 予定管理
│   ├── music.py        # 音楽再生
│   └── help.py         # ヘルプ
└── utils/              # ユーティリティ
    ├── __init__.py
    ├── helpers.py      # ヘルパー関数
    └── calendar_view.py # カレンダー表示
```

### 使用技術

- **Python 3.9+**
- **discord.py 2.3.2** - Discord BOTライブラリ
- **aiosqlite** - 非同期SQLite操作
- **yt-dlp** - YouTube動画処理
- **FFmpeg** - 音声処理

### 貢献方法

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/new-feature`)
3. 変更をコミット (`git commit -am 'Add new feature'`)
4. ブランチにプッシュ (`git push origin feature/new-feature`)
5. プルリクエストを作成

## ライセンス 📄

このプロジェクトは MIT ライセンスの下で公開されています。

## サポート 💬

問題や質問がある場合は、以下の方法でお問い合わせください：

- GitHub Issues
- Discord: [Your Discord]
- Email: [Your Email]

---

**Schedule Bot** - 予定管理とYouTube音楽再生を一つのBOTで！
