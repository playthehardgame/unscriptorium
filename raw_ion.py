import sqlite3

for book_id in ['B07RZYBHB8!!EBOK!!notebook', 'B09Q361YM5!!EBOK!!notebook']:
    db_path = f'M:/TEMP/notebooks/{book_id}/nbk_fixed.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print(f'\n=== {book_id} ===')
    cur.execute('SELECT id, payload_value FROM fragments')
    rows = cur.fetchall()
    for row_id, blob in rows:
        if blob:
            print(f'\n--- {row_id} ({len(blob)} bytes) ---')
            print(f'hex: {blob.hex()}')
            # Also try to find any ASCII text in the blob
            import re
            texts = re.findall(b'[\x20-\x7e]{3,}', blob)
            if texts:
                print(f'readable: {[t.decode() for t in texts[:20]]}')

    cur.execute('SELECT id, payload_value FROM local_delta_fragments')
    rows = cur.fetchall()
    for row_id, blob in rows:
        if blob:
            print(f'\n--- local_delta/{row_id} ({len(blob)} bytes) ---')
            print(f'hex: {blob[:100].hex()}')
            import re
            texts = re.findall(b'[\x20-\x7e]{3,}', blob)
            if texts:
                print(f'readable: {[t.decode() for t in texts[:20]]}')

    conn.close()
