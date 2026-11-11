# Progress log

Where the project stands, what was learned along the way, and what's next. Update it with each stage.

## Status (2026-11-11)

| | |
|---|---|
| Version | 0.1.0, not released; runs from source |
| Tested on | Savage Wind (game 1.9.0 + DLC, English) with saves in `F:\Games\SavageWind`, from source in the browser |
| Started from | [totk-progress](https://github.com/phatnguyen-v1/totk-progress) v1.6.0 (server, page, setup, phone view) |

### Next up
1. Check more saves (later in the game: Divine Beasts, Great Fairies, bosses, quest steps with branches).
2. Build and try the Windows exe (`build_exe.bat`) and the Linux binary; a GitHub repo and release workflow.
3. Korok puzzle types (the hidden Korok links to its puzzle through `LinkTagAnd` / `LinkTagOr` actors), memories
   (`IsGet_MemoryPhoto_NNN`, positions not found yet), Hestu.
4. Interface translations (`web/i18n/<code>.json`; only English so far, game text is already in every language).

## v0.1.0 (2026-11-11): first version

### Game files (`gamefiles.py`)
- Savage Wind keeps the romfs extracted as plain files: `<data>/extracted/romfs`, DLC in `extracted/aoc1` (aoc2
  only has `System`). `Romfs` prefers the DLC copy of a path.
- `.s*` files are Yaz0 (pure Python decoder; the map tiles take ~13 s in all). `.pack` / `.ssarc` / `.sblarc` are
  SARC, little endian. BYML v2+ little endian. MSBT as in TotK.
- `Pack/Bootup.pack`: `GameData/gamedata.ssarc` (45,027 flag names), `Map/MainField/Static.smubin`,
  `Layout/Common.sblarc`. `Pack/TitleBG.pack`: the 80 `_Static` map sections, `Quest/QuestProduct.sbquestpack`.
  `Pack/Bootup_<lang>.pack` -> `Message/Msg_<lang>.product.ssarc`: `StaticMsg/LocationMarker`, `StaticMsg/Dungeon`
  (shrine subtitles `DungeonNNN_sub`), `ActorType/*` (`<actor>_Name`), `QuestMsg/QL_<quest>` (`_Name`, step texts).
- DLC: `aoc1/Map/MainField/Static.smubin` (adds the 16 DLC shrines), loose `_Static` / `_Dynamic` sections and
  `aoc1/Pack/AocMainField.pack`.

### Map tiles (`maptiles.py`)
- `UI/MapTex/MainField/MapTex{,1,2,3}_<C>-<R>[_<n>].sbmaptex`: columns `Z, A-K` (west to east), rows `0-9`
  (north to south), 1000 world units each, same grid as TotK. 3000 / 840 / 300 / 135 px.
- No suffix = fully revealed map; `_0` = unexplored blueprint; other numbers = partly revealed (tower region bits).
- Yaz0 -> BFRES with an embedded BNTX; BC1 sRGB, block linear. The BNTX isn't relocated: mip pointers are 0 and
  relative to the `BRTD` data (`BRTD + 0x10`); reading from 0 shifted every tile by a few GOB columns.

### Save (`savefile.py`)
- `game_data.sav`: u32 version (0x4730 on 1.9.0), 0xFFFFFFFF, u32 1, then (u32 CRC32(name), u32 value) pairs
  sorted by hash. Vectors / strings / arrays: several pairs with the same hash.
- Link: `PlayerSavePos` (3 floats), only when `PlayerSavePosMapType` is `MainField`. Play time:
  `PlayReport_PlayTime` (seconds).
- Saves: `<data>/save/save_0/<slot>/game_data.sav` (slots 0-5, newest file wins).

### Quests (`build_quests.py`)
- 170 quests in the pack, 152 with an adventure log name. `Type`: `Main` (20), `Mini` = side quests (90, with the
  DLC's EX quests), `Sub` = shrine quests (42).
- Each step's `NextFlag` is set when the game reaches the step (the first one is `<quest>_Activated`). The log shows
  the text of the last step reached (`QL_<quest>_<MessageName>`); the map target is the next step's
  `IndicatorActors`. Done = the last saved step flag set. Not started = `<quest>_Ready`; otherwise not available.

### Checked against the owner's save (slot 2, 3 h 22 min)
5 Koroks (= `HiddenKorok_Number`), 4 shrines (the Great Plateau's), Great Plateau tower, 2 main quests done and
"Seek Out Impa" in progress with its target at Impa's house.
