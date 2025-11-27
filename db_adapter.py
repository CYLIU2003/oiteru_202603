"""
データベース抽張化レイヤー
SQLiteとMySQLの両方をサポート
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

# 環境変数からデータベースタイプを取得
DB_TYPE = os.getenv('DB_TYPE', 'sqlite').lower()

if DB_TYPE == 'mysql':
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    from MySQLdb.cursors import DictCursor
    # MySQLのIntegrityErrorを使用
    DatabaseError = MySQLdb.IntegrityError
else:
    # SQLiteのIntegrityErrorを使用
    DatabaseError = sqlite3.IntegrityError

class DatabaseConnection:
    """データベース接続を管理するクラス"""
    
    def __init__(self):
        self.db_type = DB_TYPE
        
        if self.db_type == 'mysql':
            self.config = {
                'host': os.getenv('MYSQL_HOST', 'localhost'),
                'port': int(os.getenv('MYSQL_PORT', 3306)),
                'user': os.getenv('MYSQL_USER', 'oiteru_user'),
                'password': os.getenv('MYSQL_PASSWORD', 'oiteru_password_2025'),
                'database': os.getenv('MYSQL_DATABASE', 'oiteru'),
                'charset': 'utf8mb4',
                'cursorclass': DictCursor,
                'autocommit': False
            }
        else:
            # SQLite
            self.db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                'oiteru.sqlite3'
            )
    
    @contextmanager
    def get_connection(self):
        """データベース接続を取得（コンテキストマネージャー）"""
        if self.db_type == 'mysql':
            conn = MySQLdb.connect(**self.config)
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
        
        try:
            yield conn
        finally:
            conn.close()
    
    def get_cursor(self, conn):
        """カーソルを取得"""
        if self.db_type == 'mysql':
            return conn.cursor()
        else:
            return conn.cursor()
    
    def execute(self, conn, query: str, params: Optional[Tuple] = None) -> Any:
        """クエリを実行"""
        cursor = self.get_cursor(conn)
        
        # MySQLの場合、プレースホルダーを%sに変換
        if self.db_type == 'mysql' and '?' in query:
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
        
        if result is None:
            return None
        
        # SQLiteのRow型をdictに変換
        if self.db_type == 'sqlite' and hasattr(result, 'keys'):
            return dict(result)
        
        return result
    
    def fetchall(self, conn, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        """全行取得"""
        cursor = self.execute(conn, query, params)
        results = cursor.fetchall()
        cursor.close()
        
        # SQLiteのRow型をdictに変換
        if self.db_type == 'sqlite' and results:
            return [dict(row) for row in results]
        
        return results if results else []
    
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

# 初期化時にデータベースタイプを表示
print(f"Database Type: {DB_TYPE.upper()}")
if DB_TYPE == 'mysql':
    print(f"MySQL Host: {os.getenv('MYSQL_HOST', 'localhost')}")
    print(f"MySQL Database: {os.getenv('MYSQL_DATABASE', 'oiteru')}")
else:
    print(f"SQLite Database: {db.db_path}")
