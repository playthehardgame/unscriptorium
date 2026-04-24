"""
Kindle Scribe NBK vector ink renderer.

Decodes Ion binary stroke data and renders notebook pages as PNG images.

Coordinate encoding (reverse-engineered):
  Stroke value blobs use an instruction stream:
  - Signature b'\x01\x01'
  - Little-endian point count (uint32)
  - Packed nibble instructions (2 per byte)
  - Variable-length payload bytes consumed by instructions
  Values are reconstructed with a 2nd-order delta integrator.

Canvas: 15624 × 20832 units @ 2520 PPI → 1860 × 2480 px (scale = 300/2520)

Page grouping:
  Each notebook page has a unique base_id (24-char random string).
  'c{base_id}*'  fragments  →  canvas/page header
  'l{base_id}*'  fragments  →  ink layer data for that page
"""
import os
import sqlite3
import struct
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import amazon.ion.simpleion as ion
from amazon.ion.symbols import shared_symbol_table, SymbolTableCatalog
from amazon.ion.simple_types import IonPyList

try:
    from PIL import Image, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Ion / YJ_symbols catalog ────────────────────────────────────────────────
IVM = b'\xe0\x01\x00\xea'
_DUMMY_YJ = shared_symbol_table('YJ_symbols', 10, tuple(f'_yk_{i}' for i in range(816)))
_CATALOG = SymbolTableCatalog()
_CATALOG.register(_DUMMY_YJ)

# ── Canvas / render constants ───────────────────────────────────────────────
CANVAS_W   = 15624
CANVAS_H   = 20832
NORM_PPI   = 2520
RENDER_DPI = 300
SCALE      = RENDER_DPI / NORM_PPI   # ≈ 0.11905
IMG_W      = round(CANVAS_W  * SCALE)   # 1860
IMG_H      = round(CANVAS_H  * SCALE)   # 2480

# Legacy fallback: old prototype assumed 7-byte fixed header + direct nibbles.
_COORD_HEADER = 7

# ── NBK byte fix ────────────────────────────────────────────────────────────
def fix_nbk_bytes(raw: bytes) -> bytes:
    """Strip the 1024-byte Kindle prefix → valid SQLite bytes."""
    page_size     = struct.unpack('>H', raw[16:18])[0]
    content_start = struct.unpack('>H', raw[105:107])[0]
    new_p1 = bytearray(page_size)
    new_p1[0:124] = raw[0:124]
    cco = 1024 + content_start
    new_p1[content_start:page_size] = raw[cco : cco + page_size - content_start]
    return bytes(new_p1) + raw[1024 + page_size:]


# ── Ion decode ──────────────────────────────────────────────────────────────
def _decode_frag(symtable: bytes, blob: bytes) -> list:
    """Decode one fragment blob using the shared symbol-table context."""
    strip    = blob[4:] if blob[:4] == IVM else blob
    combined = symtable + strip
    try:
        return list(ion.loads(combined, catalog=_CATALOG, single_value=False))
    except Exception:
        return []


# ── Coordinate decoder ──────────────────────────────────────────────────────
def _decode_stroke_values(blob: bytes, expected_points: int) -> list[int]:
    """
    Decode Kindle stroke value blobs (position_x/y, pressure, tilt, ...).

    Format:
      [0:2]   signature b'\\x01\\x01'
      [2:6]   num_points (uint32 LE)
      [6:?]   packed nibble instructions + payload bytes
    """
    data = bytes(blob)
    if len(data) < 6 or data[:2] != b'\x01\x01':
        return []

    num_vals = int.from_bytes(data[2:6], 'little')
    if num_vals <= 0:
        return []

    cursor = 6
    instrs: list[int] = []
    while len(instrs) < num_vals and cursor < len(data):
        b = data[cursor]
        cursor += 1
        instrs.append((b >> 4) & 0x0F)
        if len(instrs) < num_vals:
            instrs.append(b & 0x0F)
    if len(instrs) < num_vals:
        return []

    vals: list[int] = []
    value = 0
    change = 0
    for i in range(num_vals):
        instr = instrs[i]
        n = instr & 0x03

        if instr & 0x04:
            increment = n
        else:
            if n == 0:
                increment = 0
            elif n == 1:
                if cursor + 1 > len(data):
                    return vals
                increment = data[cursor]
                cursor += 1
            elif n == 2:
                if cursor + 2 > len(data):
                    return vals
                increment = int.from_bytes(data[cursor:cursor+2], 'little')
                cursor += 2
            else:
                if cursor + 3 > len(data):
                    return vals
                increment = int.from_bytes(data[cursor:cursor+3], 'little')
                cursor += 3

        if instr & 0x08:
            increment = -increment

        if i == 0:
            change = 0
            value = increment
        else:
            change += increment
            value += change
        vals.append(value)

    if expected_points > 0 and expected_points != len(vals):
        return vals[:min(expected_points, len(vals))]
    return vals


def _legacy_nibble_decode(blob: bytes, vmin: float, vmax: float, n: int) -> list[float]:
    """Fallback decoder kept for older experiments/corrupt edge blobs."""
    if n == 0:
        return []
    data = bytes(blob)[_COORD_HEADER:]
    if vmax == vmin:
        return [vmin] * n
    rng = vmax - vmin
    out, i = [], 0
    while len(out) < n and i < len(data):
        b = data[i]
        out.append(vmin + ((b >> 4) & 0xF) / 15.0 * rng)
        if len(out) < n:
            out.append(vmin + (b & 0xF) / 15.0 * rng)
        i += 1
    return out[:n]


# ── Fragment loader ─────────────────────────────────────────────────────────
def _sqlite_fragments(fixed: bytes) -> tuple[bytes, dict[str, bytes]]:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp.write(fixed)
        tmp_path = tmp.name
    rows: dict[str, bytes] = {}
    try:
        conn = sqlite3.connect(tmp_path)
        cur  = conn.cursor()
        for tbl in ('fragments', 'local_delta_fragments'):
            try:
                cur.execute(f'SELECT id, payload_value FROM "{tbl}"')
                for fid, blob in cur.fetchall():
                    if blob:
                        rows.setdefault(fid, blob)
            except sqlite3.OperationalError:
                pass
        conn.close()
    finally:
        os.unlink(tmp_path)
    st = rows.pop('$ion_symbol_table', b'')
    return st, rows


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    for i in range(9):
        if pos + i >= len(data):
            return 0, pos
        b = data[pos + i]
        if i < 8:
            result = (result << 7) | (b & 0x7F)
            if not (b & 0x80):
                return result, pos + i + 1
        else:
            result = (result << 8) | b
            return result, pos + i + 1
    return result, pos + 9


def _leaf_scan_fragments(raw: bytes) -> tuple[bytes, dict[str, bytes]]:
    """Fallback: walk raw bytes finding SQLite leaf pages (for large/corrupt NBK)."""
    fixed     = fix_nbk_bytes(raw)
    page_size = struct.unpack('>H', fixed[16:18])[0]
    frags: dict[str, bytes] = {}
    for pg in range(len(fixed) // page_size):
        off = pg * page_size
        hdr = off + (100 if pg == 0 else 0)
        if hdr >= len(fixed) or fixed[hdr] != 0x0D:
            continue
        try:
            n_cells = struct.unpack('>H', fixed[hdr+3:hdr+5])[0]
            if n_cells == 0 or n_cells > 500:
                continue
            for ci in range(n_cells):
                ptr = struct.unpack('>H', fixed[hdr+8+ci*2:hdr+8+ci*2+2])[0]
                if not ptr:
                    continue
                p = off + ptr
                pl, p = _read_varint(fixed, p)
                if pl == 0 or pl > 300_000:
                    continue
                _, p = _read_varint(fixed, p)
                hs = p
                hsz, p = _read_varint(fixed, p)
                if hsz == 0 or hsz > 2000:
                    continue
                he = hs + hsz
                stypes = []
                while p < he:
                    st, p = _read_varint(fixed, p)
                    stypes.append(st)
                vals = []
                for st in stypes:
                    if st == 0:
                        vals.append(None)
                    elif 1 <= st <= 4:
                        vals.append(fixed[p:p+st])
                        p += st
                    elif st >= 12 and st % 2 == 0:
                        n = (st - 12) // 2
                        vals.append(('blob', fixed[p:p+n]))
                        p += n
                    elif st >= 13 and st % 2 == 1:
                        n = (st - 13) // 2
                        try:
                            vals.append(fixed[p:p+n].decode('utf-8'))
                        except Exception:
                            vals.append(None)
                        p += n
                    else:
                        vals.append(None)
                fid  = vals[0] if vals and isinstance(vals[0], str) else None
                blob = next((v[1] for v in vals if isinstance(v, tuple) and v[0] == 'blob'), None)
                if fid and blob:
                    frags.setdefault(fid, blob)
        except Exception:
            continue
    st = frags.pop('$ion_symbol_table', b'')
    return st, frags


def load_fragments(nbk_path: Path) -> tuple[bytes, dict[str, bytes]]:
    """
    Load all Ion fragments from an NBK file.
    Returns (symtable_blob, {fragment_id: payload_blob}).
    Falls back to leaf-page scan if SQLite refuses the file.
    """
    with open(nbk_path, 'rb') as fh:
        raw = fh.read()
    fixed = fix_nbk_bytes(raw)
    try:
        st, frags = _sqlite_fragments(fixed)
        if st and frags:
            return st, frags
    except Exception:
        pass
    return _leaf_scan_fragments(raw)


# ── Page grouping ───────────────────────────────────────────────────────────
_SYSTEM_FIDS = frozenset({
    '$ion_symbol_table', 'book_metadata', 'book_navigation',
    'document_data', 'metadata', 'content_features',
})
_MIN_BASE_LEN = 18   # minimum common-prefix length to assign l→c page


def group_pages(frags: dict[str, bytes]) -> dict[str, list[str]]:
    """
    Group layer fragment IDs by page.

    Strategy:
      - Canvas ('c*') fragments mark page boundaries.
      - Each 'l*' fragment belongs to the page whose canvas ID shares the
        longest common prefix (at least _MIN_BASE_LEN chars after the type prefix).
      - 'l*' fragments with no matching canvas go into a '_global_' group.

    Returns {canvas_fid: [layer_fid, ...]} sorted by canvas_fid.
    """
    canvas_ids = sorted(
        fid for fid in frags
        if fid.startswith('c') and len(fid) > 10 and fid not in _SYSTEM_FIDS
    )
    layer_ids  = [
        fid for fid in frags
        if fid.startswith('l') and len(fid) > 10 and fid not in _SYSTEM_FIDS
    ]

    page_layers: dict[str, list[str]] = {cfid: [] for cfid in canvas_ids}

    for lfid in layer_ids:
        lbase = lfid[1:]          # strip leading 'l'
        best_cfid, best_len = None, 0
        for cfid in canvas_ids:
            cbase = cfid[1:]      # strip leading 'c'
            common = 0
            for a, b in zip(lbase, cbase):
                if a == b:
                    common += 1
                else:
                    break
            if common > best_len:
                best_len, best_cfid = common, cfid
        if best_cfid and best_len >= _MIN_BASE_LEN:
            page_layers[best_cfid].append(lfid)
        else:
            page_layers.setdefault('_global_', []).append(lfid)

    return page_layers


# ── Stroke extraction ───────────────────────────────────────────────────────
def _strokes_from_item(item) -> list[dict]:
    """Extract stroke dicts from one decoded Ion item (handles outer wrapper)."""
    strokes = []
    if not hasattr(item, 'items'):
        return strokes

    # The outer wrapper is {_yk_NNN: layer_id, _yk_MMM: [stroke, ...]}
    # Find the list value that contains the stroke structs
    candidate: list | None = None
    for _k, v in item.items():
        if isinstance(v, IonPyList) and len(v) > 0:
            candidate = v
            break
    if candidate is None:
        candidate = [item]   # fallback: treat item itself as a single stroke

    for child in candidate:
        if not hasattr(child, 'items'):
            continue
        sd = {str(k): v for k, v in child.items()}
        if 'stroke' not in str(sd.get('nmdl.type', '')).lower():
            continue
        bounds_raw = sd.get('nmdl.stroke_bounds')
        if bounds_raw is None:
            continue
        bounds = [float(x) for x in bounds_raw]
        if len(bounds) != 4:
            continue
        x0, y0, x1, y1 = bounds

        sp_raw = sd.get('nmdl.stroke_points')
        if sp_raw is None or not hasattr(sp_raw, 'items'):
            continue
        sp = {str(k): v for k, v in sp_raw.items()}
        n  = int(sp.get('nmdl.num_points', 0))
        if n == 0:
            continue

        px = sp.get('nmdl.position_x')
        py = sp.get('nmdl.position_y')
        if not isinstance(px, (bytes, bytearray)) or not isinstance(py, (bytes, bytearray)):
            continue

        x_rel = _decode_stroke_values(bytes(px), n)
        y_rel = _decode_stroke_values(bytes(py), n)
        if x_rel and y_rel:
            xs = [x0 + float(v) for v in x_rel]
            ys = [y0 + float(v) for v in y_rel]
        else:
            xs = _legacy_nibble_decode(bytes(px), x0, x1, n)
            ys = _legacy_nibble_decode(bytes(py), y0, y1, n)
        if not xs or not ys:
            continue

        point_count = min(len(xs), len(ys))
        xs = xs[:point_count]
        ys = ys[:point_count]

        pp = sp.get('nmdl.pressure')
        if isinstance(pp, (bytes, bytearray)):
            p_vals = _decode_stroke_values(bytes(pp), point_count)
            if p_vals:
                lo = min(p_vals)
                hi = max(p_vals)
                if hi > lo:
                    pressure = [(v - lo) / (hi - lo) for v in p_vals[:point_count]]
                else:
                    pressure = [0.5] * point_count
            else:
                pressure = [0.5] * point_count
        else:
            pressure = [0.5] * point_count

        strokes.append({
            'x':         xs,
            'y':         ys,
            'pressure':  pressure,
            'thickness': float(sd.get('nmdl.thickness') or 1.0),
            'color':     int(sd.get('nmdl.color') or 0),
        })
    return strokes


def _collect_layer_strokes(symtable: bytes, frags: dict[str, bytes],
                            layer_fids: list[str]) -> list[dict]:
    """Decode all strokes from a list of layer fragment IDs."""
    result = []
    for fid in layer_fids:
        blob  = frags.get(fid)
        if not blob:
            continue
        items = _decode_frag(symtable, blob)
        for item in items:
            result.extend(_strokes_from_item(item))
    return result


# ── Rendering ───────────────────────────────────────────────────────────────
def render_strokes(
    strokes: list[dict],
    width: int = IMG_W,
    height: int = IMG_H,
    scale: float = SCALE,
    bg: tuple = (255, 255, 255),
) -> 'Image.Image':
    """Render a list of stroke dicts into a white Pillow Image."""
    if not PIL_OK:
        raise RuntimeError('Pillow required: pip install Pillow')
    img  = Image.new('RGB', (width, height), color=bg)
    draw = ImageDraw.Draw(img)
    for s in strokes:
        pen_w = max(1, int(s['thickness'] * scale * 0.5))
        ink   = (0, 0, 0) if (s.get('color') or 0) == 0 else (60, 60, 60)
        pts   = [(x * scale, y * scale) for x, y in zip(s['x'], s['y'])]
        if len(pts) == 1:
            r = max(1, pen_w // 2)
            cx, cy = int(pts[0][0]), int(pts[0][1])
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=ink)
        else:
            for i in range(len(pts) - 1):
                draw.line([pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]],
                          fill=ink, width=pen_w)
    return img


# ── Public API ──────────────────────────────────────────────────────────────
def render_nbk_pages(nbk_path: Path, verbose: bool = False) -> list['Image.Image']:
    """
    Render ALL pages of an NBK notebook as Pillow Images.

    Returns a list of Images, one per page, in notebook order.
    Returns [blank_image] if no ink data is found.
    """
    if not PIL_OK:
        raise RuntimeError('Pillow required: pip install Pillow')
    symtable, frags = load_fragments(nbk_path)
    if not symtable:
        if verbose:
            print(f'[ink] No symbol table in {nbk_path.name}', file=sys.stderr)
        return [Image.new('RGB', (IMG_W, IMG_H), (255, 255, 255))]

    pages = group_pages(frags)
    if not pages:
        if verbose:
            print(f'[ink] No canvas fragments found in {nbk_path.name}', file=sys.stderr)
        # Fall back: render all layer fragments as one page
        all_l = [fid for fid in frags if fid.startswith('l') and len(fid) > 10]
        strokes = _collect_layer_strokes(symtable, frags, sorted(all_l))
        return [render_strokes(strokes)]

    images = []
    for page_num, (cfid, layer_fids) in enumerate(sorted(pages.items()), 1):
        if cfid == '_global_':
            continue
        strokes = _collect_layer_strokes(symtable, frags, sorted(layer_fids))
        if verbose:
            print(f'[ink] Page {page_num} ({cfid[:12]}…): '
                  f'{len(layer_fids)} layers, {len(strokes)} strokes')
        images.append(render_strokes(strokes))

    # If nothing was rendered, return a blank page
    return images if images else [Image.new('RGB', (IMG_W, IMG_H), (255, 255, 255))]


def render_nbk(nbk_path: Path, out_path: Path | None = None,
               verbose: bool = True) -> 'Image.Image':
    """
    Render the FIRST page of an NBK notebook (convenience wrapper).
    """
    imgs = render_nbk_pages(nbk_path, verbose=verbose)
    img  = imgs[0]
    if out_path:
        img.save(str(out_path))
        if verbose:
            print(f'[ink] Saved -> {out_path}')
    return img


def render_nbk_all_pages(nbk_path: Path, out_dir: Path,
                          verbose: bool = False) -> list[Path]:
    """
    Render ALL pages and save them as PNGs in out_dir.

    Returns list of saved paths (e.g. [page001.png, page002.png, ...]).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stem   = nbk_path.parent.name   # UUID directory name
    imgs   = render_nbk_pages(nbk_path, verbose=verbose)
    saved  = []
    for i, img in enumerate(imgs, 1):
        p = out_dir / f'{stem}_p{i:03d}.png'
        img.save(str(p))
        saved.append(p)
    if verbose:
        print(f'[ink] {len(saved)} page(s) saved -> {out_dir}')
    return saved


# ── Quick inspection helper ─────────────────────────────────────────────────
def inspect(nbk_path: Path):
    """Print a quick summary: pages, layers, stroke counts."""
    symtable, frags = load_fragments(nbk_path)
    pages = group_pages(frags)
    total_strokes = 0
    for pi, (cfid, lfids) in enumerate(sorted(pages.items()), 1):
        if cfid == '_global_':
            continue
        s = _collect_layer_strokes(symtable, frags, lfids)
        total_strokes += len(s)
        print(f'Page {pi}: {len(lfids)} layers | {len(s)} strokes [{cfid[:16]}...]')
    print(f'Total: {total_strokes} strokes across {len(pages)} pages')


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Render Kindle Scribe NBK pages to PNG')
    ap.add_argument('nbk_path', help='Path to an .nbk file')
    ap.add_argument('--out', '-o', default=None, help='Output PNG (first page only)')
    ap.add_argument('--all',  action='store_true', help='Render all pages')
    ap.add_argument('--outdir', default=None, help='Output dir for --all')
    ap.add_argument('--inspect', action='store_true', help='Print summary only')
    args = ap.parse_args()

    nbk = Path(args.nbk_path)
    if args.inspect:
        inspect(nbk)
    elif args.all:
        od = Path(args.outdir) if args.outdir else nbk.parent / 'pages'
        render_nbk_all_pages(nbk, od, verbose=True)
    else:
        out = Path(args.out) if args.out else nbk.with_suffix('.png')
        render_nbk(nbk, out_path=out, verbose=True)
