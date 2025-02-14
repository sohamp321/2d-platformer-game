# game_launcher.py

import sys
from utils.window_manager import WindowManager
from src.select_biome import display_biome_menu
from src.select_game_mode import display_game_menu

def start_game(wm):
    # --- Biome Selection ---
    selected_biome = display_biome_menu(wm)
    print("Selected Biome:", selected_biome)
    
    # --- Game Mode Menu ---
    game_mode = display_game_menu(wm)
    print("Game Mode Selected:", game_mode)
    
    # --- Launch the Appropriate Biome ---
    if selected_biome.lower() == "river":
        from biomes.river import river
        if game_mode.lower() == "new game":
            river.new_game(wm)
        elif game_mode.lower() == "load game":
            river.load_game(wm)
        else:
            print("Invalid game mode selected.")
            sys.exit(1)
    elif selected_biome.lower() == "space":
        from biomes.space import space
        if game_mode.lower() == "new game":
            space.new_game(wm)
        elif game_mode.lower() == "load game":
            space.load_game(wm)
        else:
            print("Invalid game mode selected.")
            sys.exit(1)
    elif selected_biome.lower() == "upside down":
        from biomes.upside_down import upside_down
        if game_mode.lower() == "new game":
            upside_down.new_game(wm)
        elif game_mode.lower() == "load game":
            upside_down.load_game(wm)
        else:
            print("Invalid game mode selected.")
            sys.exit(1)
    else:
        print("Biome not implemented. Exiting.")
        sys.exit(1)
