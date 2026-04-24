import sqlite3, struct, os, re

def fix_nbk_bytes(data):
    page_size = struct.unpack('>H', data[16:18])[0]
    btree_b = 100
    content_start = struct.unpack('>H', data[btree_b+5:btree_b+7])[0]
    prefix_size = 1024
    new_page1 = bytearray(page_size)
    new_page1[0:124] = data[0:124]
    cell_content_file_offset = prefix_size + content_start
    cell_content_bytes = page_size - content_start
    new_page1[content_start:page_size] = data[cell_content_file_offset:cell_content_file_offset + cell_content_bytes]
    pages_rest = data[prefix_size + page_size:]
    return bytes(new_page1) + pages_rest

def get_book_id(db_fixed_bytes):
    """Extract book_id from book_metadata fragment."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp.write(db_fixed_bytes)
        tmp_path = tmp.name
    try:
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute('SELECT payload_value FROM fragments WHERE id="book_metadata"')
        r = cur.fetchone()
        conn.close()
        os.unlink(tmp_path)
        if r and r[0]:
            blob = r[0]
            # Extract readable text from the blob
            texts = re.findall(b'[\x20-\x7e]{4,}', blob)
            return [t.decode() for t in texts]
    except:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
    return []

def extract_all_strings(db_fixed_bytes):
    """Extract all readable strings from all large blobs."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp.write(db_fixed_bytes)
        tmp_path = tmp.name
    result = {}
    try:
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        # Get large content blobs (not system fragments)
        cur.execute('''SELECT id, payload_value FROM fragments
                       WHERE id NOT IN ("$ion_symbol_table", "book_navigation")
                       AND length(payload_value) > 50
                       ORDER BY length(payload_value) DESC''')
        rows = cur.fetchall()
        for fid, blob in rows:
            if blob:
                texts = re.findall(b'[\x20-\x7e]{4,}', blob)
                readable = [t.decode() for t in texts if not t.startswith(b'\xe0')]
                if readable:
                    result[fid] = readable
        conn.close()
    except Exception as e:
        result['_error'] = str(e)
    finally:
        os.unlink(tmp_path) if os.path.exists(tmp_path) else None
    return result

# Process all UUID notebooks
notebooks_dir = 'M:/TEMP/notebooks'
uuid_dirs = sorted([d for d in os.listdir(notebooks_dir)
                    if os.path.isdir(os.path.join(notebooks_dir, d))
                    and re.match(r'^[0-9a-f-]{36}$', d)])

print(f'Processing {len(uuid_dirs)} UUID notebooks...\n')

notebooks_summary = []
for d in uuid_dirs:
    nbk_path = os.path.join(notebooks_dir, d, 'nbk')
    if not os.path.exists(nbk_path):
        continue
    with open(nbk_path, 'rb') as f:
        data = f.read()
    if len(data) < 100 or data[:4] != b'SQLi':
        continue
    try:
        fixed = fix_nbk_bytes(data)
        book_info = get_book_id(fixed)
        strings = extract_all_strings(fixed)

        # Collect interesting strings (skip pure binary noise)
        meaningful = {}
        for fid, texts in strings.items():
            good = [t for t in texts if len(t) > 5 and not all(c in '0123456789abcdefABCDEF-_' for c in t)]
            if good:
                meaningful[fid] = good

        if book_info or meaningful:
            notebooks_summary.append({
                'id': d,
                'book_info': book_info,
                'meaningful_strings': meaningful
            })
    except Exception as e:
        pass

print(f'Found {len(notebooks_summary)} notebooks with content\n')
for nb in notebooks_summary:
    print(f'\n{"="*60}')
    print(f'Notebook: {nb["id"]}')
    if nb['book_info']:
        print(f'Book info: {nb["book_info"]}')
    for fid, texts in nb['meaningful_strings'].items():
        print(f'  [{fid}]: {texts[:5]}')
