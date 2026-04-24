import struct

path = 'M:/TEMP/notebooks/B07RZYBHB8!!EBOK!!notebook/nbk'
with open(path, 'rb') as f:
    data = f.read()

page_size = 4096
b = 100  # btree header offset in page 1
num_cells = struct.unpack('>H', data[b+3:b+5])[0]
cell_ptrs = [struct.unpack('>H', data[b+8+i*2:b+8+i*2+2])[0] for i in range(num_cells)]

print(f'Cell pointers in page 1: {cell_ptrs}')

for ptr in cell_ptrs:
    abs_pos = ptr  # page 1 starts at file offset 0
    print(f'\nCell at page offset {ptr} (file offset {abs_pos}):')
    print(f'  bytes: {data[abs_pos:abs_pos+20].hex()}')

# What if cell offsets are from END of page?
print('\n=== Testing: cell offsets as positions from content_start ===')
content_start = struct.unpack('>H', data[b+5:b+7])[0]
print(f'Content start: {content_start}')

# What's at the offset if we add the "missing" bytes (file offset 4101 - cell_ptr 3957 = 144)?
offset_delta = 4101 - 3957
print(f'\nDelta between expected and actual: {offset_delta}')
print(f'Testing: cell_file_offset = ptr + {offset_delta}')
for ptr in cell_ptrs[:3]:
    adjusted = ptr + offset_delta
    print(f'  ptr={ptr} -> adjusted={adjusted}: {data[adjusted:adjusted+20].hex()}')

# Try larger range of deltas
print('\n=== Testing various deltas ===')
for delta in [0, 144, 1024, 4096, 4101-3957]:
    hits = 0
    for ptr in cell_ptrs:
        pos = ptr + delta
        if 0 <= pos < len(data) and data[pos] not in (0x00,):
            hits += 1
    print(f'  delta={delta}: {hits}/{len(cell_ptrs)} cells have non-zero start byte')
