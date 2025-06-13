
# Tetris Singleplayer

## Description

This Tetris game is written in Python using `pygame` and `moderngl`. The game offers classic Tetris gameplay with advanced visual effects, sound support, multiple color themes, and a user-friendly interface.

## Features

- Classic Tetris gameplay with hold functionality
- CRT effects (screen curvature, scanlines, glitch, pixelation, glow, rolling static)
- Multiple color themes to choose from (Green, Purple, Classic, Neon, Pastel, Candy)
- Sound effects (background music, drop and line clear sounds)
- Custom font and CRT overlay
- Main menu, pause screen, game over screen, and options menu
- Sliders for music and sound volume control
- Dynamic scaling to your screen resolution
- Custom "S" block mouse cursor that changes color with the theme
- Retro BIOS-style intro screen

## Requirements

- Python 3.8+
- [pygame](https://www.pygame.org/)
- [moderngl](https://moderngl.readthedocs.io/)
- [numpy](https://numpy.org/)

## Installation

1. Install the required libraries:
    ```sh
    pip install pygame moderngl numpy
    ```

2. Make sure the following files are in your project directory:
    - `tetris_single.py`
    - `Tetris.ttf` (font)
    - `crt.png` (CRT overlay)
    - `theme.mp3` (background music)
    - `drop.mp3` (drop sound)
    - `clear.mp3` (line clear sound)
    - `icon.ico` (app icon)

## Running the Game

To start the game, run:

```sh
python tetris_single.py
```

## Controls

- **Left/Right Arrow** – move block left/right
- **Down Arrow** – soft drop (move block down faster)
- **Up Arrow** – rotate block
- **Space** – hard drop (instant fall)
- **Q** – hold block
- **ESC** – pause/return to menu

## Menu and Options

- **Start** – start a new game
- **Options** – settings (music/sound volume, theme selection)
- **Quit** – exit the game

In the options menu, you can change the color theme and adjust music/sound volumes using sliders.

## Project Structure

```
clear.mp3
crt.png
drop.mp3
icon.ico
tetris_single.py
Tetris.ttf
theme.mp3
```

- `tetris_single.py` – main game file ([tetris_single.py](tetris_single.py))
- `Tetris.ttf` – game font
- `crt.png` – CRT overlay texture
- `theme.mp3` – background music
- `drop.mp3`, `clear.mp3` – sound effects
- `icon.ico` – app icon (optional)

## Troubleshooting

- If the game doesn’t start or sound/graphics don’t work, make sure all resource files are in the same directory as `tetris_single.py`.
- For issues with `moderngl`, ensure your graphics drivers are up to date.

## License

This project is for personal and educational use.

Enjoy the game!


## Appendix

### EXE file
- You can find full .exe file under this link on my itch.io site: [itch.io](https://marcin-sulewski.itch.io/retro-tetris)


### Credits

- Inspired by classic Tetris and retro CRT aesthetics.
- Uses [pygame](https://www.pygame.org/) and [moderngl](https://moderngl.readthedocs.io/).
---

### Contact

For questions, suggestions, or bug reports, please contact the project author.

