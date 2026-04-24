import sqlite3, struct, re

def read_db(db_path, label):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print(f'\n{"="*60}')
    print(f'DATABASE: {label}')
    print(f'{"="*60}')

    for table in ['capabilities', 'fragments', 'fragment_properties', 'local_delta_fragments', 'local_action_fragments']:
        cur.execute(f'SELECT * FROM "{table}"')
        rows = cur.fetchall()
        cur.execute(f'PRAGMA table_info("{table}")')
        cols = [c[1] for c in cur.fetchall()]
        print(f'\n--- Table: {table} ({len(rows)} rows, cols: {cols}) ---')
        for row in rows[:20]:
            display = []
            for i, val in enumerate(row):
                if isinstance(val, bytes):
                    # Try to decode blob as text first
                    display.append(f'{cols[i]}=<BLOB {len(val)}b: {val[:30].hex()}>')
                else:
                    display.append(f'{cols[i]}={repr(val)[:80]}')
            print(' ', ' | '.join(display))

    conn.close()

for book_id in ['B07RZYBHB8!!EBOK!!notebook', 'B09Q361YM5!!EBOK!!notebook']:
    db_path = f'M:/TEMP/notebooks/{book_id}/nbk_fixed.db'
    read_db(db_path, book_id)
