import sys
import os
import pygame
import numpy as np
import math
import ctypes
import random
import json
import ast
import re
from OpenGL.GL import *
from pygame.locals import DOUBLEBUF, OPENGL, QUIT, KEYDOWN

from src.end_screen import display_end_screen
from src.game_launcher import start_game

# Import helper modules:
from utils.window_manager import WindowManager
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_square, create_circle, create_object

# --- Helper Functions ---
def load_shader_source(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def translation_matrix(x, y, z):
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ], dtype=np.float32)

def draw_text(text, font_obj, pos_x, pos_y):
    """Renders text onto a texture and draws it as a quad with its bottom-left corner at (pos_x, pos_y)."""
    text_surface = font_obj.render(text, True, (255, 255, 255)).convert_alpha()
    text_width, text_height = text_surface.get_size()
    text_data = pygame.image.tostring(text_surface, 'RGBA', True)

    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(pos_x, pos_y)
    glTexCoord2f(1, 0); glVertex2f(pos_x + text_width, pos_y)
    glTexCoord2f(1, 1); glVertex2f(pos_x + text_width, pos_y + text_height)
    glTexCoord2f(0, 1); glVertex2f(pos_x, pos_y + text_height)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glDeleteTextures([texture])

# --- Background Setup ---
bg_path = os.path.join(os.path.dirname(__file__), "../../assets/textures/space.jpg")
try:
    bg_image = pygame.image.load(bg_path).convert_alpha()
except Exception as e:
    print("Error loading background image:", e)
    sys.exit(1)
bg_width, bg_height = bg_image.get_size()
bg_data = pygame.image.tostring(bg_image, "RGBA", True)
bg_texture = glGenTextures(1)
glBindTexture(GL_TEXTURE_2D, bg_texture)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, bg_width, bg_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, bg_data)
glBindTexture(GL_TEXTURE_2D, 0)

# --- Checkpoint Functions ---
CHECKPOINT_FILE = "saves/river_checkpoint.json"

def save_checkpoint(lives, health, keys_collected, waves, lily_pads, keys):
    """
    Saves the current game state to a JSON file.
    """
    data = {}
    data["lives"] = lives
    data["health"] = health
    data["keys_collected"] = keys_collected
    data["waves"] = []
    for wave in waves:
        data["waves"].append({
            "pos": wave.pos,
            "speed": wave.speed,
            "width": wave.width,
            "height": wave.height
        })
    data["lily_pads"] = []
    for lp in lily_pads:
        data["lily_pads"].append({
            "pos": lp.pos,
            "speed": lp.speed,
            "direction": lp.direction,
            "radius": lp.radius
        })
    data["keys"] = []
    for key in keys:
        try:
            lp_index = lily_pads.index(key['lily_pad'])
        except ValueError:
            lp_index = -1
        data["keys"].append({
            "lily_pad_index": lp_index,
            "collected": key['collected']
        })
    with open("saves/river_checkpoint.json", "w") as f:
        json.dump(data, f)
    print("Checkpoint saved.")

def load_checkpoint_data():
    with open("saves/river_checkpoint.json", "r") as f:
        return json.load(f)

# --- River-Specific Classes ---
# (Assuming you have LilyPad and Wave classes in biomes/river/)
from biomes.river.lilypad import LilyPad
from biomes.river.waves import Wave

# --- State Initialization ---
def initialize_game_state(state_data, model_loc):
    # Create environment objects (grass and river geometry) are static; we focus on dynamic objects.
    # Create lily pads, waves, keys and the player.
    
    # Player: defaults
    if state_data:
        lives = state_data.get("lives", 3)
        health = state_data.get("health", 100)
    else:
        lives = 3
        health = 100
    # Create the player (using a circle)
    player_radius = 0.05
    from assets.objects.objects import create_circle
    player_vertices, player_indices = create_circle([0,0,0], player_radius, [1.0, 0.5, 0.0], points=30)
    player_vao, player_count = create_object(player_vertices, player_indices)
    # We'll store player data in a dict for now:
    player = {"pos": [-0.8, 0.0, 0.0], "vao": player_vao, "count": player_count, "radius": player_radius}
    
    # Create lily pads (using your fixed y positions)
    fixed_y_positions = [-0.1, 0.15, -0.25, 0.3, -0.4, 0.45]
    lily_pads = [LilyPad(random.uniform(-0.05, 0.05), y,
                         random.uniform(0.1, 0.3),
                         random.choice([-1, 1]), 0.59, -0.59)
                 for y in fixed_y_positions]
    if state_data:
        lp_data = state_data.get("lily_pads", [])
        for i, d in enumerate(lp_data):
            if i < len(lily_pads):
                lily_pads[i].pos = d.get("pos", lily_pads[i].pos)
                lily_pads[i].speed = d.get("speed", lily_pads[i].speed)
                lily_pads[i].direction = d.get("direction", lily_pads[i].direction)
                lily_pads[i].radius = d.get("radius", lily_pads[i].radius)
    
    # Create waves
    waves = [Wave(-0.65 + i * 0.4, random.uniform(0.05, 0.1), [0.0, 0.0, 1.0],
                  random.uniform(0.1, 0.3), 2.5)
             for i in range(2)]
    if state_data:
        waves_data = state_data.get("waves", [])
        for i, d in enumerate(waves_data):
            if i < len(waves):
                waves[i].pos = d.get("pos", waves[i].pos)
                waves[i].speed = d.get("speed", waves[i].speed)
                waves[i].width = d.get("width", waves[i].width)
                waves[i].height = d.get("height", waves[i].height)
    
    # Create keys: each key is tied to a lily pad. We'll create keys as dictionaries.
    key_size = 0.03
    from assets.objects.objects import create_square
    keys = []
    # For a new game, randomly select 3 lily pads:
    if not state_data:
        selected_lily_pads = random.sample(lily_pads, 3)
        for lp in selected_lily_pads:
            key_vertices, key_indices = create_square([0,0,0], key_size, [1.0,1.0,0.0])
            key_vao, key_count = create_object(key_vertices, key_indices)
            keys.append({'vao': key_vao, 'count': key_count, 'lily_pad': lp, 'collected': False})
    else:
        # Recreate keys (we assume same number: 3) then update collected flag from checkpoint.
        selected_lily_pads = random.sample(lily_pads, 3)
        for lp in selected_lily_pads:
            key_vertices, key_indices = create_square([0,0,0], key_size, [1.0,1.0,0.0])
            key_vao, key_count = create_object(key_vertices, key_indices)
            keys.append({'vao': key_vao, 'count': key_count, 'lily_pad': lp, 'collected': False})
        keys_data = state_data.get("keys", [])
        for i, d in enumerate(keys_data):
            if i < len(keys):
                keys[i]['collected'] = d.get("collected", False)
    
    # Return all dynamic assets
    return {"player": player, "lily_pads": lily_pads, "waves": waves, "keys": keys, "lives": lives, "health": health}

# --- Game Loop ---
def run_game_loop(wm, assets, modelLoc, shader_program):
    hud_font = pygame.font.SysFont("Arial", 24)
    # Unpack assets
    player = assets["player"]
    lily_pads = assets["lily_pads"]
    waves = assets["waves"]
    keys = assets["keys"]
    lives = assets["lives"]
    health = assets["health"]
    
    # Create environment geometry (grass and river)
    left_grass_vertices, left_grass_indices = create_rect(-1.0, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    left_grass_vao, left_grass_count = create_object(left_grass_vertices, left_grass_indices)
    river_vertices, river_indices = create_rect(-0.7, -1.0, 1.4, 2.0, [0.0, 0.0, 0.7])
    river_vao, river_count = create_object(river_vertices, river_indices)
    right_grass_vertices, right_grass_indices = create_rect(0.7, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    right_grass_vao, right_grass_count = create_object(right_grass_vertices, right_grass_indices)
    
    # Variables for player movement and jumping
    player_pos = assets["player"]["pos"]  # [x, y, z]
    jump_duration = 30
    jump_height = 0.3
    jump_time = 0
    is_jumping = False
    jump_offset = 0

    # Variables for health blinking
    health_cooldown = 0
    blink_interval = 0.05
    blink_timer = 0
    player_visible = True

    clock = pygame.time.Clock()
    game_over = False
    game_over_timer = 0.0

    # Create a shadow for the player
    shadow_vertices, shadow_indices = create_circle([0,0,0], 0.05, [0.2, 0.2, 0.2], points=30)
    shadow_vao, shadow_count = create_object(shadow_vertices, shadow_indices)
    
    width, height_screen = wm.width, wm.height

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        # Process events
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not is_jumping:
                    is_jumping = True
                    jump_time = 0
                elif event.key == pygame.K_F5:
                    collected_count = sum(1 for k in keys if k['collected'])
                    save_checkpoint(lives, health, collected_count, waves, lily_pads, keys)
                elif event.key == pygame.K_F9:
                    try:
                        data = load_checkpoint_data()
                        lives = data.get("lives", lives)
                        health = data.get("health", health)
                        # Update waves and lily pads if needed…
                        keys_data = data.get("keys", [])
                        for i, d in enumerate(keys_data):
                            if i < len(keys):
                                keys[i]['collected'] = d.get("collected", keys[i]['collected'])
                        print("Checkpoint loaded.")
                    except Exception as e:
                        print("Error loading checkpoint:", e)
        
        # Movement input
        keys_pressed = pygame.key.get_pressed()
        move_speed = 0.8 * (0.5 if is_jumping else 1)
        if keys_pressed[pygame.K_a]:
            player_pos[0] -= move_speed * dt
        if keys_pressed[pygame.K_d]:
            player_pos[0] += move_speed * dt
        if keys_pressed[pygame.K_w]:
            player_pos[1] += move_speed * dt
        if keys_pressed[pygame.K_s]:
            player_pos[1] -= move_speed * dt

        # Start jump if active
        if is_jumping:
            jump_time += 1
            t = jump_time / jump_duration
            jump_offset = jump_height * 4 * t * (1 - t)
            if jump_time >= jump_duration:
                is_jumping = False
        else:
            jump_offset = 0

        # Update blinking if under health cooldown
        if health_cooldown > 0:
            health_cooldown -= dt
            blink_timer += dt
            if blink_timer >= blink_interval:
                player_visible = not player_visible
                blink_timer = 0
        else:
            player_visible = True

        # Clamp player position
        player_pos[0] = max(-1.0, min(1.0, player_pos[0]))
        player_pos[1] = max(-1.0, min(1.0, player_pos[1]))
        effective_y = player_pos[1] + jump_offset

        # Update waves
        for wave in waves:
            wave.update(dt)
            if wave.collides_with_player(player_pos[0], effective_y) and health_cooldown <= 0:
                health -= 5
                collected_count = sum(1 for k in keys if k['collected'])
                save_checkpoint(lives, health, collected_count, waves, lily_pads, keys)
                health_cooldown = 0.5
                if health <= 0:
                    lives -= 1
                    collected_count = sum(1 for k in keys if k['collected'])
                    save_checkpoint(lives, health, collected_count, waves, lily_pads, keys)
                    if lives <= 0:
                        game_over = True
                    else:
                        player_pos = [-0.8, 0.0, 0.0]
                        health = 100

        # Check for lily pad collisions and key collection
        if -0.7 <= player_pos[0] <= 0.7:
            on_lily_pad = False
            for lp in lily_pads:
                distance = np.sqrt((player_pos[0] - lp.pos[0])**2 + ((effective_y) - lp.pos[1]*2)**2)
                if distance < 0.15:
                    on_lily_pad = True
                    for key in keys:
                        if not key['collected'] and key['lily_pad'] == lp:
                            if distance < 0.1:
                                key['collected'] = True
                                collected_count = sum(1 for k in keys if k['collected'])
                                save_checkpoint(lives, health, collected_count, waves, lily_pads, keys)
                    break
            if not on_lily_pad and not is_jumping:
                lives -= 1
                collected_count = sum(1 for k in keys if k['collected'])
                save_checkpoint(lives, health, collected_count, waves, lily_pads, keys)
                if lives <= 0:
                    game_over = True
                    collected_count = sum(1 for k in keys if k['collected'])
                    save_checkpoint(lives, health, collected_count, waves, lily_pads, keys)
                else:
                    player_pos = [-0.8, 0.0, 0.0]

        # Check win condition: if player reaches the right side and all keys are collected.
        if player_pos[0] > 0.7:
            all_keys_collected = all(key['collected'] for key in keys)
            if all_keys_collected:
                running = False
                with open("saves/river_checkpoint.txt", "w") as file:
                    file.write("")
            else:
                player_pos[0] = min(0.75, player_pos[0])
        
        # Update lily pads
        for lp in lily_pads:
            lp.update(dt)
        
        # --- Render Background ---
        glViewport(0, 0, width, height_screen)
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        
        shader_program.use()
        identity = np.eye(4, dtype=np.float32)
        glUniformMatrix4fv(modelLoc, 1, GL_TRUE, identity)
        
        glBindVertexArray(left_grass_vao)
        glDrawElements(GL_TRIANGLES, left_grass_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        
        glBindVertexArray(river_vao)
        glDrawElements(GL_TRIANGLES, river_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        
        glBindVertexArray(right_grass_vao)
        glDrawElements(GL_TRIANGLES, right_grass_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        
        for wave in waves:
            wave_model = translation_matrix(wave.pos[0], wave.pos[1], wave.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, wave_model)
            glBindVertexArray(wave.vao)
            glDrawElements(GL_TRIANGLES, wave.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
        
        for lp in lily_pads:
            model = translation_matrix(lp.pos[0], lp.pos[1], lp.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(lp.vao)
            glDrawElements(GL_TRIANGLES, lp.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
        
        for key in keys:
            if not key.get('collected', False):
                key_pos = key['lily_pad'].pos
                key_model = translation_matrix(key_pos[0], key_pos[1]*2, key_pos[2])
                glUniformMatrix4fv(modelLoc, 1, GL_TRUE, key_model)
                glBindVertexArray(key['vao'])
                glDrawElements(GL_TRIANGLES, key['count'], GL_UNSIGNED_INT, None)
                glBindVertexArray(0)
        
        # Render player shadow and player if visible
        shadow_scale = max(0.3, 1.0 - jump_offset/jump_height)
        shadow_model = np.array([
            [shadow_scale, 0, 0, player_pos[0]],
            [0, shadow_scale, 0, player_pos[1] - 0.01],
            [0, 0, 1, player_pos[2]],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        if player_visible:
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, shadow_model)
            glBindVertexArray(shadow_vao)
            glDrawElements(GL_TRIANGLES, shadow_count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
            
            model = translation_matrix(player_pos[0], effective_y, player_pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(player["vao"])
            glDrawElements(GL_TRIANGLES, player["count"], GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
        
        # Render HUD
        glUseProgram(0)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, width, 0, height_screen, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        hud_text = f"Lives: {'♥'*lives}"
        draw_text(hud_text, hud_font, 20, height_screen - 40)
        health_bar_width = 200
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(20, height_screen - 50)
        glVertex2f(20, height_screen - 70)
        glVertex2f(20 + health_bar_width, height_screen - 70)
        glVertex2f(20 + health_bar_width, height_screen - 50)
        glEnd()
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_QUADS)
        glVertex2f(20, height_screen - 50)
        glVertex2f(20, height_screen - 70)
        glVertex2f(20 + health_bar_width * (health / 100), height_screen - 70)
        glVertex2f(20 + health_bar_width * (health / 100), height_screen - 50)
        glEnd()
        key_text = f"Keys: {sum(key['collected'] for key in keys)}/3"
        draw_text(key_text, hud_font, 20, height_screen - 100)
        
        if not game_over and sum(key['collected'] for key in keys) < 3:
            prompt = "Collect all the keys to complete biome"
            prompt_width, _ = hud_font.size(prompt)
            draw_text(prompt, hud_font, (width - prompt_width) // 2, 20)
        # if game_over:
        #     over_msg = "Game Over"
        #     over_width, _ = hud_font.size(over_msg)
        #     draw_text(over_msg, hud_font, (width - over_width) // 2, height_screen // 2)
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        wm.swap_buffers()
        
        if game_over:
            # pygame.time.wait(2000)
            running = False
        
    # End of game loop: clear checkpoint on win
    if not game_over:
        with open("saves/river_checkpoint.txt", "w") as file:
            file.write("")
    
    # Show end screen
    option = display_end_screen(wm, won=(not game_over))
    print("User selected:", option)
    if option == "New Game":
        new_game(wm)
    elif option == "Select Biome":
        start_game(wm)
    else:
        wm.quit()
        pygame.font.quit()
        sys.exit()

# --- Entry Points ---
def new_game(wm):
    def load_shader_source(filepath):
        with open(filepath, 'r') as f:
            return f.read()
    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")
    shader_program = Shader(vertex_shader_source, fragment_shader_source)
    shader_program.use()
    global modelLoc
    modelLoc = glGetUniformLocation(shader_program.ID, "model")
    state_data = None
    assets = initialize_game_state(state_data, modelLoc)
    run_game_loop(wm, assets, modelLoc, shader_program)

def load_game(wm):
    def load_shader_source(filepath):
        with open(filepath, 'r') as f:
            return f.read()
    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")
    shader_program = Shader(vertex_shader_source, fragment_shader_source)
    shader_program.use()
    global modelLoc
    modelLoc = glGetUniformLocation(shader_program.ID, "model")
    try:
        state_data = load_checkpoint_data()
    except Exception as e:
        print("No checkpoint found; starting new game.", e)
        state_data = None
    assets = initialize_game_state(state_data, modelLoc)
    run_game_loop(wm, assets, modelLoc, shader_program)

if __name__ == "__main__":
    pygame.init()
    wm = WindowManager(800,600,"River Biome")
    # To start a new game:
    new_game(wm)
    # To load from checkpoint instead, you can call:
    # load_game(wm)
