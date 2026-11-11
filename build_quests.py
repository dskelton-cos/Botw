"""Build assets/quests.json from your own Breath of the Wild game files (Savage Wind's extracted folder).

    python build_quests.py --extracted <Savage Wind data folder>\\extracted [--lang USen]

Reads Quest/QuestProduct.sbquestpack (in Pack/TitleBG.pack: each quest's steps, the flag that ends each
step and the places they point to) and the adventure log texts (QuestMsg/QL_<quest>.msbt), quest giver and
region names from Pack/Bootup_<lang>.pack.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import gamefiles
from build_mapdata import crc, game_flags, messages, Text, placed_actors
from paths import ASSETS

OUT = ASSETS / 'quests.json'
CATEGORY = {'Main': 'main', 'Sub': 'shrine', 'Mini': 'side_quest'}
ORDER = {'main': 0, 'side_quest': 1, 'shrine': 2}


def tidy(s):
    return re.sub(r'\n{3,}', '\n\n', (s or '').replace('\r', '')).strip()


def points(step):
    out = []
    for a in step.get('IndicatorActors') or []:
        loc = a.get('Location')
        if isinstance(loc, dict):
            p = [round(loc['X'], 1), round(loc.get('Y', 0), 1), round(loc['Z'], 1)]
            if p not in out and (p[0], p[2]) != (0, 0):
                out.append(p)
    return out


def build(extracted, out=OUT, lang='USen', log=print, objs=None):
    rf = gamefiles.Romfs(extracted)
    raw, lang = messages(rf, lang)
    text = Text(raw)
    places = text('StaticMsg/LocationMarker')
    actors = text.actors()
    flags = game_flags(rf)
    pack = gamefiles.byml(rf.pack('Pack/TitleBG.pack', dlc=False)['Quest/QuestProduct.sbquestpack'])
    # quest givers: where the NPC who gives the quest is placed (when there's just one of them)
    if objs is None:
        objs = placed_actors(rf, log=lambda m: None)
    where = {}
    for o in objs:
        u = o['UnitConfigName']
        if u.startswith('Npc_') and 'Translate' in o:
            t = o['Translate']
            where.setdefault(u, []).append([round(t[0], 1), round(t[1], 1), round(t[2], 1)])

    quests = []
    for i, q in enumerate(pack):
        qid = q['Name']
        msg = text(f'QuestMsg/QL_{qid}')
        name = msg.get(f'QL_{qid}_Name')
        if not name or q.get('NotPostNote'):
            continue   # not in the adventure log
        steps = []
        for s in q.get('Steps', []):
            nf = s.get('NextFlag')
            steps.append({
                'name': s.get('Name', ''),
                'flag': crc(nf) if nf and nf in flags else None,
                'text': tidy(msg.get(f'QL_{qid}_{s.get("MessageName")}', '')),
                'points': points(s),
            })
        giver = q.get('Orderer') or ''
        spots = where.get(giver, [])
        exact = 0 < len(spots) <= 3
        start = spots if exact else next((s['points'] for s in steps if s['points']), [])
        ready = f'{qid}_Ready'
        quests.append({
            'id': qid,
            'name': name,
            'category': CATEGORY.get(q.get('Type'), 'side_quest'),
            'sort': i,
            'giver': actors.get(f'{giver}_Name', '') if giver.startswith('Npc') else '',
            'region': places.get(q.get('Location') or '', ''),
            'ready': crc(ready) if ready in flags else None,
            'start': {'points': start[:4], 'exact': exact},
            'requires': None,
            'steps': steps,
        })
    quests.sort(key=lambda x: (ORDER.get(x['category'], 9), x['sort']))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix('.part')
    tmp.write_text(json.dumps({'lang': lang, 'quests': quests}, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')
    tmp.replace(out)
    by = {}
    for x in quests:
        by[x['category']] = by.get(x['category'], 0) + 1
    log(f'{len(quests)} quests {by}')
    return quests


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--extracted', required=True)
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--lang', default='USen')
    args = ap.parse_args()
    if not (Path(args.extracted) / 'romfs').is_dir():
        sys.exit('Not a Savage Wind extracted folder (no romfs inside).')
    build(args.extracted, args.out, args.lang)


if __name__ == '__main__':
    main()
