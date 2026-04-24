import struct, re

def read_varint(data, pos):
    result = 0
    for i in range(9):
        if pos + i >= len(data): return 0, pos
        byte = data[pos + i]
        if i < 8:
            result = (result << 7) | (byte & 0x7f)
            if not (byte & 0x80): return result, pos + i + 1
        else:
            result = (result << 8) | byte
            return result, pos + i + 1
    return result, pos + 9

def try_parse_leaf(data, abs_start):
    """Try to parse a leaf page at absolute offset abs_start."""
    if abs_start >= len(data) or data[abs_start] != 0x0D:
        return None
    try:
        num_cells = struct.unpack('>H', data[abs_start+3:abs_start+5])[0]
        if num_cells == 0 or num_cells > 200: return None
        records = []
        for i in range(num_cells):
            ptr = struct.unpack('>H', data[abs_start+8+i*2:abs_start+8+i*2+2])[0]
            if ptr == 0: continue
            cell_pos = abs_start + ptr
            payload_size, p = read_varint(data, cell_pos)
            if payload_size == 0 or payload_size > 100000: continue
            row_id, p = read_varint(data, p)
            hdr_start = p
            hdr_size, p = read_varint(data, p)
            if hdr_size == 0 or hdr_size > 1000: continue
            hdr_end = hdr_start + hdr_size
            serial_types = []
            while p < hdr_end:
                st, p = read_varint(data, p)
                serial_types.append(st)
            values = []
            p = hdr_end
            for st in serial_types:
                if st == 0: values.append(None)
                elif 1 <= st <= 4:
                    n = st
                    values.append(int.from_bytes(data[p:p+n], 'big', signed=True)); p += n
                elif st == 8: values.append(0)
                elif st == 9: values.append(1)
                elif st >= 12 and st % 2 == 0:
                    n = (st - 12) // 2
                    values.append(('blob', data[p:p+n])); p += n
                elif st >= 13 and st % 2 == 1:
                    n = (st - 13) // 2
                    try: values.append(data[p:p+n].decode('utf-8'))
                    except: values.append(('raw', data[p:p+n]))
                    p += n
                else: values.append(f'<st={st}>')
            if values: records.append((row_id, values))
        return records if records else None
    except: return None

path = 'M:/TEMP/notebooks/B07RZYBHB8!!EBOK!!notebook/nbk'
with open(path, 'rb') as f:
    data = f.read()

# Scan every byte for 0x0D (leaf page marker)
print('Scanning for valid leaf pages...')
found = []
for offset in range(0, len(data) - 100, 1):
    if data[offset] == 0x0D:
        r = try_parse_leaf(data, offset)
        if r and len(r) >= 1:
            # Check if records look valid (strings contain printable text)
            valid = False
            for row in r:
                for v in row[1]:
                    if isinstance(v, str) and len(v) > 3:
                        valid = True
                    elif isinstance(v, tuple) and v[0] == 'blob' and len(v[1]) > 10:
                        valid = True
            if valid:
                found.append((offset, r))

print(f'Found {len(found)} valid leaf pages')
for offset, records in found[:20]:
    print(f'\n=== Leaf page at offset {offset} ({offset:#x}) ===')
    for row_id, vals in records[:3]:
        print(f'  Row {row_id}:')
        for v in vals:
            if isinstance(v, str): print(f'    TEXT: {repr(v[:100])}')
            elif isinstance(v, tuple) and v[0] == 'blob': print(f'    BLOB ({len(v[1])} bytes): {v[1][:30].hex()}')
            elif isinstance(v, int): print(f'    INT: {v}')
            else: print(f'    OTHER: {v}')
