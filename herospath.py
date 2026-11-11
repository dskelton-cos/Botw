"""Read the Hero's Path: where Link has been, as the game records it for the map's Hero's Path mode.

The game keeps it in a `tracker` folder next to the save slots (`<save>/tracker/` beside `<save>/0/`, `<save>/1/`,
...), one recording per difficulty: `trackblockNN.sav` for normal mode and `trackblock_hardNN.sav` for Master
Mode. Each is a ring of up to 32 files: when the last one is full the game starts over at 00, overwriting the
oldest part of the path. A recording is shared by the slots of its mode, and loading an older save shows it up
to that save's play time.

trackblock file (64 KiB, little endian), worked out from two saves (one of 900+ hours with a wrapped ring and a
Master Mode run) and checked against their slots: the point where each slot was saved is on the path:

    0x00  u8 file number, u8 sequence (goes up by one per file written, so it orders the ring after a wrap),
          u16 current block (the one being written), u32 points in it, u32 flags (1 or 17), zeros to 0x40
    0x40  blocks of 0x4C0 bytes (48 are used, 53 would fit):
            u32 play time of the first point (seconds), u32 another clock (not the play time; not used), u32 0,
            u32 0, then 300 points, u32 each, one every 2 seconds of play

    point bits  0-11  |z|          bit 12  z < 0
                13-25  |x|          bit 26  x < 0
                27     Link arrived here without walking: fast travel, or a save was loaded (after dying, or
                       picked from the menu), which also puts the play time back to that save's
                28-29  markers the game sets around warps (not needed to draw the path)
                31     on the map of Hyrule (MainField); clear inside shrines, Divine Beasts and other maps,
                       where the coordinates are that map's own

The game keeps writing after a load, so the file still holds what happened between the save and the load (the
run that ended in a death); `read` drops it, keeping the path that leads to the saves. Which arrivals were loads,
and how far back each went, isn't stored either. A block's 300 points cover about 600 s of play, so when the next
block starts earlier than that, the difference is how far the loads in this block went back in all. It's put on
the arrival that was a load: the one where Link had been that much earlier (a save is made where Link is), else the
last arrival in the block. The last block has nothing after it; there the saves say it (an arrival before the
point where a save was made, when that save's play time is earlier than the point's).

Heights aren't recorded. Positions are whole world units, the same x / z as everything else on the map.
"""
import base64
import bisect
import re
import struct
from pathlib import Path

HEADER = 0x40
BLOCK = 0x4C0
BLOCK_POINTS = 300
STEP = 2                 # seconds of play between two points
MAX_BLOCKS = (0x10000 - HEADER) // BLOCK
LOAD = 1 << 27
BREAK = -0x8000          # in the packed output: no point here (a warp, a shrine, ...): the line stops
# Farther than this between two points 2 s apart is a warp (fast travel, a load, Travel Medallion), not a walk:
# a horse at full gallop or a long shield-surf covers well under half of it.
JUMP = 150
MATCH = 16               # a load puts Link where the save was made, on the path within a step or so
MATCH_POINTS = 4 * 3600 // STEP   # how far back to look for it (4 hours of play)
SLACK = 10               # a block may run a few seconds over 600 s (loading screens): not a load
TOLERANCE = 30           # seconds: how close a load's rewind has to come to the block's

MODES = ('normal', 'master')
_NAME = {'normal': re.compile(r'^trackblock(\d+)\.sav$', re.IGNORECASE),
         'master': re.compile(r'^trackblock_hard(\d+)\.sav$', re.IGNORECASE)}


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


def block_files(folder, mode='normal'):
    """The trackblock files of a mode ('normal' or 'master'), by file number."""
    try:
        files = [(int(m.group(1)), f) for f in Path(folder).iterdir()
                 if (m := _NAME[mode].match(f.name)) and f.is_file()]
    except OSError:
        return []
    return [f for _, f in sorted(files)]


def modes(folder):
    """The modes that have a recording in this tracker folder."""
    return [m for m in MODES if block_files(folder, m)] if folder else []


def decode(word):
    """(x, z, on the map of Hyrule) of one point."""
    z = word & 0xFFF
    if word >> 12 & 1:
        z = -z
    x = word >> 13 & 0x1FFF
    if word >> 26 & 1:
        x = -x
    return x, z, bool(word >> 31)


def read_file(buf):
    """(sequence, [(play time of the first point, [point words])]) of one trackblock file, in the order written."""
    if len(buf) < HEADER + BLOCK:
        raise PathError('not a trackblock file (too short)')
    seq = buf[1]
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
        if not words or (t0 == 0 and not any(words)):
            continue
        blocks.append((t0, list(words)))
    return seq, blocks


def read_blocks(buf):
    """[(play time of the first point, [point words])] of one trackblock file, in the order written."""
    return read_file(buf)[1]


def _in_order(files):
    """The files' blocks in the order written: by sequence, which wraps at 256 (the ring holds 32 files)."""
    if not files:
        return []
    seqs = [s for s, _ in files]
    wrapped = max(seqs) - min(seqs) > 128
    files.sort(key=lambda f: f[0] + 256 if wrapped and f[0] < 128 else f[0])
    return [b for _, blocks in files for b in blocks]


def _rewinds(out, block, x, z, now, upto):
    """How far back (seconds, up to `upto`) a load arriving at (x, z) at play time `now` could have gone: to each
    earlier time Link was there (sorted). Looks at the points of this block before it, then back through `out`
    (twice as far back as `upto` seconds of points, as runs that were reloaded over sit in between)."""
    found = set()
    left = min(MATCH_POINTS, 2 * upto // STEP + BLOCK_POINTS)
    for prior in (block, out):
        for j in range(len(prior) - 1, max(-1, len(prior) - 1 - left), -1):
            t, px, pz = prior[j][:3]
            if now - upto <= t < now and abs(px - x) <= MATCH and abs(pz - z) <= MATCH:
                found.add(now - t)
        left -= len(prior)
        if left <= 0:
            break
    return sorted(found)


def _near(values, target):
    """A value in the sorted list within TOLERANCE of target, or None."""
    i = bisect.bisect_left(values, target - TOLERANCE)
    return values[i] if i < len(values) and values[i] <= target + TOLERANCE else None


def _split(total, arrivals, cands, boundary_load):
    """{arrival index: seconds back} for a block whose loads went back `total` seconds in all."""
    for i in reversed(arrivals):                       # one load
        if _near(cands[i], total) is not None:
            return {i: total}
    for a, i in enumerate(arrivals):                   # two loads
        for j in arrivals[a + 1:]:
            for c in cands[i]:
                if c < total and _near(cands[j], total - c) is not None:
                    return {i: c, j: total - c}
    if boundary_load:                                  # the next block starts with the load
        return {}
    return {arrivals[-1]: total} if arrivals else {}


def timeline(blocks, saves=()):
    """The points of a recording ([(play time of the first point, words)] in the order written) with their play
    times, oldest first, without the stretches a load went back over: [(play time, x, z, on the map of Hyrule)].
    `saves` ([(play time, x, z)] of the slots) place the loads in the last block."""
    out = []
    for k, (t0, words) in enumerate(blocks):
        n = len(words)
        pts = [decode(w) for w in words]
        arrivals = [i for i in range(1, n) if words[i] & LOAD]
        back = {}
        if arrivals and k + 1 < len(blocks):
            total = t0 + STEP * n - blocks[k + 1][0]
            if total > SLACK:
                plain = [(t0 + STEP * i, *pts[i]) for i in range(n)]
                cands = {i: _rewinds(out, plain[:i], *pts[i][:2], t0 + STEP * i, total + TOLERANCE) for i in arrivals}
                back = _split(total, arrivals, cands, bool(blocks[k + 1][1][0] & LOAD))
        elif arrivals and saves:
            # the last block: where a save was made after an arrival, at a play time earlier than the point's
            best = None
            for pt, x, z in saves:
                for i in range(n - 1, arrivals[0] - 1, -1):
                    if abs(pts[i][0] - x) <= 3 and abs(pts[i][1] - z) <= 3:
                        if t0 + STEP * i - pt > SLACK and (best is None or i > best[0]):
                            best = (i, t0 + STEP * i - pt)
                        break
            if best:
                back = {max(a for a in arrivals if a <= best[0]): best[1]}
        t = t0
        for i, (x, z, field) in enumerate(pts):
            if i:
                t += STEP - back.get(i, 0)
            out.append((t, x, z, field))
    # A load goes back to the save's play time: what was recorded before it at that time or later is a run that
    # didn't count (the one that ended in a death). Keep each point only if nothing later is earlier in play time.
    keep, low = [], float('inf')
    for p in reversed(out):
        if p[0] < low:
            keep.append(p)
            low = p[0]
    keep.reverse()
    return keep


def read(folder, mode='normal', saves=()):
    """Every recorded point of a mode, oldest first: (play time, x, z, on the map of Hyrule). `saves`:
    [(play time, x, z)] of the save slots (see timeline)."""
    files = []
    for f in block_files(folder, mode):
        try:
            files.append(read_file(f.read_bytes()))
        except (OSError, struct.error, PathError):
            continue   # the game may be writing it; the next read picks it up
    return timeline(_in_order(files), saves)


def distance_at(points, playtime, x, z, within=30):
    """How far (x, z) is from where the path was around this play time (± within seconds), or None."""
    times = [p[0] for p in points] if not isinstance(points, _Indexed) else points.times
    lo = bisect.bisect_left(times, playtime - within)
    hi = bisect.bisect_right(times, playtime + within)
    if lo >= hi:
        return None
    return min(((p[1] - x) ** 2 + (p[2] - z) ** 2) ** 0.5 for p in points[lo:hi])


class _Indexed(list):
    """A timeline with its play times, for repeated distance_at lookups."""

    def __init__(self, points):
        super().__init__(points)
        self.times = [p[0] for p in points]


def indexed(points):
    return _Indexed(points)


def slot_mode(timelines, playtime, x, z):
    """Which recording ({mode: timeline}) a save made at this play time and position belongs to: the one that was
    closest to it at that time (a save from a run that was reloaded over isn't on the path, but its mode's
    recording still has that play time). None when no recording has that play time (older than the ring holds)."""
    best = None
    for mode, points in timelines.items():
        d = distance_at(points, playtime, x, z)
        if d is not None and (best is None or d < best[0]):
            best = (d, mode)
    return best[1] if best else None


def pack(points):
    """For the page: the points on the map of Hyrule as Int16 (x, z) pairs, base64, with a (BREAK, BREAK) pair
    wherever the line stops (left the map or warped), and the play time of each pair (Uint32, base64).
    Times go up in steps of about 2 s, so the page can cut the path at any play time."""
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


def stamp(folder, mode='normal'):
    """Changes whenever a trackblock file of the mode does (for caching)."""
    out = []
    for f in block_files(folder, mode):
        try:
            st = f.stat()
            out.append((f.name, st.st_mtime_ns, st.st_size))
        except OSError:
            pass
    return tuple(out)
