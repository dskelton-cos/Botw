"""Map icons taken from your own BotW files: the game's map UI icons and Hyrule Compendium pictures, written
as PNGs to assets/gameicons/ (plus meta.json listing them). Icons the game has no picture for keep this
project's own SVG (web/icons/).

Sources:
- Pack/Bootup.pack -> Layout/Common.sblarc -> timg/__Combined.bntx: map UI icons. `^t` textures are colour
  icons; `^s` ones are one-channel masks that the game colours in its layouts, so they are coloured here.
- UI/PictureBook/<actor>.jpg: compendium pictures.
"""
import io
import json
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import gamefiles
import maptiles
from paths import ASSETS

VERSION = 1  # bump when the icon set or its drawing changes: the app then rebuilds it
SIZE = 96  # output px; markers are drawn at 20-24 css px, so this stays sharp on high-dpi screens

# name: (kind, source, colour)
#   ui    - colour icon from the combined UI textures
#   mask  - mask from the combined UI textures (`^s`: one channel; `^t`: two channels, the shape in the
#           second), filled with colour
#   photo - UI/PictureBook/<source>.jpg, cut to a circle
RECIPES = {
    'korok': ('mask', 'Nt_StampIconLeaf_00^s', (236, 196, 72)),
    'shrine': ('mask', 'Nt_MapDungeonNew_00^t', (245, 170, 60)),
    'tower': ('mask', 'Nt_MapTowerNew_00^t', (120, 215, 255)),
    'hinox': ('photo', 'Enemy_Giant_Junior', None),
    'talus': ('photo', 'Enemy_Golem_Junior', None),
    'molduga': ('photo', 'Enemy_Sandworm', None),
    'lynel': ('photo', 'Enemy_Lynel_Junior', None),
    'treasure_chest': ('mask', 'Nt_StampIconTBox_00^s', (240, 190, 90)),
    'player': ('mask', 'Nt_MapPlayerIconNew_00^s', (255, 214, 64)),
}


def _image(data, offset):
    w, h, bgra, kind = maptiles.decode_texture(data, offset)
    img = Image.frombytes('RGBA', (w, h), bgra, 'raw', 'BGRA')
    if kind == 0x1D:  # BC4: one channel (red) = coverage
        img = Image.merge('RGBA', (*[Image.new('L', img.size, 255)] * 3, img.getchannel('R')))
    return img


def _fit(img, box):
    # crop to what's visible; masks have faint noise around the glyph, so ignore near-transparent pixels
    visible = img.getchannel('A').point(lambda v: 255 if v > 100 else 0).getbbox()
    if visible:  # keep a little of the soft edge
        l, t, r, b = visible
        visible = (max(l - 2, 0), max(t - 2, 0), min(r + 2, img.width), min(b + 2, img.height))
    img = img.crop(visible or (0, 0, *img.size))
    scale = box / max(img.size)   # up or down: some glyphs are only ~25 px in their texture
    img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    out = Image.new('RGBA', (SIZE, SIZE))
    out.alpha_composite(img, ((SIZE - img.width) // 2, (SIZE - img.height) // 2))
    return out


def _with_outline(img, width=5, opacity=0.85):
    """Dark outline + soft shadow so light icons stay readable on the bright map."""
    alpha = img.getchannel('A')
    edge = alpha.filter(ImageFilter.MaxFilter(width)).filter(ImageFilter.GaussianBlur(1.5))
    edge = edge.point(lambda v: int(v * opacity))
    out = Image.new('RGBA', img.size, (20, 16, 10, 0))
    out.putalpha(edge)
    out.alpha_composite(img)
    return out


def _tint(mask, colour):
    out = Image.new('RGBA', mask.size, (*colour, 0))
    out.putalpha(mask.getchannel('A'))
    return out


def _photo(img):
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((SIZE - 8, SIZE - 8), Image.LANCZOS)
    mask = Image.new('L', img.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, img.width - 1, img.height - 1), fill=255)
    out = Image.new('RGBA', (SIZE, SIZE))
    ImageDraw.Draw(out).ellipse((0, 0, SIZE - 1, SIZE - 1), fill=(20, 16, 10, 255))
    ImageDraw.Draw(out).ellipse((2, 2, SIZE - 3, SIZE - 3), fill=(232, 214, 160, 255))
    img.putalpha(ImageChops.multiply(img.getchannel('A'), mask))
    out.alpha_composite(img, (4, 4))
    return out


def build(romfs, out=ASSETS / 'gameicons', log=print):
    """Write <name>.png for every icon found; returns the list of names written."""
    rf = romfs if isinstance(romfs, gamefiles.Romfs) else gamefiles.Romfs(romfs)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ui = None
    written = []
    for name, (kind, src, colour) in RECIPES.items():
        try:
            if kind in ('ui', 'mask'):
                if ui is None:
                    boot = rf.pack('Pack/Bootup.pack', dlc=False)
                    ui = gamefiles.sarc(boot['Layout/Common.sblarc'])['timg/__Combined.bntx']
                    ui_index = dict(maptiles.textures(ui))
                img = _image(ui, ui_index[src])
                if src.endswith('^t'):   # two channels (BC5): the shape is in green
                    img = Image.merge('RGBA', (*[Image.new('L', img.size, 255)] * 3, img.getchannel('G')))
                if kind == 'mask':
                    img = _tint(img, colour)
                img = _with_outline(_fit(img, SIZE - 12))
            else:
                img = _photo(Image.open(io.BytesIO(rf.read(f'UI/PictureBook/{src}.jpg', dlc=False))).convert('RGBA'))
        except Exception as e:  # keep the app's own icon for this one
            log(f'icon {name}: {type(e).__name__}: {e}')
            continue
        img.save(out / f'{name}.png', optimize=True)
        written.append(name)
    (out / 'meta.json').write_text(json.dumps({'version': VERSION, 'icons': written, 'built': int(time.time())}), encoding='utf-8')
    log(f'{len(written)} game icons -> {out}')
    return written


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--extracted', required=True, help="Savage Wind's extracted folder")
    ap.add_argument('--out', default=str(ASSETS / 'gameicons'))
    a = ap.parse_args()
    build(a.extracted, a.out)
