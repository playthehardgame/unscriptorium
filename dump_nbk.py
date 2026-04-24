import struct

path = 'M:/TEMP/notebooks/B07RZYBHB8!!EBOK!!notebook/nbk'

with open(path, 'rb') as f:
    data = f.read()

print(f'File size: {len(data)} bytes')
print(f'Header magic: {data[:16]}')

# SQLite header fields
page_size = struct.unpack('>H', data[16:18])[0]
print(f'Page size: {page_size}')
num_pages = struct.unpack('>I', data[28:32])[0]
print(f'Num pages: {num_pages}')

# Try to find readable text in the file
import re
text_chunks = re.findall(b'[\x20-\x7e]{6,}', data)
print(f'\nReadable strings ({len(text_chunks)} found):')
for chunk in text_chunks[:100]:
    print(' ', chunk.decode('utf-8', errors='replace'))
