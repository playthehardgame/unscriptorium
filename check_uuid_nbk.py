import sqlite3, struct, os, re

def fix_nbk_bytes(data):
    """Fix the 1024-byte offset issue and return corrected SQLite bytes."""
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

def get_nbk_info(nbk_path):
    """Read key info from an NBK file."""
    try:
        with open(nbk_path, 'rb') as f:
            data = f.read()
        if len(data) < 100 or data[:4] != b'SQLi':
            return None

        fixed = fix_nbk_bytes(data)

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp.write(fixed)
            tmp_path = tmp.name

        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()

        # Count rows in each table
        info = {}
        for table in ['fragments', 'local_delta_fragments', 'local_action_fragments', 'fragment_properties']:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            info[table] = cur.fetchone()[0]

        # Get fragment IDs
        cur.execute('SELECT id, payload_type, length(payload_value) FROM fragments')
        info['fragment_ids'] = cur.fetchall()

        cur.execute('SELECT id, payload_type, length(payload_value) FROM local_delta_fragments')
        info['delta_ids'] = cur.fetchall()

        conn.close()
        os.unlink(tmp_path)
        return info
    except Exception as e:
        return {'error': str(e)}

# Check a sample of UUID directories
notebooks_dir = 'M:/TEMP/notebooks'
uuid_dirs = [d for d in os.listdir(notebooks_dir)
             if os.path.isdir(os.path.join(notebooks_dir, d))
             and re.match(r'^[0-9a-f-]{36}$', d)]

print(f'Total UUID directories: {len(uuid_dirs)}')

# Find ones with actual content
with_content = []
for d in uuid_dirs[:50]:  # Check first 50
    nbk_path = os.path.join(notebooks_dir, d, 'nbk')
    if os.path.exists(nbk_path):
        info = get_nbk_info(nbk_path)
        if info and 'error' not in info:
            total_rows = sum(v for k, v in info.items() if k.endswith('s') and isinstance(v, int))
            if info.get('fragments', 0) > 1 or info.get('local_delta_fragments', 0) > 0:
                with_content.append((d, info))
                print(f'\n{d}: frags={info["fragments"]}, deltas={info["local_delta_fragments"]}')
                print(f'  Fragment IDs: {info["fragment_ids"]}')
                print(f'  Delta IDs: {info["delta_ids"][:3]}')

print(f'\n\nDirectories with content: {len(with_content)}')
