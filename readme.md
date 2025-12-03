# Forest Relic

Top-down, room-clear built with Pygame Zero. Grab every gem, wipe every enemy, and reach the exit. Spikes toggle, turrets track, enemies chase on sight, and hearts sometimes drop to heal you. Three stages; beat them all to win.

## Run it
- Install: `pip install pgzero`
- Play: `pgzrun main.py` (run from this folder)
- Prefer `python main.py`? Append `import pgzrun; pgzrun.go()` at the bottom first.

## Controls
- Move: WASD
- Shoot: Left click toward the aim
- Reload: R
- Menu: Click buttons; ESC to return to menu mid-run

## Rules and flow
- Each stage randomizes gems, enemies, and turrets. Clear all enemies and grab all gems to unlock the exit, then step on it.
- Enemies chase if they see you; spikes pulse on/off; turrets track and fire; hearts can drop to restore HP.
- Ammo is limited—reload between fights. Touching enemies/spikes or getting shot hurts.

## Assets and sound
- Pixel sprites live in `images/`. Effects in `sounds/`. Background loop in `music/music.wav`.
- All assets in this folder were generated for this project; no external downloads required.

## Modules
- Pygame Zero, math, random, and the allowed `pygame.Rect`.
