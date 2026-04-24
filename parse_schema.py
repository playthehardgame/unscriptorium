import struct

def read_varint(data, pos):
    result = 0
    for i in range(9):
        byte = data[pos + i]
        if i < 8:
            result = (result << 7) | (byte & 0x7f)
            if not (byte & 0x80):
                return result, pos + i + 1
        else:
            result = (result << 8) | byte
            return result, pos + i + 1
    return result, pos + 9

path = 'M:/TEMP/notebooks/B07RZYBHB8!!EBOK!!notebook/nbk'
with open(path, 'rb') as f:
    data = f.read()

page_size = struct.unpack('>H', data[16:18])[0]
print(f'Page size: {page_size}')

# Page 1 = first page (sqlite_master/schema table)
# Note: page 1 has a 100-byte SQLite file header before the B-tree page header
page1 = data[0:page_size]
btree_start = 100  # page 1 only has 100-byte file header

# Parse leaf table b-tree page
page_type = page1[btree_start]
print(f'Page type: {page_type:#04x} (0x0d=leaf table)')
b = btree_start
first_freeblock = struct.unpack('>H', page1[b+1:b+3])[0]
num_cells = struct.unpack('>H', page1[b+3:b+5])[0]
content_start = struct.unpack('>H', page1[b+5:b+7])[0]
print(f'Num cells: {num_cells}')
print(f'Content start: {content_start}')

# Cell pointer array starts at byte 8 after btree header
cell_offsets = []
for i in range(num_cells):
    off = struct.unpack('>H', page1[b+8 + i*2 : b+10 + i*2])[0]
    cell_offsets.append(off)
print(f'Cell offsets: {cell_offsets}')

# Parse each cell (record format for sqlite_master)
# sqlite_master columns: type, name, tbl_name, rootpage, sql
for cell_off in cell_offsets:
    pos = cell_off
    payload_size, pos = read_varint(page1, pos)
    row_id, pos = read_varint(page1, pos)

    # Read header
    header_start = pos
    header_size, pos = read_varint(page1, pos)
    header_end = header_start + header_size

    serial_types = []
    p = pos
    while p < header_end:
        st, p = read_varint(page1, p)
        serial_types.append(st)

    # Read values
    pos = header_end
    values = []
    for st in serial_types:
        if st == 0:  # NULL
            values.append(None)
        elif st == 1:
            values.append(struct.unpack('>b', page1[pos:pos+1])[0]); pos += 1
        elif st == 2:
            values.append(struct.unpack('>h', page1[pos:pos+2])[0]); pos += 2
        elif st == 3:
            val = struct.unpack('>i', b'\x00' + page1[pos:pos+3])[0]; pos += 3; values.append(val)
        elif st == 4:
            values.append(struct.unpack('>i', page1[pos:pos+4])[0]); pos += 4
        elif st == 5:
            val = struct.unpack('>q', b'\x00\x00' + page1[pos:pos+6])[0]; pos += 6; values.append(val)
        elif st == 6:
            values.append(struct.unpack('>q', page1[pos:pos+8])[0]); pos += 8
        elif st == 7:
            values.append(struct.unpack('>d', page1[pos:pos+8])[0]); pos += 8
        elif st == 8: values.append(0)
        elif st == 9: values.append(1)
        elif st >= 12 and st % 2 == 0:  # blob
            n = (st - 12) // 2
            values.append(('blob', page1[pos:pos+n])); pos += n
        elif st >= 13 and st % 2 == 1:  # text
            n = (st - 13) // 2
            values.append(page1[pos:pos+n].decode('utf-8', errors='replace')); pos += n
        else:
            values.append(f'<unknown st={st}>')

    print(f'\nRowID {row_id}: {values[:4]}')
    if len(values) > 4:
        print(f'  SQL: {values[4][:200] if isinstance(values[4], str) else values[4]}')
