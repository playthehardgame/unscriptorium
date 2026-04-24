import sqlite3
import amazon.ion.simpleion as ion
import io, json

def ion_to_dict(val):
    """Convert Ion value to Python dict/list/str for display."""
    if hasattr(val, 'items'):  # struct/dict
        return {str(k): ion_to_dict(v) for k, v in val.items()}
    elif hasattr(val, '__iter__') and not isinstance(val, (str, bytes)):
        try:
            return [ion_to_dict(x) for x in val]
        except:
            return str(val)
    elif isinstance(val, bytes):
        return val.hex()
    else:
        return str(val)

def decode_blob(blob_bytes, label=''):
    """Decode an Amazon Ion binary blob."""
    try:
        result = ion.loads(blob_bytes, single_value=False)
        return result
    except Exception as e:
        return f'Error: {e}'

for book_id in ['B07RZYBHB8!!EBOK!!notebook', 'B09Q361YM5!!EBOK!!notebook']:
    db_path = f'M:/TEMP/notebooks/{book_id}/nbk_fixed.db'
    print(f'\n{"="*70}')
    print(f'BOOK: {book_id}')
    print(f'{"="*70}')

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Read all blobs from both tables
    for table, id_col in [('fragments', 'id'), ('local_delta_fragments', 'id')]:
        cur.execute(f'SELECT {id_col}, payload_type, payload_value FROM "{table}"')
        rows = cur.fetchall()
        for row_id, ptype, blob in rows:
            if blob is None:
                continue
            print(f'\n--- {table}/{row_id} (type={ptype}, {len(blob)} bytes) ---')
            decoded = decode_blob(blob, row_id)
            if isinstance(decoded, list):
                for item in decoded:
                    try:
                        d = ion_to_dict(item)
                        print(json.dumps(d, indent=2, ensure_ascii=False)[:2000])
                    except:
                        print(f'  {item}')
            else:
                print(decoded)

    conn.close()
