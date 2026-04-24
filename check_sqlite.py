import struct, sqlite3

path = 'M:/TEMP/notebooks/B07RZYBHB8!!EBOK!!notebook/nbk'

with open(path, 'rb') as f:
    header = f.read(100)

print(f'SQLite version: {sqlite3.sqlite_version}')
print(f'Magic: {header[:16]}')
page_size = struct.unpack('>H', header[16:18])[0]
print(f'Page size: {page_size}')
print(f'File format write: {header[18]}')
print(f'File format read: {header[19]}')
reserved_bytes = header[20]
print(f'Reserved bytes per page: {reserved_bytes}')
print(f'File change counter: {struct.unpack(">I", header[24:28])[0]}')
print(f'DB size in pages: {struct.unpack(">I", header[28:32])[0]}')
print(f'Schema cookie: {struct.unpack(">I", header[40:44])[0]}')
print(f'Schema format: {struct.unpack(">I", header[44:48])[0]}')
print(f'User version: {struct.unpack(">I", header[60:64])[0]}')
print(f'Application ID: {struct.unpack(">I", header[68:72])[0]}')
print(f'SQLite version number: {struct.unpack(">I", header[96:100])[0]}')
print(f'Header bytes 20-23: {header[20:24].hex()}')
print(f'Full header hex: {header.hex()}')

# Try reading with PRAGMA
try:
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA integrity_check')
    print('Integrity check: OK')
except Exception as e:
    print(f'Integrity check error: {e}')

# Try bypassing schema
try:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # Direct page scan
    with open(path, 'rb') as f:
        data = f.read()

    # Look at page 1 schema area (starts at offset 100 after the header)
    page1 = data[:4096]
    print('\nPage 1 bytes 100-200:')
    print(page1[100:200].hex())
except Exception as e:
    print(f'Error: {e}')
