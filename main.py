# main.py

import sys
from utils.window_manager import WindowManager
from src.welcome import display_welcome_screen
from src.game_launcher import start_game

def main():
    wm = WindowManager(800, 800, "2D Platformer")
    
    # --- Welcome Screen ---
    welcome_choice = display_welcome_screen(wm)
    
    # Start the game loop.
    start_game(wm)
    
    # Cleanup when the game loop ends.
    wm.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
