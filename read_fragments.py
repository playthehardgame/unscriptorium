import sqlite3
import struct

def read_table(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table_name}")')
    cols = [c[1] for c in cur.fetchall()]
    cur.execute(f'SELECT * FROM "{table_name}"')
    rows = cur.fetchall()
    conn.close()
    return cols, rows

for book_id in ['B07RZYBHB8!!EBOK!!notebook', 'B09Q361YM5!!EBOK!!notebook']:
    path = f'M:/TEMP/notebooks/{book_id}/nbk'
    print(f'\n{"="*60}')
    print(f'Book: {book_id}')
    print(f'{"="*60}')

    for table in ['fragments', 'local_delta_fragments', 'local_action_fragments', 'fragment_properties', 'capabilities']:
        try:
            cols, rows = read_table(path, table)
            print(f'\n--- Table: {table} ({len(rows)} rows) ---')
            print(f'Columns: {cols}')
            for row in rows[:10]:
                row_info = []
                for i, val in enumerate(row):
                    if isinstance(val, bytes):
                        row_info.append(f'{cols[i]}=<blob {len(val)} bytes, hex: {val[:20].hex()}>')
                    else:
                        row_info.append(f'{cols[i]}={repr(val)}')
                print(' ', ', '.join(row_info))
        except Exception as e:
            print(f'  Error on {table}: {e}')
