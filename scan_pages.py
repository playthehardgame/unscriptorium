import struct

def read_varint(data, pos):
    result = 0
    for i in range(9):
        if pos + i >= len(data):
            return 0, pos
        byte = data[pos + i]
        if i < 8:
            result = (result << 7) | (byte & 0x7f)
            if not (byte & 0x80):
                return result, pos + i + 1
        else:
            result = (result << 8) | byte
            return result, pos + i + 1
    return result, pos + 9

def try_parse_leaf_page(data, page_start, page_size, header_offset=0):
    """Try to parse a leaf table B-tree page starting at page_start in data."""
    h = page_start + header_offset
    if h >= len(data) or data[h] != 0x0D:
        return None

    try:
        num_cells = struct.unpack('>H', data[h+3:h+5])[0]
        if num_cells == 0 or num_cells > 500:
            return None
        content_start = struct.unpack('>H', data[h+5:h+7])[0]
        if content_start == 0:
            content_start = 65536

        # Read cell pointers
        cell_ptrs = []
        for i in range(num_cells):
            ptr = struct.unpack('>H', data[h+8+i*2:h+8+i*2+2])[0]
            cell_ptrs.append(ptr)

        records = []
        for ptr in cell_ptrs:
            # cell offset is relative to start of page
            cell_abs = page_start + ptr
            if cell_abs >= len(data):
                continue
            payload_size, p = read_varint(data, cell_abs)
            if payload_size == 0 or payload_size > 50000:
                continue
            row_id, p = read_varint(data, p)

            # Parse record header
            hdr_start = p
            hdr_size, p = read_varint(data, p)
            if hdr_size == 0 or hdr_size > 1000:
                continue
            hdr_end = hdr_start + hdr_size

            serial_types = []
            while p < hdr_end:
                st, p = read_varint(data, p)
                serial_types.append(st)

            values = []
            p = hdr_end
            for st in serial_types:
                if st == 0:
                    values.append(None)
                elif 1 <= st <= 4:
                    n = st
                    if p + n > len(data):
                        break
                    val = int.from_bytes(data[p:p+n], 'big', signed=True)
                    values.append(val)
                    p += n
                elif st == 5:
                    if p + 6 > len(data):
                        break
                    val = int.from_bytes(b'\x00\x00' + data[p:p+6], 'big', signed=True)
                    values.append(val)
                    p += 6
                elif st == 6:
                    if p + 8 > len(data):
                        break
                    val = struct.unpack('>q', data[p:p+8])[0]
                    values.append(val)
                    p += 8
                elif st == 8:
                    values.append(0)
                elif st == 9:
                    values.append(1)
                elif st >= 12 and st % 2 == 0:
                    n = (st - 12) // 2
                    if p + n > len(data):
                        break
                    values.append(('blob', data[p:p+n]))
                    p += n
                elif st >= 13 and st % 2 == 1:
                    n = (st - 13) // 2
                    if p + n > len(data):
                        break
                    try:
                        values.append(data[p:p+n].decode('utf-8'))
                    except:
                        values.append(('raw', data[p:p+n]))
                    p += n
                else:
                    values.append(f'<st={st}>')

            if values:
                records.append((row_id, values))

        return records
    except Exception as e:
        return None

path = 'M:/TEMP/notebooks/B07RZYBHB8!!EBOK!!notebook/nbk'
with open(path, 'rb') as f:
    data = f.read()

page_size = struct.unpack('>H', data[16:18])[0]
num_pages_hdr = struct.unpack('>I', data[28:32])[0]
print(f'Page size: {page_size}, Pages in header: {num_pages_hdr}')
print(f'File size: {len(data)}, Expected: {num_pages_hdr * page_size}')

# Try page 1 with btree offset 100
print('\n=== Page 1 (offset=100) ===')
r = try_parse_leaf_page(data, 0, page_size, header_offset=100)
if r:
    for row in r:
        print(f'  Row {row[0]}: {[str(v)[:80] for v in row[1]]}')
else:
    print('  Not a valid leaf page with header at 100')

# Try scanning different offsets for the first valid B-tree page
print('\n=== Scanning for valid leaf pages ===')
for start in range(0, len(data), 16):
    if data[start] == 0x0D:
        r = try_parse_leaf_page(data, start, page_size, header_offset=0)
        if r and len(r) > 0:
            print(f'  Found leaf page at offset {start} ({start:#x}), {len(r)} records')
            for row in r[:2]:
                vals = [str(v)[:60] for v in row[1]]
                print(f'    Row {row[0]}: {vals}')
