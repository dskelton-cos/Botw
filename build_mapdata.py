"""Build assets/map_data.json from your own Breath of the Wild game files (Savage Wind's extracted folder).

    python build_mapdata.py --extracted <Savage Wind data folder>\\extracted [--lang USen]

Everything the map shows comes from the game files: the location markers and Korok list of
Map/MainField/Static.smubin, the actors placed in the 80 map sections (Map/MainField/<A-J>-<1-8>_Static and
_Dynamic), the save-data flag list (GameData/gamedata.ssarc) and the names in Pack/Bootup_<lang>.pack.
Each object carries the CRC32 of the save flag that says it's done (`completion_hash`).
"""
import argparse
import json
import re
import sys
import zlib
from pathlib import Path

import gamefiles
from paths import ASSETS

OUT = ASSETS / 'map_data.json'

# Location marker icons that are a place you discover (shops sit inside towns and get no marker here)
PLACE_ICONS = {'Village', 'Hatago', 'CheckPoint', 'Labo', 'Castle', 'StartPoint', None}
# Placed enemies tracked once each (the DLC's monster medals keep a flag per actor: MainField_IsDefeat_<actor>_<id>)
BOSSES = (('Enemy_Giant', 'hinoxes'), ('Enemy_Golem', 'taluses'), ('Enemy_Sandworm', 'moldugas'))


def crc(name):
    return zlib.crc32(name.encode('utf-8'))


def pos(t):
    if isinstance(t, dict):
        x, y, z = t['X'], t['Y'], t['Z']
    else:
        x, y, z = t[0], t[1], t[2]
    return {'x': round(x, 2), 'y': round(y, 2), 'z': round(z, 2)}


def messages(rf, lang):
    """{msbt path without .msbt: {label: text}} of the game text in `lang` (USen when missing)."""
    for code in (lang, 'USen'):
        pack = f'Pack/Bootup_{code}.pack'
        if rf.exists(pack):
            files = rf.pack(pack, dlc=False)
            ssarc = next(n for n in files if n.endswith('.ssarc'))
            return {n[:-5]: d for n, d in gamefiles.sarc(files[ssarc]).items() if n.endswith('.msbt')}, code
    raise FileNotFoundError('no Pack/Bootup_<language>.pack in the game files')


class Text:
    def __init__(self, raw):
        self.raw = raw
        self.cache = {}

    def __call__(self, name):
        if name not in self.cache:
            self.cache[name] = gamefiles.msbt(self.raw[name]) if name in self.raw else {}
        return self.cache[name]

    def actors(self):
        out = {}
        for n in self.raw:
            if n.startswith('ActorType/'):
                out.update(self(n))
        return out


def game_flags(rf):
    """{flag name: data type} of every save flag the game knows (GameData/gamedata.ssarc in Bootup.pack)."""
    boot = rf.pack('Pack/Bootup.pack', dlc=False)
    out = {}
    for fn, data in gamefiles.sarc(boot['GameData/gamedata.ssarc']).items():
        kind = fn.rsplit('/', 1)[-1].rsplit('_', 1)[0]
        doc = gamefiles.byml(data)
        for lst in doc.values():
            for e in lst:
                out[e['DataName']] = kind
    return out


def static_doc(rf):
    """Map/MainField/Static.smubin: the DLC's copy when installed (it adds the DLC shrines), else the base."""
    if rf.exists('Map/MainField/Static.smubin'):
        return gamefiles.byml(rf.read('Map/MainField/Static.smubin'))
    return gamefiles.byml(rf.pack('Pack/Bootup.pack', dlc=False)['Map/MainField/Static.smubin'])


def placed_actors(rf, log=print):
    """Every actor placed in the 80 MainField sections. The DLC's copies of a section win over the base game's."""
    titlebg = rf.pack('Pack/TitleBG.pack', dlc=False)
    aoc = rf.pack('Pack/AocMainField.pack') if rf.exists('Pack/AocMainField.pack') else {}
    objs = []
    for c in 'ABCDEFGHIJ':
        for r in range(1, 9):
            sec = f'{c}-{r}'
            for kind in ('Static', 'Dynamic'):
                rel = f'Map/MainField/{sec}/{sec}_{kind}.smubin'
                if rf.aoc and rf.path(rel) and rf.path(rel) != rf.base / rel:
                    data = rf.read(rel)
                elif rel in aoc:
                    data = aoc[rel]
                elif rel in titlebg:
                    data = titlebg[rel]
                elif rf.exists(rel):
                    data = rf.read(rel, dlc=False)
                else:
                    continue
                for o in gamefiles.byml(data).get('Objs', []):
                    objs.append(o)
        log(f'map data: section {c} read')
    return objs


def korok_kind(o):
    p = o.get('!Parameters', {})
    if p.get('IsHiddenKorokLiftAppear'):
        return 'Under a rock'
    return None


def build(extracted, out=OUT, lang='USen', log=print):
    rf = gamefiles.Romfs(extracted)
    raw, lang = messages(rf, lang)
    text = Text(raw)
    places = text('StaticMsg/LocationMarker')
    dungeons = text('StaticMsg/Dungeon')   # shrine names and their trial subtitles (DungeonNNN_sub)
    actors = text.actors()
    flags = game_flags(rf)
    log(f'map data: {len(flags)} save flags')
    static = static_doc(rf)
    objs = placed_actors(rf, log)
    log(f'map data: {len(objs)} placed actors')

    def flag(name):
        return crc(name) if name in flags else None

    def actor_name(a):
        return actors.get(f'{a}_Name') or actors.get(f'{a.replace("Put", "", 1)}_Name')

    data = {k: [] for k in ('koroks', 'shrines', 'towers', 'divine_beasts', 'locations', 'great_fairies',
                            'hinoxes', 'taluses', 'moldugas', 'lynels', 'armor_chests', 'treasure_chests')}

    # ---- location markers: shrines, towers, Divine Beasts, villages, stables and other places
    seen = set()
    for m in static.get('LocationMarker', []) + static.get('LocationPointer', []):
        sf, mid, icon = m.get('SaveFlag'), m.get('MessageID'), m.get('Icon')
        if not sf or sf in seen or not mid:
            continue
        name = places.get(mid) or mid
        p = pos(m['Translate'])
        if icon == 'Dungeon':
            seen.add(sf)
            o = {'internal_name': mid, 'display_name': name, 'position': p,
                 'completion_hash': flag(f'Clear_{mid}'), 'found_hash': flag(sf)}
            sub = dungeons.get(f'{mid}_sub')
            if sub:
                o['subtitle'] = sub
            data['shrines'].append(o)
        elif icon == 'Tower':
            seen.add(sf)
            n = re.sub(r'\D', '', mid)
            data['towers'].append({'internal_name': mid, 'display_name': name, 'position': p,
                                   'completion_hash': flag(f'MapTower_{int(n):02d}') if n else None})
        elif icon and icon.startswith('Remains'):
            if icon in {o['internal_name'] for o in data['divine_beasts']}:
                continue
            seen.add(sf)
            data['divine_beasts'].append({'internal_name': icon, 'display_name': places.get(icon) or name,
                                          'position': p, 'completion_hash': flag(f'Clear_{icon}')})
        elif (icon in PLACE_ICONS) and sf.startswith('Location_') and sf in flags:
            seen.add(sf)
            data['locations'].append({'internal_name': mid, 'display_name': name, 'position': p,
                                      'completion_hash': crc(sf)})
    # a Divine Beast marker moves with the beast; the location marker with Clear_ is the one that counts
    data['shrines'].sort(key=lambda o: o['internal_name'])
    data['towers'].sort(key=lambda o: o['internal_name'])

    # ---- Korok seeds: Static.smubin's KorokLocation list, with the hidden Korok's save flag
    by_hash = {}
    for o in objs:
        by_hash.setdefault(o.get('HashId'), o)
    for k in static.get('KorokLocation', []):
        f = k.get('Flag')
        if not f or f not in flags:
            continue
        hid = int(f.rsplit('_', 1)[1]) if f.rsplit('_', 1)[-1].isdigit() else None
        actor = by_hash.get(hid, {})
        o = {'completion_hash': crc(f), 'position': pos(k['Translate'])}
        kind = korok_kind(actor or {'!Parameters': k})
        if kind:
            o['type'] = kind
        data['koroks'].append(o)

    # ---- placed actors: Great Fairies, bosses, Lynels, treasure chests
    for o in objs:
        u = o['UnitConfigName']
        hid = o.get('HashId')
        t = o.get('Translate')
        if t is None:
            continue
        if u.startswith('Npc_DressFairy_'):   # the Great Fairy of fountain N (RevivalGreatFairyN+1 when restored)
            n = int(u.rsplit('_', 1)[1]) + 1
            data['great_fairies'].append({'display_name': actor_name(u) or 'Great Fairy', 'position': pos(t),
                                          'completion_hash': flag(f'RevivalGreatFairy{n}'), 'actor': u})
            continue
        for prefix, key in BOSSES:
            if u.startswith(prefix):
                f = flag(f'MainField_IsDefeat_{u}_{hid}')
                if f is not None:
                    data[key].append({'display_name': actor_name(u) or u, 'completion_hash': f,
                                      'position': pos(t), 'actor': u})
                break
        if u.startswith('Enemy_Lynel'):
            data['lynels'].append({'display_name': actor_name(u) or 'Lynel', 'position': pos(t), 'actor': u})
        elif u.startswith('TBox_'):
            f = flag(f'MainField_{u}_{hid}')
            if f is None:
                continue
            drop = (o.get('!Parameters') or {}).get('DropActor') or ''
            key = 'armor_chests' if drop.startswith('Armor_') else 'treasure_chests'
            entry = {'completion_hash': f, 'position': pos(t), 'actor': u}
            if drop:
                entry['display_name'] = actor_name(drop) or drop
                entry['drop'] = drop
            data[key].append(entry)
    # the Great Fairy fountains before restoring: GreatFairyBeforeRevival stands where the fairy will be
    if not data['great_fairies']:
        for o in objs:
            if o['UnitConfigName'] == 'GreatFairyBeforeRevival':
                data['great_fairies'].append({'display_name': 'Great Fairy', 'position': pos(o['Translate'])})

    data = {k: [o for o in v if o.get('completion_hash') is not None or k == 'lynels'] for k, v in data.items()}
    data['meta'] = {'lang': lang}
    write(data, out)
    summary = ', '.join(f'{k} {len(v)}' for k, v in data.items() if k != 'meta')
    log(f'map data: {summary}')
    return data


def write(data, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix('.part')
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    tmp.replace(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--extracted', required=True, help="Savage Wind's extracted folder (romfs, aoc1, ...)")
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--lang', default='USen')
    args = ap.parse_args()
    if not (Path(args.extracted) / 'romfs').is_dir():
        sys.exit('Not a Savage Wind extracted folder (no romfs inside).')
    build(args.extracted, args.out, args.lang)


if __name__ == '__main__':
    main()
