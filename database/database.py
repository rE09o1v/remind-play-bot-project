"""
データベース操作関数
SQLiteを使用した予定管理データのCRUD操作

作成者: [Your Name]
作成日: 2025-07-31
"""

import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from .models import Schedule, Reminder, INIT_SQL_STATEMENTS

logger = logging.getLogger(__name__)

# データベースファイルのパス
DB_PATH = Path(__file__).parent / 'schedule_bot.db'

async def init_database():
    """
    データベースの初期化
    テーブルとインデックスを作成
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # テーブルとインデックスの作成
            for sql in INIT_SQL_STATEMENTS:
                await db.execute(sql)
            
            await db.commit()
            logger.info(f"データベースを初期化しました: {DB_PATH}")
            
    except Exception as e:
        logger.error(f"データベース初期化エラー: {e}")
        raise

# ==================== 予定管理 (CRUD) ====================

async def create_schedule(
    user_id: str,
    guild_id: str,
    title: str,
    start_datetime: datetime,
    description: Optional[str] = None,
    end_datetime: Optional[datetime] = None
) -> int:
    """
    新しい予定を作成
    
    Args:
        user_id: ユーザーID
        guild_id: サーバーID
        title: 予定タイトル
        start_datetime: 開始日時
        description: 説明（オプション）
        end_datetime: 終了日時（オプション）
    
    Returns:
        作成された予定のID
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO schedules (user_id, guild_id, title, description, start_datetime, end_datetime)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, guild_id, title, description, start_datetime, end_datetime)
            )
            await db.commit()
            
            schedule_id = cursor.lastrowid
            logger.info(f"予定を作成しました: ID={schedule_id}, タイトル='{title}'")
            return schedule_id
            
    except Exception as e:
        logger.error(f"予定作成エラー: {e}")
        raise

async def get_schedule_by_id(schedule_id: int) -> Optional[Schedule]:
    """
    IDで予定を取得
    
    Args:
        schedule_id: 予定ID
    
    Returns:
        予定オブジェクト（存在しない場合はNone）
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row  # 辞書形式でデータを取得
            
            async with db.execute(
                "SELECT * FROM schedules WHERE id = ? AND is_active = TRUE",
                (schedule_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    data = dict(row)
                    # 日時文字列をdatetimeオブジェクトに変換
                    data['start_datetime'] = datetime.fromisoformat(data['start_datetime'])
                    if data['end_datetime']:
                        data['end_datetime'] = datetime.fromisoformat(data['end_datetime'])
                    if data['created_at']:
                        data['created_at'] = datetime.fromisoformat(data['created_at'])
                    if data['updated_at']:
                        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                    
                    return Schedule(data)
                
                return None
                
    except Exception as e:
        logger.error(f"予定取得エラー (ID: {schedule_id}): {e}")
        return None

async def get_schedules_by_user(
    user_id: str,
    guild_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50
) -> List[Schedule]:
    """
    ユーザーの予定一覧を取得
    
    Args:
        user_id: ユーザーID
        guild_id: サーバーID
        start_date: 取得開始日（オプション）
        end_date: 取得終了日（オプション）
        limit: 取得件数の上限
    
    Returns:
        予定リスト
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # クエリの構築
            query = """
                SELECT * FROM schedules 
                WHERE user_id = ? AND guild_id = ? AND is_active = TRUE
            """
            params = [user_id, guild_id]
            
            # 日付範囲の条件追加
            if start_date:
                query += " AND start_datetime >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND start_datetime <= ?"
                params.append(end_date)
            
            query += " ORDER BY start_datetime ASC LIMIT ?"
            params.append(limit)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
                schedules = []
                for row in rows:
                    data = dict(row)
                    # 日時文字列の変換
                    data['start_datetime'] = datetime.fromisoformat(data['start_datetime'])
                    if data['end_datetime']:
                        data['end_datetime'] = datetime.fromisoformat(data['end_datetime'])
                    if data['created_at']:
                        data['created_at'] = datetime.fromisoformat(data['created_at'])
                    if data['updated_at']:
                        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                    
                    schedules.append(Schedule(data))
                
                return schedules
                
    except Exception as e:
        logger.error(f"予定一覧取得エラー (ユーザー: {user_id}): {e}")
        return []

async def get_schedules_by_guild(
    guild_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> List[Schedule]:
    """
    サーバー全体の予定一覧を取得
    
    Args:
        guild_id: サーバーID
        start_date: 取得開始日（オプション）
        end_date: 取得終了日（オプション）
        limit: 取得件数の上限
    
    Returns:
        予定リスト
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            query = """
                SELECT * FROM schedules 
                WHERE guild_id = ? AND is_active = TRUE
            """
            params = [guild_id]
            
            if start_date:
                query += " AND start_datetime >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND start_datetime <= ?"
                params.append(end_date)
            
            query += " ORDER BY start_datetime ASC LIMIT ?"
            params.append(limit)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
                schedules = []
                for row in rows:
                    data = dict(row)
                    data['start_datetime'] = datetime.fromisoformat(data['start_datetime'])
                    if data['end_datetime']:
                        data['end_datetime'] = datetime.fromisoformat(data['end_datetime'])
                    if data['created_at']:
                        data['created_at'] = datetime.fromisoformat(data['created_at'])
                    if data['updated_at']:
                        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                    
                    schedules.append(Schedule(data))
                
                return schedules
                
    except Exception as e:
        logger.error(f"サーバー予定一覧取得エラー (サーバー: {guild_id}): {e}")
        return []

async def update_schedule(
    schedule_id: int,
    user_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None
) -> bool:
    """
    予定を更新
    
    Args:
        schedule_id: 予定ID
        user_id: ユーザーID（権限チェック用）
        title: 新しいタイトル（オプション）
        description: 新しい説明（オプション）
        start_datetime: 新しい開始日時（オプション）
        end_datetime: 新しい終了日時（オプション）
    
    Returns:
        更新成功の可否
    """
    try:
        # 更新項目の構築
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if start_datetime is not None:
            updates.append("start_datetime = ?")
            params.append(start_datetime)
        
        if end_datetime is not None:
            updates.append("end_datetime = ?")
            params.append(end_datetime)
        
        if not updates:
            logger.warning("更新項目が指定されていません")
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([schedule_id, user_id])
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                f"""
                UPDATE schedules 
                SET {', '.join(updates)}
                WHERE id = ? AND user_id = ? AND is_active = TRUE
                """,
                params
            )
            await db.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"予定を更新しました: ID={schedule_id}")
                return True
            else:
                logger.warning(f"予定の更新に失敗（存在しないか権限なし）: ID={schedule_id}")
                return False
                
    except Exception as e:
        logger.error(f"予定更新エラー: {e}")
        return False

async def delete_schedule(schedule_id: int, user_id: str) -> bool:
    """
    予定を削除（論理削除）
    
    Args:
        schedule_id: 予定ID
        user_id: ユーザーID（権限チェック用）
    
    Returns:
        削除成功の可否
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                UPDATE schedules 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND is_active = TRUE
                """,
                (schedule_id, user_id)
            )
            await db.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"予定を削除しました: ID={schedule_id}")
                return True
            else:
                logger.warning(f"予定の削除に失敗（存在しないか権限なし）: ID={schedule_id}")
                return False
                
    except Exception as e:
        logger.error(f"予定削除エラー: {e}")
        return False

# ==================== リマインダー機能 ====================

async def create_reminder(
    schedule_id: int,
    user_id: str,
    guild_id: str,
    channel_id: str,
    remind_datetime: datetime,
    message: Optional[str] = None
) -> int:
    """
    リマインダーを作成
    
    Args:
        schedule_id: 対象予定ID
        user_id: ユーザーID
        guild_id: サーバーID
        channel_id: 通知チャンネルID
        remind_datetime: リマインダー日時
        message: カスタムメッセージ
    
    Returns:
        作成されたリマインダーID
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO reminders (schedule_id, user_id, guild_id, channel_id, remind_datetime, message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (schedule_id, user_id, guild_id, channel_id, remind_datetime, message)
            )
            await db.commit()
            
            reminder_id = cursor.lastrowid
            logger.info(f"リマインダーを作成しました: ID={reminder_id}")
            return reminder_id
            
    except Exception as e:
        logger.error(f"リマインダー作成エラー: {e}")
        raise

async def get_pending_reminders() -> List[Dict[str, Any]]:
    """
    送信待ちのリマインダーを取得
    
    Returns:
        送信待ちリマインダーリスト
    """
    try:
        current_time = datetime.now()
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            async with db.execute(
                """
                SELECT r.*, s.title, s.start_datetime
                FROM reminders r
                JOIN schedules s ON r.schedule_id = s.id
                WHERE r.is_sent = FALSE 
                AND r.remind_datetime <= ?
                AND s.is_active = TRUE
                ORDER BY r.remind_datetime ASC
                """,
                (current_time,)
            ) as cursor:
                rows = await cursor.fetchall()
                
                reminders = []
                for row in rows:
                    data = dict(row)
                    data['remind_datetime'] = datetime.fromisoformat(data['remind_datetime'])
                    data['start_datetime'] = datetime.fromisoformat(data['start_datetime'])
                    reminders.append(data)
                
                return reminders
                
    except Exception as e:
        logger.error(f"リマインダー取得エラー: {e}")
        return []

async def mark_reminder_sent(reminder_id: int) -> bool:
    """
    リマインダーを送信済みにマーク
    
    Args:
        reminder_id: リマインダーID
    
    Returns:
        更新成功の可否
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "UPDATE reminders SET is_sent = TRUE WHERE id = ?",
                (reminder_id,)
            )
            await db.commit()
            
            return cursor.rowcount > 0
            
    except Exception as e:
        logger.error(f"リマインダー更新エラー: {e}")
        return False

# ==================== 一括操作 ====================

async def create_bulk_schedules(schedules_data: List[Dict[str, Any]]) -> List[int]:
    """
    複数の予定を一括作成
    
    Args:
        schedules_data: 予定データのリスト
    
    Returns:
        作成された予定IDのリスト
    """
    try:
        created_ids = []
        
        async with aiosqlite.connect(DB_PATH) as db:
            for data in schedules_data:
                cursor = await db.execute(
                    """
                    INSERT INTO schedules (user_id, guild_id, title, description, start_datetime, end_datetime)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data['user_id'],
                        data['guild_id'],
                        data['title'],
                        data.get('description'),
                        data['start_datetime'],
                        data.get('end_datetime')
                    )
                )
                created_ids.append(cursor.lastrowid)
            
            await db.commit()
            logger.info(f"一括で{len(created_ids)}件の予定を作成しました")
            return created_ids
            
    except Exception as e:
        logger.error(f"一括予定作成エラー: {e}")
        return []
