# Progress log

Where the project stands, what was learned along the way, and what's next. Update it with each stage.

## Status (2026-11-11)

| | |
|---|---|
| Version | 0.1.0: Windows exe and Linux binary built by GitHub Actions on the `v0.1.0` tag |
| Tested on | Savage Wind (game 1.9.0 + DLC, English) with saves in `F:\Games\SavageWind`: from source in the browser, and the exe (app window, setup, save) from a Desktop shortcut |
| Also in 0.1.0 | Spoiler-free mode and new-version notice, ported from totk-progress `cb4377f`; README screenshots taken with headless Edge from the running app |
| Started from | [totk-progress](https://github.com/phatnguyen-v1/totk-progress) v1.6.0 (server, page, setup, phone view) |

### Next up
1. Check more saves (later in the game: Divine Beasts, Great Fairies, bosses, quest steps with branches).
2. Try the Linux binary on a real desktop / Steam Deck (CI only runs a start-up smoke test).
3. Korok puzzle types (the hidden Korok links to its puzzle through `LinkTagAnd` / `LinkTagOr` actors), memories
   (`IsGet_MemoryPhoto_NNN`, positions not found yet), Hestu.
4. Interface translations (`web/i18n/<code>.json`; only English so far, game text is already in every language).

## Hero's Path (2026-11-11)

Fork addition: the game's Hero's Path drawn on the map (`herospath.py`, `/api/path`, Hero's Path section in the
panel and button in the map bar).

### Format (`tracker/trackblockNN.sav`)
- Next to the slot folders: `<save>/tracker/trackblock00.sav` beside `<save>/0/game_data.sav` (Switch / emulator
  layout; Savage Wind keeps the same layout under `save/save_0`). Shared by all slots.
- 64 KiB. Header: u16 0, u16 block being written, u32 points in it, u32 1; blocks from 0x40, 0x4C0 bytes each
  (53 per file): u32 play time of the first point, u32 a second time (equal or a little later), 8 bytes 0, then 300
  u32 points, one per 2 s of play.
- Point: bits 0-11 |z|, 12 z sign, 13-25 |x|, 26 x sign, 31 on MainField (clear inside shrines etc., where the
  coordinates are the shrine's own), 27-29 markers around warps/loads (not used). No height.
- Checked against a Yuzu save of a Great Plateau run (6 slots, 3 h): all six `PlayerSavePos` lie on the path within 2
  units, and point times (block time + 2 s x index) line up with `PlayReport_PlayTime` (the last point is 1 s before
  the newest slot's play time; older slots land within a few seconds where Link was moving). The path traces the Plateau's edge.
- Not checked yet: a save with more than one trackblock file (long games; read in file order and sorted by block
  time), and a Savage Wind save folder (assumed to keep `tracker/` like the Switch).

### Page
- Cut at the shown slot's play time (an older slot = the path up to that save), slider for earlier times, replay
  (about 40 s for the whole path), color by time (14 bands), last-30-minutes trail, click for the time you were
  there, distance travelled (world units are metres). Gaps over 150 units in 2 s are warps and break the line.
- Prefs `hpath`, `hpathColor`, `hpathTrail`.

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

### Checked against a public 100% save (2026-11-11)
[Torphedo/BOTW-CompletedSaveFile](https://github.com/Torphedo/BOTW-CompletedSaveFile) release 1.0, `Switch-100.zip`
(game 1.6 format, version 0x471b; kept out of the repo). Slots 0-5, 362 h: Koroks 900/900 (= `HiddenKorok_Number`),
shrines 136/136, towers 15/15, Divine Beasts 4/4, locations 164/164, Great Fairies 4/4, Hinoxes 40/40, Taluses 40/40,
Moldugas 4/4, quests 151 done with only "Destroy Ganon" open (the game reloads to before the final fight).
- Fixed: the Champions' Ballad's Igneo Talus Titan (`Enemy_Golem_Fire_R`) and Molduking (`Enemy_SandwormR`) have
  an `IsDefeat` flag that stays 0 even at 100%, so they're left out (the medal counts are 40 Taluses, 4 Moldugas).
- Chests: 372 of 1,281 opened, armor chests 30/31 (the Great Plateau's Warm Doublet chest wasn't opened). 100%
  doesn't need chests; every chest flag is a never-reset one (`ResetType` 0), so this is the player's real count.
- Slots 6-7 (an earlier run, 26 h): sensible current steps for 39 active quests, the DLC's EX quests all open at
  once as in the game.
