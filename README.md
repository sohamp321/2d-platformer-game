# 2D Platformer Game

A Python-based 2D platformer game featuring multiple unique biomes and gameplay environments.

## Features

- Multiple themed biomes:

  - River Biome - Navigate through water and lily pads
  - Space Biome - Experience a low gravity challenge with asteroid barrage
  - Upside Down Biome - Gravity-defying challenges
- Game Features:

  - OpenGL-based graphics rendering
  - Checkpoint save system
  - Custom shader support
  - Interactive HUD system
  - Multiple game modes (New Game/Load Game)

## Requirements

- Python 3.x
- PyGame
- OpenGL
- NumPy

## Installation

1. Clone the repository
2. Run `run_game.py` to create a Python environment with all the dependencies installed using

   ```bash
   python run_game.py
   ```
3. Run the same file whever you wish to play the game

# Project Structure

## Core Files

- [main.py](main.py) - Main entry point
- [run_game.py](run_game.py) - Game runner and initialization
- [README.md](README.md) - Project documentation

## Biomes

[biomes/](biomes/)

- [river/](biomes/river/) - Water-based platforming
  - River biome implementation
  - Checkpoint system
  - Lily pad mechanics
- [space/](biomes/space/) - Zero gravity environment
  - Space biome implementation
  - Asteroid mechanics
  - Platform mechanics
- [upside_down/](biomes/upside_down/) - Inverted gravity biome
  - Upside down biome implementation

## Core Assets

[assets/](assets/)

- [fonts/](assets/fonts/) - Game fonts
- [maker/](assets/maker/) - Asset creation tools
- [objects/](assets/objects/) - Game object definitions
- [shaders/](assets/shaders/)
  - [default.vert](assets/shaders/default.vert) - Default vertex shader
  - [default.frag](assets/shaders/default.frag) - Default fragment shader
- [textures/](assets/textures/) - Game textures

## Save System

[saves/](saves/)

- [river_checkpoint.json](saves/river_checkpoint.json)
- [space_checkpoint.json](saves/space_checkpoint.json)
- [upside_down_checkpoint.json](saves/upside_down_checkpoint.json)

## Source Code

[src/](src/)

- Core game logic and utilities and screens

## Utils

[utils/](utils/)

- Helper functions and utilities

## Environment

[env/](env/)

- Python virtual environment
- Dependencies
