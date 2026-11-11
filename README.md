# BotW Progress Map

A companion app for [Savage Wind Recomp](https://github.com/Revivedx/SavageWindRecomp), the native PC port of
*Breath of the Wild*. It reads your save and shows what you have and haven't found on the map of Hyrule: Korok
seeds, shrines (including ones you found but haven't finished), Sheikah Towers, Divine Beasts, Great Fairies,
locations, Hinoxes, Taluses, Moldugas, Lynels, armor chests and every other treasure chest (with what's inside).
A yellow arrow marks where Link was when the game last saved; the **Link** button jumps there.

The **Quests** tab lists the 152 adventure-log quests (Main Quests, Side Quests, Shrine Quests, with the DLC's) with
their status (in progress, not started, not available yet, done), the quest giver and region, and the adventure log
text of the step you're on. "Show on map" jumps to where the quest wants you to go, and active quest targets can be
shown on the map (gold). "Where to start quests" puts a blue **!** where the quest giver stands.

It re-reads the save every few seconds, so the map updates on its own whenever the game saves. It only ever
reads your game and save files; it never writes to them.

It's the sister app of [TotK Progress Map](https://github.com/phatnguyen-v1/totk-progress) and works the same way.

## Get started

You need Savage Wind set up with your game files (game version 1.9.0, with or without the DLC). The app builds
its map, collectibles and quests from those files.

1. Run the app (see *Run from source* below).
2. The setup page opens. Pick your Savage Wind folder: the one with `savagewind.exe`, or its data folder (the one
   with `extracted` and `save`, e.g. the `SAVAGEWIND_DATA_ROOT` you set). The app looks on your drives and usually
   finds it; otherwise click **Browse…**.
3. Click **Set up**. It draws the map and finds every shrine, Korok, tower, boss, chest and quest in your own game
   files (about 20 seconds). Then the map opens with your progress.

**⚙** at the top of the panel changes the game folder, the language, and has *Open in browser* and the phone view.

**On your phone:** click the phone button at the bottom right of the map, *Turn on*, and scan the QR code. Only
phones and tablets on the **same Wi-Fi or network** as your PC can open it. They get the same map, read-only.

The map starts with Koroks, shrines, towers, Divine Beasts, Great Fairies and armor chests; turn on more in the
legend. Your choices (legend, filters, tab) are kept by the app.

Place, item and quest names and quest texts come from your game files, in the language Savage Wind is set to
(`text_language` in its `savagewind.ini`); pick another of the game's languages in **⚙** → *Language*. The app's
own interface is in English for now.

## Run from source

Needs Python 3.10+. Double-click `start.bat` (Linux: `sh start.sh`), or:

```
pip install -r requirements.txt   # texture2ddecoder and Pillow, to draw the map from the game's textures
python server.py                  # opens the app window (or http://localhost:8788/) and walks you through setup
```

Options: `--save-dir DIR` reads saves from another folder (one with `<slot>/game_data.sav`), `--port`, `--browser`,
`--no-browser`. `BOTW_DIR` points the folder search at your Savage Wind data folder.

Building a single-file app: `build_exe.bat` (Windows) or `sh build_linux.sh` (Linux).

## How it works

| What | From the game files | Done when (save flag, CRC32 of the name in `game_data.sav`) |
|---|---|---|
| Map | `UI/MapTex/MainField/MapTex{1,2}_<col>-<row>.sbmaptex` (Yaz0 BFRES, BC1) | |
| Shrines | `Map/MainField/Static.smubin` `LocationMarker` `Icon: Dungeon` | `Clear_DungeonNNN`; found: `Location_DungeonNNN` |
| Sheikah Towers | `LocationMarker` `Icon: Tower` (`TowerNN`) | `MapTower_NN` |
| Divine Beasts | `LocationMarker` `Icon: Remains*` | `Clear_Remains<Name>` |
| Locations | `LocationMarker` / `LocationPointer` with a `Location_*` save flag | that flag |
| Korok seeds | `Static.smubin` `KorokLocation` | its `Flag` (`MainField_Npc_HiddenKorok*_<id>`) |
| Great Fairies | placed `Npc_DressFairy_0N` | `RevivalGreatFairy<N+1>` |
| Hinox, Talus, Molduga | placed `Enemy_Giant*`, `Enemy_Golem*`, `Enemy_Sandworm*` | `MainField_IsDefeat_<actor>_<id>` |
| Chests | placed `TBox_*`, contents from `DropActor` | `MainField_<actor>_<id>` |
| Quests | `Quest/QuestProduct.sbquestpack` (in `TitleBG.pack`), texts `QuestMsg/QL_<quest>.msbt` | each step's `NextFlag` |

Placed actors are read from the 80 map sections (`Map/MainField/<A-J>-<1-8>_{Static,Dynamic}.smubin`, the DLC's
copies first). Lynels come back after every Blood Moon, so they're shown but not tracked.
