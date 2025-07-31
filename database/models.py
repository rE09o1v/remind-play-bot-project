"""
データベースモデル定義
予定管理のためのテーブル構造

作成者: [Your Name]
作成日: 2025-07-31
"""

from datetime import datetime
from typing import Optional, Dict, Any

# データベーステーブルの構造定義

# schedules テーブル - 予定情報
SCHEDULES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,                    -- Discord ユーザーID
    guild_id TEXT NOT NULL,                   -- Discord サーバーID
    title TEXT NOT NULL,                      -- 予定のタイトル
    description TEXT,                         -- 予定の詳細説明
    start_datetime DATETIME NOT NULL,         -- 開始日時
    end_datetime DATETIME,                    -- 終了日時（オプション）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 作成日時
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 更新日時
    is_active BOOLEAN DEFAULT TRUE            -- 有効/無効フラグ
);
"""

# reminders テーブル - リマインダー設定
REMINDERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL,             -- 予定ID（外部キー）
    user_id TEXT NOT NULL,                    -- 通知対象ユーザーID
    guild_id TEXT NOT NULL,                   -- Discord サーバーID
    channel_id TEXT NOT NULL,                 -- 通知チャンネルID
    remind_datetime DATETIME NOT NULL,        -- リマインダー実行日時
    message TEXT,                             -- カスタムメッセージ
    is_sent BOOLEAN DEFAULT FALSE,            -- 送信済みフラグ
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES schedules (id) ON DELETE CASCADE
);
"""

# インデックスの作成
INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_schedules_user_id ON schedules (user_id);",
    "CREATE INDEX IF NOT EXISTS idx_schedules_guild_id ON schedules (guild_id);",
    "CREATE INDEX IF NOT EXISTS idx_schedules_start_datetime ON schedules (start_datetime);",
    "CREATE INDEX IF NOT EXISTS idx_reminders_schedule_id ON reminders (schedule_id);",
    "CREATE INDEX IF NOT EXISTS idx_reminders_remind_datetime ON reminders (remind_datetime);",
    "CREATE INDEX IF NOT EXISTS idx_reminders_is_sent ON reminders (is_sent);"
]

class Schedule:
    """
    予定データのモデルクラス
    """
    
    def __init__(self, data: Dict[str, Any]):
        self.id: Optional[int] = data.get('id')
        self.user_id: str = data['user_id']
        self.guild_id: str = data['guild_id']
        self.title: str = data['title']
        self.description: Optional[str] = data.get('description')
        self.start_datetime: datetime = data['start_datetime']
        self.end_datetime: Optional[datetime] = data.get('end_datetime')
        self.created_at: Optional[datetime] = data.get('created_at')
        self.updated_at: Optional[datetime] = data.get('updated_at')
        self.is_active: bool = data.get('is_active', True)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式に変換
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'guild_id': self.guild_id,
            'title': self.title,
            'description': self.description,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active
        }
    
    def __str__(self) -> str:
        """
        文字列表現
        """
        return f"Schedule(id={self.id}, title='{self.title}', start={self.start_datetime})"

class Reminder:
    """
    リマインダーデータのモデルクラス
    """
    
    def __init__(self, data: Dict[str, Any]):
        self.id: Optional[int] = data.get('id')
        self.schedule_id: int = data['schedule_id']
        self.user_id: str = data['user_id']
        self.guild_id: str = data['guild_id']
        self.channel_id: str = data['channel_id']
        self.remind_datetime: datetime = data['remind_datetime']
        self.message: Optional[str] = data.get('message')
        self.is_sent: bool = data.get('is_sent', False)
        self.created_at: Optional[datetime] = data.get('created_at')
    
    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式に変換
        """
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'user_id': self.user_id,
            'guild_id': self.guild_id,
            'channel_id': self.channel_id,
            'remind_datetime': self.remind_datetime,
            'message': self.message,
            'is_sent': self.is_sent,
            'created_at': self.created_at
        }
    
    def __str__(self) -> str:
        """
        文字列表現
        """
        return f"Reminder(id={self.id}, schedule_id={self.schedule_id}, remind_at={self.remind_datetime})"

# データベース初期化用のSQL文リスト
INIT_SQL_STATEMENTS = [
    SCHEDULES_TABLE_SQL,
    REMINDERS_TABLE_SQL
] + INDEXES_SQL
