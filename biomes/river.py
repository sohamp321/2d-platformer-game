import sys
import pygame
import random
from OpenGL.GL import *
import numpy as np
import ctypes
import ast  
import re 
from utils.window_manager import WindowManager
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_lilypad, create_square, create_circle

# --- Helper functions ---

def load_shader_source(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def create_object(vertices, indices):
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    stride = 6 * ctypes.sizeof(ctypes.c_float)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
    glEnableVertexAttribArray(1)

    glBindVertexArray(0)
    return vao, len(indices)

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

def save_checkpoint(lives, health, keys_collected, waves, lily_pads, keys):
    """
    Saves the current game state to "checkpoint.txt". The file stores:
      - Lives, health, and number of keys collected
      - For each wave: its position, speed, width, and height.
      - For each lily pad: its position, speed, direction, and radius.
      - For each key: the index of its associated lily pad and its 'collected' flag.
    """
    with open("checkpoint.txt", "w") as file:
        file.write(f"Lives: {lives}\n")
        file.write(f"Health: {health}\n")
        file.write(f"Keys Collected: {keys_collected}\n")
        file.write("Waves:\n")
        for i, wave in enumerate(waves):
            file.write(f"  Wave {i}: pos={wave.pos}, speed={wave.speed:.2f}, width={wave.width:.2f}, height={wave.height:.2f}\n")
        file.write("LilyPads:\n")
        for i, lp in enumerate(lily_pads):
            file.write(f"  LilyPad {i}: pos={lp.pos}, speed={lp.speed:.2f}, direction={lp.direction}, radius={lp.radius:.2f}\n")
        file.write("Keys:\n")
        # For each key, store the index of its lily pad and whether it's collected.
        for i, key in enumerate(keys):
            # Determine the lily pad index.
            try:
                lp_index = lily_pads.index(key['lily_pad'])
            except ValueError:
                lp_index = -1
            file.write(f"  Key {i}: lily_pad_index={lp_index}, collected={key['collected']}\n")

def load_checkpoint():
    """
    Loads checkpoint data from "checkpoint.txt" and returns a dictionary with:
      - 'lives': int
      - 'health': float
      - 'keys_collected': int
      - 'waves': list of dicts (each with 'pos', 'speed', 'width', 'height')
      - 'lily_pads': list of dicts (each with 'pos', 'speed', 'direction', 'radius')
      - 'keys': list of dicts (each with 'lily_pad_index' and 'collected')
    Returns None if the file is not found.
    """
    try:
        with open("checkpoint.txt", "r") as file:
            lines = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return None

    checkpoint = {}
    try:
        checkpoint["lives"] = int(next(line for line in lines if line.startswith("Lives:")).split(":", 1)[1].strip())
        checkpoint["health"] = float(next(line for line in lines if line.startswith("Health:")).split(":", 1)[1].strip())
        checkpoint["keys_collected"] = int(next(line for line in lines if line.startswith("Keys Collected:")).split(":", 1)[1].strip())
    except StopIteration:
        return None

    # Get indices for each section.
    try:
        waves_index = lines.index("Waves:")
        lily_index = lines.index("LilyPads:")
    except ValueError:
        checkpoint["waves"] = []
        checkpoint["lily_pads"] = []
        checkpoint["keys"] = []
        return checkpoint

    # Process waves.
    waves_data = []
    for line in lines[waves_index+1:lily_index]:
        if line.startswith("Wave"):
            pos_match = re.search(r"pos=\[([^\]]+)\]", line)
            pos_value = ast.literal_eval("[" + pos_match.group(1) + "]") if pos_match else None
            speed_match = re.search(r"speed=([0-9.]+)", line)
            speed_value = float(speed_match.group(1)) if speed_match else None
            width_match = re.search(r"width=([0-9.]+)", line)
            width_value = float(width_match.group(1)) if width_match else None
            height_match = re.search(r"height=([0-9.]+)", line)
            height_value = float(height_match.group(1)) if height_match else None
            waves_data.append({
                "pos": pos_value,
                "speed": speed_value,
                "width": width_value,
                "height": height_value
            })
    checkpoint["waves"] = waves_data

    # Process lily pads.
    lily_pads_data = []
    try:
        lily_index = lines.index("LilyPads:")
    except ValueError:
        lily_index = len(lines)
    # Determine index for Keys section (if any).
    try:
        keys_index = lines.index("Keys:")
    except ValueError:
        keys_index = len(lines)
    for line in lines[lily_index+1:keys_index]:
        if line.startswith("LilyPad"):
            pos_match = re.search(r"pos=\[([^\]]+)\]", line)
            pos_value = ast.literal_eval("[" + pos_match.group(1) + "]") if pos_match else None
            speed_match = re.search(r"speed=([0-9.]+)", line)
            speed_value = float(speed_match.group(1)) if speed_match else None
            direction_match = re.search(r"direction=(-?[0-9]+)", line)
            direction_value = int(direction_match.group(1)) if direction_match else None
            radius_match = re.search(r"radius=([0-9.]+)", line)
            radius_value = float(radius_match.group(1)) if radius_match else None
            lily_pads_data.append({
                "pos": pos_value,
                "speed": speed_value,
                "direction": direction_value,
                "radius": radius_value
            })
    checkpoint["lily_pads"] = lily_pads_data

    # Process keys.
    keys_data = []
    if "Keys:" in lines:
        keys_start = lines.index("Keys:") + 1
        for line in lines[keys_start:]:
            if line.startswith("Key"):
                lp_index_match = re.search(r"lily_pad_index=(-?[0-9]+)", line)
                lp_index = int(lp_index_match.group(1)) if lp_index_match else -1
                collected_match = re.search(r"collected=(True|False)", line)
                collected_value = (collected_match.group(1) == "True") if collected_match else False
                keys_data.append({
                    "lily_pad_index": lp_index,
                    "collected": collected_value
                })
    checkpoint["keys"] = keys_data

    return checkpoint

# --- Game Object Classes ---
class LilyPad:
    def __init__(self, x, y, speed, direction, right_bound, left_bound, radius=0.1):
        self.pos = [x, y, 0.0]
        self.speed = speed
        self.direction = direction  # 1 = right, -1 = left
        self.radius = radius
        self.vertices, self.indices = create_lilypad(self.pos, self.radius, [0.4, 0.8, 0.4], points=30)
        self.vao, self.count = create_object(self.vertices, self.indices)
        self.right_bound = right_bound
        self.left_bound = left_bound

    def update(self, dt):
        self.pos[0] += self.direction * self.speed * dt
        if self.pos[0] > self.right_bound or self.pos[0] < self.left_bound:
            self.direction = -self.direction

    def collides_with(self, x, y):
        dx = x - self.pos[0]
        dy = y - self.pos[1] * 2
        return np.sqrt(dx*dx + dy*dy) < (self.radius + 0.05)

class Wave:
    def __init__(self, x, speed, color=[0.0, 0.0, 1.0], width=0.1, height=1.8):
        self.pos = [x, 0.0, 0.0]  # Waves move horizontally
        self.speed = speed
        self.width = width
        self.height = height
        vertices, indices = create_rect(0, -1, self.width, self.height, color)
        self.vao, self.count = create_object(vertices, indices)
        
    def reset_position(self, x=None):
        if x is None:
            x = -0.65
        self.pos = [x, 0.0, 0.0]
        self.speed = random.uniform(0.05, 0.2)
        self.width = random.uniform(0.1, 0.2)
        self.height = random.uniform(1.2, 2.0)
        
    def update(self, dt):
        self.pos[0] += self.speed * dt
        if self.pos[0] + self.width > 0.68:
            self.reset_position()
            
    def collides_with_player(self, player_x, player_y):
        return (self.pos[0] - self.width/2 <= player_x <= self.pos[0] + self.width/2)

# --- Main Function ---

def main():
    width, height = 800, 800
    wm = WindowManager(width, height, "Player Movement with HUD")
    pygame.init()
    pygame.font.init()
    hud_font = pygame.font.SysFont("Arial", 24)

    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")
    shader_program = Shader(vertex_shader_source, fragment_shader_source)
    modelLoc = glGetUniformLocation(shader_program.ID, "model")

    # Create environment objects.
    left_grass_vertices, left_grass_indices = create_rect(-1.0, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    left_grass_vao, left_grass_count = create_object(left_grass_vertices, left_grass_indices)
    river_vertices, river_indices = create_rect(-0.7, -1.0, 1.4, 2.0, [0.0, 0.0, 0.7])
    river_vao, river_count = create_object(river_vertices, river_indices)
    right_grass_vertices, right_grass_indices = create_rect(0.7, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    right_grass_vao, right_grass_count = create_object(right_grass_vertices, right_grass_indices)

    # Spawn lily pads.
    fixed_y_positions = [-0.1, 0.15, -0.25, 0.3, -0.4, 0.45]
    lily_pads = [LilyPad(random.uniform(-0.05, 0.05), y,
                         random.uniform(0.1, 0.3),
                         random.choice([-1, 1]), 0.59, -0.59)
                 for y in fixed_y_positions]

    # Create keys on three random lily pads.
    key_size = 0.03
    key_color = [1.0, 1.0, 0.0]
    selected_lily_pads = random.sample(lily_pads, 3)
    keys = []
    for lp in selected_lily_pads:
        key_vertices, key_indices = create_square([0, 0, 0], key_size, key_color)
        key_vao, key_count = create_object(key_vertices, key_indices)
        keys.append({'vao': key_vao, 'count': key_count, 'lily_pad': lp, 'collected': False})

    # Create waves.
    waves = [Wave(-0.65 + i * 0.4, random.uniform(0.05, 0.1), [0.0, 0.0, 1.0],
                  random.uniform(0.1, 0.3), 2.5)
             for i in range(2)]

    # --- Load checkpoint if available ---
    checkpoint = load_checkpoint()
    if checkpoint is not None:
        lives = checkpoint.get("lives", 3)
        health = checkpoint.get("health", 100)
        # Update waves from checkpoint.
        waves_data = checkpoint.get("waves", [])
        for i, wave_data in enumerate(waves_data):
            if i < len(waves):
                waves[i].pos = wave_data.get("pos", waves[i].pos)
                waves[i].speed = wave_data.get("speed", waves[i].speed)
                waves[i].width = wave_data.get("width", waves[i].width)
                waves[i].height = wave_data.get("height", waves[i].height)
        # Update lily pads from checkpoint.
        lily_pads_data = checkpoint.get("lily_pads", [])
        for i, lp_data in enumerate(lily_pads_data):
            if i < len(lily_pads):
                lily_pads[i].pos = lp_data.get("pos", lily_pads[i].pos)
                lily_pads[i].speed = lp_data.get("speed", lily_pads[i].speed)
                lily_pads[i].direction = lp_data.get("direction", lily_pads[i].direction)
                lily_pads[i].radius = lp_data.get("radius", lily_pads[i].radius)
        # Update keys from checkpoint.
        keys_data = checkpoint.get("keys", [])
        # We assume the number of keys remains the same.
        for i, key_data in enumerate(keys_data):
            if i < len(keys):
                keys[i]['collected'] = key_data.get("collected", keys[i]['collected'])
        # Set global checkpoint state variables.
        global_lives = lives
        global_health = health
    else:
        lives = 3
        health = 100

    # Create the player.
    player_pos = [-0.8, 0.0, 0.0]
    player_radius = 0.05
    player_vertices, player_indices = create_circle([0, 0, 0], player_radius, [1.0, 0.5, 0.0], points=30)
    player_vao, player_count = create_object(player_vertices, player_indices)

    speed = 0.8
    jump_duration = 30
    jump_height = 0.3
    jump_time = 0
    is_jumping = False

    clock = pygame.time.Clock()
    # lives and health have been set above
    health_cooldown = 0
    blink_interval = 0.05
    blink_timer = 0
    player_visible = True

    game_over = False
    game_over_timer = 0.0

    running = True
    
    shadow_vertices, shadow_indices = create_circle([0, 0, 0], 0.05, [0.2, 0.2, 0.2], points=30)
    shadow_vao, shadow_count = create_object(shadow_vertices, shadow_indices)
    while running:
        dt = clock.tick(60) / 1000.0
        running = wm.process_events(lambda event: None)
        keyboard = pygame.key.get_pressed()

        if not game_over:
            movement_speed = speed * (0.5 if is_jumping else 1)
            if keyboard[pygame.K_a]:
                player_pos[0] -= movement_speed * dt
            if keyboard[pygame.K_d]:
                player_pos[0] += movement_speed * dt
            if keyboard[pygame.K_w]:
                player_pos[1] += movement_speed * dt
            if keyboard[pygame.K_s]:
                player_pos[1] -= movement_speed * dt

            if keyboard[pygame.K_SPACE] and not is_jumping:
                is_jumping = True
                jump_time = 0
            if is_jumping:
                jump_time += 1
                t = jump_time / jump_duration
                jump_offset = jump_height * 4 * t * (1 - t)
                if jump_time >= jump_duration:
                    is_jumping = False
            else:
                jump_offset = 0

            if health_cooldown > 0:
                health_cooldown -= dt
                blink_timer += dt
                if blink_timer >= blink_interval:
                    player_visible = not player_visible
                    blink_timer = 0
            else:
                player_visible = True

            player_pos[0] = max(-1.0, min(1.0, player_pos[0]))
            player_pos[1] = max(-1.0, min(1.0, player_pos[1]))
            effective_y = player_pos[1] + jump_offset

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

            if -0.7 <= player_pos[0] <= 0.7:
                on_lily_pad = False
                for lp in lily_pads:
                    distance = np.sqrt((player_pos[0] - lp.pos[0])**2 + (effective_y - lp.pos[1]*2)**2)
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

            if player_pos[0] > 0.7:
                all_keys_collected = all(key['collected'] for key in keys)
                if all_keys_collected:
                    running = False  
                    with open("checkpoint.txt", "w") as file:
                        file.write("")# Win condition reached.
                else:
                    player_pos[0] = min(0.75, player_pos[0])

            for lp in lily_pads:
                lp.update(dt)
        else:
            game_over_timer += dt
            if keyboard[pygame.K_RETURN] or game_over_timer > 3.0:
                running = False

        glViewport(0, 0, width, height)
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
                
        shadow_scale = max(0.3, 1.0 - jump_offset/jump_height)
        shadow_model = np.array([
            [shadow_scale, 0, 0, player_pos[0]],
            [0, shadow_scale, 0, player_pos[1] - 0.01],  # Slightly below player
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
            glBindVertexArray(player_vao)
            glDrawElements(GL_TRIANGLES, player_count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
        
        glUseProgram(0)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        hud_text = f"Lives: {'♥'*lives}"
        draw_text(hud_text, hud_font, 20, height - 40)
        
        health_bar_width = 200
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(20, height - 50)
        glVertex2f(20, height - 70)
        glVertex2f(20 + health_bar_width, height - 70)
        glVertex2f(20 + health_bar_width, height - 50)
        glEnd()
        
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_QUADS)
        glVertex2f(20, height - 50)
        glVertex2f(20, height - 70)
        glVertex2f(20 + health_bar_width * (health / 100), height - 70)
        glVertex2f(20 + health_bar_width * (health / 100), height - 50)
        glEnd()
        
        key_text = f"Keys: {sum(key['collected'] for key in keys)}/3"
        draw_text(key_text, hud_font, 20, height - 100)
        
        if not game_over and sum(key['collected'] for key in keys) < 3:
            prompt = "Collect all the keys to complete biome"
            prompt_width, _ = hud_font.size(prompt)
            draw_text(prompt, hud_font, (width - prompt_width) / 2, 20)
        
        if game_over:
            over_msg = "Game Over"
            over_width, _ = hud_font.size(over_msg)
            draw_text(over_msg, hud_font, (width - over_width) / 2, height / 2)
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        wm.swap_buffers()
    
    # --- Clean the checkpoint on game over ---
    if game_over:
        with open("checkpoint.txt", "w") as file:
            file.write("")
    
    wm.quit()
    pygame.font.quit()
    sys.exit()

if __name__ == "__main__":
    main()
