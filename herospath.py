"""Read the Hero's Path: where Link has been, as the game records it for the map's Hero's Path mode.

The game keeps it in `tracker/trackblockNN.sav`, next to the save slots (`<save>/tracker/` beside `<save>/0/`,
`<save>/1/`, ...). The path is shared by all slots: it's one recording of the play time, and loading an older
save shows it up to that save's play time.

trackblockNN.sav (64 KiB, little endian), worked out from a save and checked against its six slots: every saved position
(`PlayerSavePos`) is on the path within 2 units, and the times line up with `PlayReport_PlayTime`:

    0x00  u16 0, u16 current block (the one being written), u32 points in it, u32 1, then zeros to 0x40
    0x40  blocks of 0x4C0 bytes (53 fit in a file):
            u32 play time of the first point (seconds), u32 a second time (equal or a little later), u32 0, u32 0
            300 points, u32 each, one every 2 seconds of play

    point bits  0-11  |z|          bit 12  z < 0
                13-25  |x|          bit 26  x < 0
                27-29  markers the game sets around warps and loads (not needed to draw the path)
                31     on the map of Hyrule (MainField); clear inside shrines, Divine Beasts and other maps,
                       where the coordinates are that map's own

Heights aren't recorded. Positions are whole world units, the same x / z as everything else on the map.
"""
import base64
import re
import struct
from pathlib import Path

HEADER = 0x40
BLOCK = 0x4C0
BLOCK_POINTS = 300
STEP = 2                 # seconds of play between two points
MAX_BLOCKS = (0x10000 - HEADER) // BLOCK
BREAK = -0x8000          # in the packed output: no point here (a warp, a shrine, ...): the line stops
# Farther than this between two points 2 s apart is a warp (fast travel, a load, Travel Medallion), not a walk:
# a horse at full gallop or a long shield-surf covers well under half of it.
JUMP = 150

_NAME = re.compile(r'trackblock(\d+)\.sav$', re.IGNORECASE)


class PathError(Exception):
    pass


def tracker_dir(save_dir):
    """The tracker folder for a save folder (the one with the numbered slots), or None."""
    if not save_dir:
        return None
    save_dir = Path(save_dir)
    for cand in (save_dir / 'tracker', save_dir.parent / 'tracker'):
        if cand.is_dir():
            return cand
    return None


def block_files(folder):
    """trackblockNN.sav files in order."""
    try:
        files = [(int(m.group(1)), f) for f in Path(folder).iterdir() if (m := _NAME.search(f.name)) and f.is_file()]
    except OSError:
        return []
    return [f for _, f in sorted(files)]


def decode(word):
    """(x, z, on the map of Hyrule) of one point."""
    z = word & 0xFFF
    if word >> 12 & 1:
        z = -z
    x = word >> 13 & 0x1FFF
    if word >> 26 & 1:
        x = -x
    return x, z, bool(word >> 31)


def read_blocks(buf):
    """[(play time of the first point, [point words])] of one trackblock file, oldest first."""
    if len(buf) < HEADER + BLOCK:
        raise PathError('not a trackblock file (too short)')
    current, count = struct.unpack_from('<HI', buf, 2)
    if current >= MAX_BLOCKS or count > BLOCK_POINTS:
        raise PathError('not a trackblock file (bad header)')
    blocks = []
    for k in range(current + 1):
        off = HEADER + k * BLOCK
        if off + BLOCK > len(buf):
            break
        t0 = struct.unpack_from('<I', buf, off)[0]
        n = BLOCK_POINTS if k < current else count
        words = struct.unpack_from(f'<{n}I', buf, off + 16)
        if t0 == 0 and not any(words):
            continue
        blocks.append((t0, list(words)))
    return blocks


def read(folder):
    """Every recorded point, oldest first: (play time, x, z, on the map of Hyrule)."""
    blocks = []
    for f in block_files(folder):
        try:
            blocks += read_blocks(f.read_bytes())
        except (OSError, struct.error, PathError):
            continue   # the game may be writing it; the next read picks it up
    blocks.sort(key=lambda b: b[0])
    points = []
    for t0, words in blocks:
        for i, w in enumerate(words):
            x, z, field = decode(w)
            points.append((t0 + STEP * i, x, z, field))
    return points


def pack(points):
    """For the page: the points on the map of Hyrule as Int16 (x, z) pairs, base64, with a (BREAK, BREAK) pair
    wherever the line stops (left the map or warped), and the play time of each pair (Uint32, base64).
    Times go up in steps of 2 s, so the page can cut the path at any play time."""
    xz, ts = [], []
    prev = None
    for t, x, z, field in points:
        if not field:
            prev = None
            continue
        if prev and (abs(x - prev[0]) > JUMP or abs(z - prev[1]) > JUMP):
            prev = None
        if prev is None and xz:
            if xz[-2:] != [BREAK, BREAK]:
                xz += [BREAK, BREAK]
                ts.append(t)
        xz += [x, z]
        ts.append(t)
        prev = (x, z)
    return {
        'n': len(ts),
        'xz': base64.b64encode(struct.pack(f'<{len(xz)}h', *xz)).decode('ascii'),
        't': base64.b64encode(struct.pack(f'<{len(ts)}I', *ts)).decode('ascii'),
        'start': points[0][0] if points else 0,
        'end': points[-1][0] if points else 0,
        'step': STEP,
    }


def stamp(folder):
    """Changes whenever a trackblock file does (for caching)."""
    out = []
    for f in block_files(folder):
        try:
            st = f.stat()
            out.append((f.name, st.st_mtime_ns, st.st_size))
        except OSError:
            pass
    return tuple(out)
