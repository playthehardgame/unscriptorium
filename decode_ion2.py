import sqlite3
import amazon.ion.simpleion as ion
import amazon.ion.core as ion_core
import io

def decode_with_symtable(symtable_blob, data_blob):
    """Decode a blob using the given symbol table blob."""
    # Prepend the symbol table blob to the data blob
    combined = symtable_blob + data_blob
    try:
        results = list(ion.loads(combined, single_value=False))
        return results
    except Exception as e:
        return f'Combined decode error: {e}'

def decode_raw(blob):
    """Try to decode raw Ion binary, dumping symbol table info."""
    reader = ion.loads(blob, single_value=False)
    results = []
    try:
        for item in ion.loads(blob, single_value=False):
            results.append(item)
        return results
    except Exception as e:
        return str(e)

for book_id in ['B07RZYBHB8!!EBOK!!notebook', 'B09Q361YM5!!EBOK!!notebook']:
    db_path = f'M:/TEMP/notebooks/{book_id}/nbk_fixed.db'
    print(f'\n{"="*70}')
    print(f'BOOK: {book_id}')

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get symbol table blobs
    symtable_blobs = {}
    for table in ['fragments', 'local_delta_fragments']:
        cur.execute(f'SELECT id, payload_value FROM "{table}" WHERE id = "$ion_symbol_table"')
        r = cur.fetchone()
        if r:
            symtable_blobs[table] = r[1]
            print(f'Found symbol table in {table}: {len(r[1])} bytes')

    # Decode symbol table to see what symbols are defined
    for tbl, stblob in symtable_blobs.items():
        print(f'\nSymbol table from {tbl}:')
        try:
            result = list(ion.loads(stblob, single_value=False))
            for item in result:
                if hasattr(item, 'items'):
                    print('  Struct fields:')
                    for k, v in item.items():
                        print(f'    {k}: {str(v)[:200]}')
                else:
                    print(f'  Value: {str(item)[:200]}')
        except Exception as e:
            print(f'  Error: {e}')

    # Try combined decode for other fragments
    for table in ['fragments']:
        cur.execute(f'SELECT id, payload_type, payload_value FROM "{table}" WHERE id != "$ion_symbol_table"')
        rows = cur.fetchall()
        for row_id, ptype, blob in rows:
            if blob is None:
                continue
            print(f'\n--- {table}/{row_id} ---')
            # Try each symbol table
            for stbl_name, stblob in symtable_blobs.items():
                combined = stblob + blob
                try:
                    result = list(ion.loads(combined, single_value=False))
                    print(f'  Decoded with symtable from {stbl_name}:')
                    for item in result:
                        if hasattr(item, 'items'):
                            for k, v in item.items():
                                print(f'    {k}: {str(v)[:300]}')
                        else:
                            print(f'  {str(item)[:300]}')
                    break
                except Exception as e:
                    print(f'  Error with {stbl_name}: {e}')

    conn.close()
