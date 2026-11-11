"""Generate the app's own map icons (web/icons/*.svg). Drawn for this project; no game art.

    python tools/make_icons.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'web' / 'icons'

# name: (badge color, glyph SVG in a 32x32 box, glyph color)
W = '#fff8e6'
ICONS = {
    'korok': ('#c98a2b', '<path d="M16 6c6 4 8 10 3 18-1 1-2 2-3 2s-2-1-3-2C8 16 10 10 16 6z"/><path d="M16 9v15" stroke="#7a4f12" stroke-width="1.6" fill="none"/>', W),
    'shrine': ('#d9822b', '<path d="M8 24V14a8 8 0 0 1 16 0v10z"/><rect x="6.5" y="23.5" width="19" height="3" rx="1"/><path d="M12.5 23.5v-9a3.5 3.5 0 0 1 7 0v9z" fill="#6b3a0c"/><circle cx="16" cy="17.5" r="2" fill="#ffd28a"/>', W),
    'tower': ('#2f7fb0', '<path d="M13 27l1.5-15h3L19 27z"/><path d="M9 12h14l-3-5h-8z"/><circle cx="16" cy="9" r="1.6" fill="#2f7fb0"/>', W),
    'divine_beast': ('#3b8f9a', '<circle cx="16" cy="16" r="9" fill="none" stroke-width="2.4"/><circle cx="16" cy="16" r="3.5"/><path d="M16 4v5M16 23v5M4 16h5M23 16h5" stroke-width="2.2" stroke-linecap="round" fill="none"/>', '#e6fbff'),
    'location': ('#8a7d64', '<path d="M16 5a7 7 0 0 1 7 7c0 6-7 14-7 14S9 18 9 12a7 7 0 0 1 7-7z"/><circle cx="16" cy="12" r="2.6" fill="#8a7d64"/>', W),
    'great_fairy': ('#c2549a', '<path d="M16 9c-6-6-12-1-8 5 2 3 6 3 8 1 2 2 6 2 8-1 4-6-2-11-8-5z"/><path d="M16 15v11" stroke-width="2.2" stroke-linecap="round" fill="none"/><circle cx="16" cy="12" r="2"/>', W),
    'hinox': ('#9a3b2e', '<ellipse cx="16" cy="16" rx="10" ry="7"/><circle cx="16" cy="16" r="4" fill="#9a3b2e"/><circle cx="16" cy="16" r="1.8"/>', W),
    'talus': ('#7d7466', '<path d="M8 24l2-9 6-6 6 4 3 11z"/><path d="M13 16l3-2 3 3" stroke="#7d7466" stroke-width="1.6" fill="none"/>', W),
    'molduga': ('#b8863b', '<path d="M4 20c4-6 8-6 12 0s8 6 12 0" fill="none" stroke-width="3" stroke-linecap="round"/><path d="M10 13l3-5 3 5" />', W),
    'lynel': ('#a3442a', '<path d="M7 25l3-9 6-7 6 7 3 9z"/><path d="M10 10l2-5 2 4M22 10l-2-5-2 4" stroke-width="1.8" fill="none"/><circle cx="13.5" cy="16" r="1.4" fill="#a3442a"/><circle cx="18.5" cy="16" r="1.4" fill="#a3442a"/>', W),
    'armor_chest': ('#5a6fa8', '<rect x="6" y="12" width="20" height="13" rx="2"/><path d="M6 15a10 6 0 0 1 20 0z"/><path d="M12 16h8v5l-4 2-4-2z" fill="#5a6fa8"/>', W),
    'treasure_chest': ('#9b6a2c', '<rect x="6" y="12" width="20" height="13" rx="2"/><path d="M6 15a10 6 0 0 1 20 0z"/><rect x="14" y="15" width="4" height="5" rx="1" fill="#9b6a2c"/>', W),
    # Link's last saved position
    'player': ('#e0a400', '<path d="M16 5l8 20-8-5-8 5z"/>', W),
}


def svg(color, glyph, glyph_color):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
            f'<circle cx="16" cy="16" r="15" fill="{color}" stroke="#141414" stroke-width="1.5"/>'
            f'<g fill="{glyph_color}" stroke="{glyph_color}" stroke-width="0">{glyph}</g></svg>\n')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (color, glyph, gcolor) in ICONS.items():
        (OUT / f'{name}.svg').write_text(svg(color, glyph, gcolor), encoding='utf-8')
    print(f'{len(ICONS)} icons -> {OUT}')


if __name__ == '__main__':
    main()
