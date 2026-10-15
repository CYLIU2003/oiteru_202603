"""
OITELU データビューアー
読み取り専用モードでデータベースを参照・分析するツール
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os

class OITELUDataViewer:
    def __init__(self, db_path='oiteru.sqlite3'):
        """データベースに接続（読み取り専用）"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"データベースが見つかりません: {db_path}")
        
        # 読み取り専用モードで接続
        self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.conn.row_factory = sqlite3.Row
        print(f"✓ データベースに接続しました: {db_path}")
    
    def get_user_summary(self):
        """ユーザーサマリーを取得"""
        cursor = self.conn.cursor()
        
        # 総ユーザー数
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        # 有効ユーザー数
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE allow = 1")
        active_users = cursor.fetchone()['active']
        
        # 総利用回数
        cursor.execute("SELECT SUM(total) as sum_total FROM users")
        total_usage = cursor.fetchone()['sum_total'] or 0
        
        # 今日の利用回数
        cursor.execute("SELECT SUM(today) as sum_today FROM users")
        today_usage = cursor.fetchone()['sum_today'] or 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_usage': total_usage,
            'today_usage': today_usage
        }
    
    def get_all_users(self):
        """全ユーザーデータを取得"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY total DESC")
        return cursor.fetchall()
    
    def get_unit_summary(self):
        """子機サマリーを取得"""
        cursor = self.conn.cursor()
        
        # 総子機数
        cursor.execute("SELECT COUNT(*) as total FROM units")
        total_units = cursor.fetchone()['total']
        
        # 利用可能な子機数
        cursor.execute("SELECT COUNT(*) as available FROM units WHERE available = 1")
        available_units = cursor.fetchone()['available']
        
        # 総在庫数
        cursor.execute("SELECT SUM(stock) as total_stock FROM units")
        total_stock = cursor.fetchone()['total_stock'] or 0
        
        return {
            'total_units': total_units,
            'available_units': available_units,
            'total_stock': total_stock
        }
    
    def get_usage_history(self, limit=100):
        """利用履歴を取得"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM history 
            WHERE txt LIKE '%利用を記録しました%'
            ORDER BY id DESC 
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()
    
    def export_users_to_excel(self, filename='users_export.xlsx'):
        """ユーザーデータをExcelに出力"""
        users = self.get_all_users()
        
        # データを辞書のリストに変換
        data = []
        for user in users:
            data.append({
                'ID': user['id'],
                'カードID': user['card_id'],
                '利用許可': '許可' if user['allow'] else '不許可',
                '登録日時': user['entry'],
                '残り在庫': user['stock'],
                '今日の利用': user['today'],
                '総利用回数': user['total']
            })
        
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"✓ ユーザーデータを {filename} に出力しました")
        return filename
    
    def export_usage_stats_to_excel(self, filename='usage_stats.xlsx'):
        """利用統計をExcelに出力"""
        cursor = self.conn.cursor()
        
        # 利用履歴から統計を作成
        cursor.execute("""
            SELECT txt FROM history 
            WHERE txt LIKE '%] 利用を記録しました%'
        """)
        
        logs = cursor.fetchall()
        
        # 時間帯別、曜日別の集計
        hourly_stats = [0] * 24
        daily_stats = {}
        
        for log in logs:
            txt = log['txt']
            # 日時を抽出（例: "2025-01-15 10:30: ..."）
            try:
                date_str = txt.split(':')[0]
                dt = datetime.strptime(date_str, "%Y-%m-%d %H")
                
                # 時間帯別
                hourly_stats[dt.hour] += 1
                
                # 日別
                date_key = dt.strftime("%Y-%m-%d")
                daily_stats[date_key] = daily_stats.get(date_key, 0) + 1
            except:
                continue
        
        # DataFrameに変換
        hourly_df = pd.DataFrame({
            '時間帯': [f"{h:02d}:00" for h in range(24)],
            '利用回数': hourly_stats
        })
        
        daily_df = pd.DataFrame([
            {'日付': k, '利用回数': v} 
            for k, v in sorted(daily_stats.items())
        ])
        
        # Excelに複数シートで出力
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            hourly_df.to_excel(writer, sheet_name='時間帯別', index=False)
            daily_df.to_excel(writer, sheet_name='日別', index=False)
        
        print(f"✓ 利用統計を {filename} に出力しました")
        return filename
    
    def print_summary(self):
        """サマリーをコンソールに表示"""
        print("\n" + "="*60)
        print("OITELU システムサマリー")
        print("="*60)
        
        # ユーザーサマリー
        user_summary = self.get_user_summary()
        print("\n📊 ユーザー統計:")
        print(f"  総ユーザー数:     {user_summary['total_users']}")
        print(f"  有効ユーザー数:   {user_summary['active_users']}")
        print(f"  総利用回数:       {user_summary['total_usage']}")
        print(f"  今日の利用回数:   {user_summary['today_usage']}")
        
        # 子機サマリー
        unit_summary = self.get_unit_summary()
        print("\n🖥️  子機統計:")
        print(f"  総子機数:         {unit_summary['total_units']}")
        print(f"  利用可能子機数:   {unit_summary['available_units']}")
        print(f"  総在庫数:         {unit_summary['total_stock']}")
        
        print("\n" + "="*60 + "\n")
    
    def close(self):
        """データベース接続を閉じる"""
        self.conn.close()
        print("✓ データベース接続を閉じました")

def main():
    """メイン処理"""
    import sys
    
    # コマンドライン引数の処理
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python data_viewer.py summary              # サマリー表示")
        print("  python data_viewer.py export-users         # ユーザーをExcel出力")
        print("  python data_viewer.py export-stats         # 統計をExcel出力")
        print("  python data_viewer.py export-all           # 全てをExcel出力")
        return
    
    command = sys.argv[1]
    
    # データベースパスの指定（オプション）
    db_path = sys.argv[2] if len(sys.argv) > 2 else 'oiteru.sqlite3'
    
    try:
        viewer = OITELUDataViewer(db_path)
        
        if command == 'summary':
            viewer.print_summary()
        
        elif command == 'export-users':
            filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            viewer.export_users_to_excel(filename)
        
        elif command == 'export-stats':
            filename = f"usage_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            viewer.export_usage_stats_to_excel(filename)
        
        elif command == 'export-all':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            viewer.export_users_to_excel(f"users_{timestamp}.xlsx")
            viewer.export_usage_stats_to_excel(f"stats_{timestamp}.xlsx")
            print("\n✓ 全てのデータを出力しました")
        
        else:
            print(f"エラー: 不明なコマンド '{command}'")
        
        viewer.close()
    
    except FileNotFoundError as e:
        print(f"エラー: {e}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
