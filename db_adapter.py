"""
データベース接続レイヤー（MySQL 8 専用）

SQLite は廃止しました。DB_TYPE を省略すると mysql として扱い、
mysql 以外が指定されていたら起動時にエラーで止めます。
（設定ミスのまま、本番とは別の空 DB に黙って書き込むのを防ぐため）
"""

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)

DB_TYPE = (os.getenv('DB_TYPE') or 'mysql').strip().lower()
if DB_TYPE != 'mysql':
    raise RuntimeError(
        f"DB_TYPE={DB_TYPE} には対応していません。OITERU は MySQL 8 専用です"
        "（SQLite は廃止しました）。.env の DB_TYPE を mysql にしてください。"
    )

DatabaseError = pymysql.IntegrityError


class DatabaseConnection:
    """データベース接続を管理するクラス"""

    def __init__(self):
        self.db_type = DB_TYPE

    def _mysql_config(self):
        return {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'oiteru_user'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'oiteru'),
            'charset': 'utf8mb4',
            'cursorclass': DictCursor,
            'autocommit': False
        }
    
    @contextmanager
    def get_connection(self):
        """データベース接続を取得（コンテキストマネージャー）"""
        conn = None
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                conn = pymysql.connect(**self._mysql_config())
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    import time
                    logger.warning(
                        "DB接続失敗 (試行 %d/%d): %s", attempt + 1, max_retries, type(e).__name__
                    )
                    time.sleep(retry_delay)
                else:
                    raise
        
        try:
            yield conn
            conn.commit()  # 正常終了時はコミット
        except Exception:
            if conn:
                conn.rollback()  # エラー時はロールバック
            raise
        finally:
            if conn:
                conn.close()
    
    def get_cursor(self, conn):
        """カーソルを取得"""
        return conn.cursor()
    
    def execute(self, conn, query: str, params: Optional[Tuple] = None) -> Any:
        """クエリを実行"""
        cursor = self.get_cursor(conn)
        
        # 既存コードの ? プレースホルダーを MySQL の %s に変換
        if '?' in query:
            query = query.replace('?', '%s')
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        return cursor
    
    def fetchone(self, conn, query: str, params: Optional[Tuple] = None) -> Optional[Dict]:
        """1行取得"""
        cursor = self.execute(conn, query, params)
        result = cursor.fetchone()
        cursor.close()
        
        return result
    
    def fetchall(self, conn, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        """全行取得"""
        cursor = self.execute(conn, query, params)
        results = cursor.fetchall()
        cursor.close()
        
        return list(results) if results else []
    
    def insert(self, conn, query: str, params: Optional[Tuple] = None) -> int:
        """INSERT文を実行し、挿入されたIDを返す"""
        cursor = self.execute(conn, query, params)
        last_id = cursor.lastrowid
        cursor.close()
        return last_id
    
    def update(self, conn, query: str, params: Optional[Tuple] = None) -> int:
        """UPDATE文を実行し、影響を受けた行数を返す"""
        cursor = self.execute(conn, query, params)
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount
    
    def delete(self, conn, query: str, params: Optional[Tuple] = None) -> int:
        """DELETE文を実行し、削除された行数を返す"""
        cursor = self.execute(conn, query, params)
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount
    
    def commit(self, conn):
        """トランザクションをコミット"""
        conn.commit()
    
    def rollback(self, conn):
        """トランザクションをロールバック"""
        conn.rollback()

# グローバルインスタンス
db = DatabaseConnection()

# 使いやすいヘルパー関数
def get_connection():
    """データベース接続を取得"""
    return db.get_connection()

def execute_query(query: str, params: Optional[Tuple] = None, fetch: str = 'none'):
    """
    クエリを実行する便利関数
    
    Args:
        query: SQL文
        params: パラメータ
        fetch: 'one', 'all', 'none'
    """
    with db.get_connection() as conn:
        if fetch == 'one':
            result = db.fetchone(conn, query, params)
            db.commit(conn)
            return result
        elif fetch == 'all':
            result = db.fetchall(conn, query, params)
            db.commit(conn)
            return result
        else:
            db.execute(conn, query, params)
            db.commit(conn)
            return None

def get_db_type():
    """現在のデータベースタイプを取得"""
    return DB_TYPE

logger.info(
    "Database: MySQL host=%s database=%s",
    os.getenv('MYSQL_HOST', 'localhost'),
    os.getenv('MYSQL_DATABASE', 'oiteru'),
)
