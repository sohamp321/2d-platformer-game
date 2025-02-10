import sys
import pygame
import random
from OpenGL.GL import *
import numpy as np
import ctypes
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
    """
    Renders the given text onto a texture using Pygame's font,
    and draws it as a textured quad with its bottom-left corner at (pos_x, pos_y).
    """
    text_surface = font_obj.render(text, True, (255, 255, 255)).convert_alpha()
    text_width, text_height = text_surface.get_size()
    text_data = pygame.image.tostring(text_surface, 'RGBA', True)

    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    # Set unpack alignment to 1 to avoid row alignment issues.
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
        dy = y - self.pos[1]*2
        distance = np.sqrt(dx*dx + dy*dy)
        return distance < (self.radius + 0.05)

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
        self.color = [0.0, 0.0, random.uniform(0.5, 0.9)]
        
    def update(self, dt):
        self.pos[0] += self.speed * dt
        if self.pos[0] + self.width > 0.68:
            self.reset_position()
            
    def collides_with_player(self, player_x, player_y):
        return (self.pos[0] - self.width/2 <= player_x <= self.pos[0] + self.width/2)

# --- Main Function ---
def main():
    # Set up Pygame and create an OpenGL window.
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
    waves = [Wave(-0.65 + i*0.4, random.uniform(0.05, 0.1), [0.0, 0.0, 1.0],
                  random.uniform(0.1, 0.3), 2.5)
             for i in range(2)]

    # Create the player.
    player_pos = [-0.8, 0.0, 0.0]
    player_radius = 0.05
    player_vertices, player_indices = create_circle([0, 0, 0], player_radius, [1.0, 0.5, 0.0], points=30)
    player_vao, player_count = create_object(player_vertices, player_indices)

    speed = 0.8        # Normal movement speed.
    jump_duration = 30 # Frames.
    jump_height = 0.3  # Maximum jump offset.
    jump_time = 0
    is_jumping = False

    clock = pygame.time.Clock()
    lives = 3
    health = 100
    health_cooldown = 0
    blink_interval = 0.05
    blink_timer = 0
    player_visible = True

    # New variables for handling game-over state.
    game_over = False
    game_over_timer = 0.0  # Count how long the game-over message has been displayed.

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        running = wm.process_events(lambda event: None)
        keyboard = pygame.key.get_pressed()

        # --- Update Game State (only if not in game-over) ---
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
                jump_offset = jump_height * 4 * t * (1-t)
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

            # Update waves.
            for wave in waves:
                wave.update(dt)
                if wave.collides_with_player(player_pos[0], effective_y) and health_cooldown <= 0:
                    health -= 5
                    health_cooldown = 0.5
                    if health <= 0:
                        lives -= 1
                        if lives <= 0:
                            game_over = True
                        else:
                            player_pos = [-0.8, 0.0, 0.0]
                            health = 100

            # Check if player is on a lily pad.
            if -0.7 <= player_pos[0] <= 0.7:
                on_lily_pad = False
                for lp in lily_pads:
                    distance = np.sqrt((player_pos[0]-lp.pos[0])**2 + (effective_y-lp.pos[1]*2)**2)
                    if distance < 0.15:
                        on_lily_pad = True
                        for key in keys:
                            if not key['collected'] and key['lily_pad'] == lp:
                                if distance < 0.1:
                                    key['collected'] = True
                        break
                if not on_lily_pad and not is_jumping:
                    lives -= 1
                    if lives <= 0:
                        game_over = True
                    else:
                        player_pos = [-0.8, 0.0, 0.0]

            # Check win condition: if player reaches the right side with all keys.
            if player_pos[0] > 0.7:
                all_keys_collected = all(key['collected'] for key in keys)
                if all_keys_collected:
                    # Win condition: exit game (or you could display a win message)
                    running = False
                else:
                    player_pos[0] = min(0.75, player_pos[0])

            for lp in lily_pads:
                lp.update(dt)
        else:
            # When game_over is True, count the time before quitting.
            game_over_timer += dt
            # Optionally, allow the player to press Enter to exit immediately.
            if keyboard[pygame.K_RETURN] or game_over_timer > 3.0:
                running = False

        # --- Render the 3D Scene ---
        glViewport(0, 0, width, height)
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        
        shader_program.use()
        identity = np.eye(4, dtype=np.float32)
        glUniformMatrix4fv(modelLoc, 1, GL_TRUE, identity)

        # Draw background objects.
        glBindVertexArray(left_grass_vao)
        glDrawElements(GL_TRIANGLES, left_grass_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        glBindVertexArray(river_vao)
        glDrawElements(GL_TRIANGLES, river_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        glBindVertexArray(right_grass_vao)
        glDrawElements(GL_TRIANGLES, right_grass_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        # Draw waves.
        for wave in waves:
            wave_model = translation_matrix(wave.pos[0], wave.pos[1], wave.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, wave_model)
            glBindVertexArray(wave.vao)
            glDrawElements(GL_TRIANGLES, wave.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

        # Draw lily pads.
        for lp in lily_pads:
            model = translation_matrix(lp.pos[0], lp.pos[1], lp.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(lp.vao)
            glDrawElements(GL_TRIANGLES, lp.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

        # Draw keys.
        for key in keys:
            if not key.get('collected', False):
                key_pos = key['lily_pad'].pos
                key_model = translation_matrix(key_pos[0], key_pos[1]*2, key_pos[2])
                glUniformMatrix4fv(modelLoc, 1, GL_TRUE, key_model)
                glBindVertexArray(key['vao'])
                glDrawElements(GL_TRIANGLES, key['count'], GL_UNSIGNED_INT, None)
                glBindVertexArray(0)

        # Draw the player.
        if player_visible:
            model = translation_matrix(player_pos[0], effective_y, player_pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(player_vao)
            glDrawElements(GL_TRIANGLES, player_count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

        # --- Render HUD Text and Additional Messages ---
        # Switch to fixed-function pipeline with an orthographic projection.
        glUseProgram(0)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, width, 0, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Draw HUD elements.
        hud_text = f"Lives: {'♥'*lives}"
        draw_text(hud_text, hud_font, 20, height - 40)

        # Draw health bar.
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

        # If the game is not over and not all keys have been collected, show the prompt.
        if not game_over and sum(key['collected'] for key in keys) < 3:
            prompt = "Collect all the keys to complete biome"
            prompt_width, prompt_height = hud_font.size(prompt)
            draw_text(prompt, hud_font, (width - prompt_width) / 2, 20)
        
        # If the game is over, display "Game Over" in the center.
        if game_over:
            over_msg = "Game Over"
            over_width, over_height = hud_font.size(over_msg)
            draw_text(over_msg, hud_font, (width - over_width) / 2, height / 2)

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        wm.swap_buffers()

    wm.quit()
    pygame.font.quit()
    sys.exit()

if __name__ == "__main__":
    main()
