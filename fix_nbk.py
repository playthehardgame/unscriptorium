import struct, sqlite3, os

def fix_nbk(input_path, output_path):
    """
    The NBK file has a non-standard layout:
    - Bytes 0-1023: Prefix containing SQLite file header (0-99) + B-tree header (100-107)
                    + cell pointers (108-123) + zeros
    - Bytes 1024-5119: Page 1 actual cell content area (4096 bytes)
    - Bytes 5120-37887: Pages 2-9 (standard 4096-byte SQLite pages)

    Cell pointers in the B-tree header reference offsets within the content area.
    We reconstruct a valid 4096-byte page 1 that combines these.
    """
    with open(input_path, 'rb') as f:
        data = f.read()

    page_size = struct.unpack('>H', data[16:18])[0]  # 4096
    prefix_size = 1024

    # B-tree page header is at file[100:108], cell pointers at file[108:124]
    # Content start within content area
    btree_b = 100
    content_start = struct.unpack('>H', data[btree_b+5:btree_b+7])[0]

    print(f'Page size: {page_size}')
    print(f'B-tree content_start: {content_start}')
    print(f'File size: {len(data)}, Expected: {(len(data) - prefix_size)} = {(len(data) - prefix_size) // page_size} pages')

    # Build new page 1 (4096 bytes)
    new_page1 = bytearray(page_size)
    # Copy SQLite file header + B-tree header + cell pointers (first 124 bytes)
    new_page1[0:124] = data[0:124]
    # Copy cell content from content area (starts at content_start within 4096-byte area)
    content_area_start = prefix_size  # file offset 1024
    cell_content_file_offset = content_area_start + content_start
    cell_content_bytes = page_size - content_start  # = 4096 - 3077 = 1019
    new_page1[content_start:page_size] = data[cell_content_file_offset:cell_content_file_offset + cell_content_bytes]

    # Pages 2-9 start at file offset prefix_size + page_size = 1024 + 4096 = 5120
    pages_2_to_9_start = prefix_size + page_size  # 5120
    pages_2_to_9 = data[pages_2_to_9_start:]

    # Write reconstructed file
    with open(output_path, 'wb') as f:
        f.write(bytes(new_page1))
        f.write(pages_2_to_9)

    print(f'Written {len(new_page1) + len(pages_2_to_9)} bytes to {output_path}')

    # Verify
    try:
        conn = sqlite3.connect(output_path)
        cur = conn.cursor()
        cur.execute("SELECT type, name, tbl_name, rootpage FROM sqlite_master")
        rows = cur.fetchall()
        print(f'\nSchema ({len(rows)} entries):')
        for r in rows:
            print(f'  {r}')
        conn.close()
        return True
    except Exception as e:
        print(f'Verification error: {e}')
        return False

# Process both files
for book_id in ['B07RZYBHB8!!EBOK!!notebook', 'B09Q361YM5!!EBOK!!notebook']:
    input_path = f'M:/TEMP/notebooks/{book_id}/nbk'
    output_path = f'M:/TEMP/notebooks/{book_id}/nbk_fixed.db'
    print(f'\n{"="*60}')
    print(f'Processing: {book_id}')
    fix_nbk(input_path, output_path)
