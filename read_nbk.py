import sqlite3
import json

for book_id in ['B07RZYBHB8!!EBOK!!notebook', 'B09Q361YM5!!EBOK!!notebook']:
    path = f'M:/TEMP/notebooks/{book_id}/nbk'
    print(f'\n=== {book_id} ===')
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name, type, sql FROM sqlite_master")
        schema = cur.fetchall()
        print('Schema:')
        for s in schema:
            print(' ', s)

        tables = [s[0] for s in schema if s[1] == 'table']
        for t in tables:
            try:
                cur.execute(f'PRAGMA table_info("{t}")')
                cols = [c[1] for c in cur.fetchall()]
                print(f'\nTable {t}: columns={cols}')
                cur.execute(f'SELECT * FROM "{t}"')
                rows = cur.fetchall()
                print(f'  Rows: {len(rows)}')
                for r in rows[:5]:
                    print(' ', r)
            except Exception as e:
                print(f'  Error reading {t}: {e}')
        conn.close()
    except Exception as e:
        print(f'Error: {e}')
