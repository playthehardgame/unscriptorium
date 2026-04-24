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
page1 = data[0:page_size]
b = 100  # file header offset for page 1

num_cells = struct.unpack('>H', page1[b+3:b+5])[0]
cell_offsets = [struct.unpack('>H', page1[b+8+i*2:b+10+i*2])[0] for i in range(num_cells)]

for cell_off in cell_offsets[:2]:  # debug first 2 cells
    print(f'\n--- Cell at offset {cell_off} ---')
    raw = page1[cell_off:cell_off+50]
    print(f'Raw bytes: {raw.hex()}')

    pos = cell_off
    payload_size, pos2 = read_varint(page1, pos)
    row_id, pos3 = read_varint(page1, pos2)
    print(f'payload_size={payload_size}, rowid={row_id}, header_starts_at={pos3}')

    # Header
    header_start = pos3
    header_size, p = read_varint(page1, pos3)
    print(f'header_size={header_size}')
    header_end = header_start + header_size

    serial_types = []
    while p < header_end:
        st, p = read_varint(page1, p)
        serial_types.append(st)
    print(f'serial_types: {serial_types}')

    # Values
    pos = header_end
    for st in serial_types:
        if st >= 13 and st % 2 == 1:
            n = (st - 13) // 2
            val = page1[pos:pos+n].decode('utf-8', errors='replace')
            print(f'  TEXT({n}): {repr(val[:100])}')
            pos += n
        elif st >= 12 and st % 2 == 0:
            n = (st - 12) // 2
            print(f'  BLOB({n}): {page1[pos:pos+20].hex()}...')
            pos += n
        elif st in (0,):
            print(f'  NULL')
        elif st in (1,2,3,4):
            sizes = {1:1, 2:2, 3:3, 4:4}
            n = sizes[st]
            val = int.from_bytes(page1[pos:pos+n], 'big', signed=True)
            print(f'  INT{n*8}: {val}')
            pos += n
        else:
            print(f'  st={st} (unknown)')
