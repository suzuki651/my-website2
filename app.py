import sqlite3
import datetime
import os
from typing import List, Dict, Union
from flask import Flask, render_template, request, redirect, url_for

# アプリケーションの初期化
app = Flask(__name__)

# データベースのパスを設定（Azure対応）
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

# データベースの初期設定
def init_db() -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS punch_cards (
            id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            check_in_time TEXT,
            check_out_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

# アプリケーション起動時にデータベースを初期化
init_db()

# --- スマホ用打刻アプリ ---
@app.route('/')
def index():
    return render_template('index.html')

# 打刻処理
@app.route('/punch', methods=['POST'])
def punch():
    employee_name: str = request.form['employee_name']
    action: str = request.form['action']
    current_time: str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    if action == 'check_in':
        # 出勤打刻：新しいレコードを作成
        c.execute('INSERT INTO punch_cards (employee_name, check_in_time) VALUES (?, ?)', 
                 (employee_name, current_time))
    elif action == 'check_out':
        # 退勤打刻：最新の出勤レコードを更新
        # まず、未打刻の最新の出勤レコードを探す
        c.execute('SELECT id FROM punch_cards WHERE employee_name = ? AND check_out_time IS NULL ORDER BY id DESC LIMIT 1', 
                 (employee_name,))
        latest_id = c.fetchone()
        
        if latest_id:
            # 最新のレコードがあれば、そのレコードを更新
            c.execute('UPDATE punch_cards SET check_out_time = ? WHERE id = ?', 
                     (current_time, latest_id[0]))
    
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# --- PC用管理アプリ ---
@app.route('/admin')
def admin():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM punch_cards ORDER BY id DESC')
    punch_cards = c.fetchall()
    conn.close()
    
    # データを表示用に整形
    processed_data: List[Dict[str, Union[int, str]]] = []
    
    for row in punch_cards:
        # 型を明示的に変換
        record_id: int = int(row[0]) if row[0] is not None else 0
        employee_name: str = str(row[1]) if row[1] is not None else ''
        check_in_time: str = str(row[2]) if row[2] is not None else '未打刻'
        check_out_time: str = str(row[3]) if row[3] is not None else '未打刻'
        
        # 辞書を作成
        record: Dict[str, Union[int, str]] = {
            'id': record_id,
            'employee_name': employee_name,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time
        }
        
        processed_data.append(record)
    
    return render_template('admin.html', punch_cards=processed_data)

# ヘルスチェックエンドポイント（Azure用）
@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    # Azure App Serviceでは環境変数PORTが設定される
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)