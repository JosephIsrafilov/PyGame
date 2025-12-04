# Forest Relic

Top-down, room-clear built with Pygame Zero. Collect every gem, clear every enemy, and hit the exit. Spikes toggle, turrets track, enemies chase on sight, and hearts sometimes drop to heal you. Three stages; beat them all to win.

## Run it
- Install: `pip install pgzero`
- Play: `pgzrun main.py` (run from this folder)
- If you prefer `python main.py`, append `import pgzrun; pgzrun.go()` at the bottom first.

## Controls
- Move: Arrow keys or WASD
- Shoot: Left click toward where you want to fire
- Reload: R
- Menu: Click buttons; ESC to return to menu mid-run

## Rules and flow
- Each stage randomizes gems, enemies, and turrets. Clear all enemies and pick up all gems to unlock the exit, then step on it.
- Enemies pursue if they see you; spikes pulse on/off; turrets track and fire; hearts can drop to restore HP.
- Ammo is limited—reload between fights. Touching enemies/spikes or taking shots reduces HP.

## Assets and sound
- Pixel sprites live in `images/`. Effects in `sounds/`. Background loop in `music/music.wav`.
- All assets in this folder were generated for this project; no external downloads required.

## Modules
- Pygame Zero, math, random, and a tiny custom `rect_stub.Rect` (no pygame usage).
