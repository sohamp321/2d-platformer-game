import sys
import pygame
import numpy as np
import math
import ctypes
import random
import json
import os
from OpenGL.GL import *
from pygame.locals import DOUBLEBUF, OPENGL, QUIT, KEYDOWN, K_SPACE

from src.end_screen import display_end_screen
from src.game_launcher import start_game  # Avoid circular imports

# Initialize pygame and the font module.
pygame.init()
hud_font = pygame.font.SysFont("Segoe UI Symbol", 24)

# Import helper modules.
from utils.window_manager import WindowManager
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_circle, create_object

# --- Checkpoint Functions ---
CHECKPOINT_FILE = "saves/upside_down_checkpoint.json"

def save_checkpoint(state):
    if state is None:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        print("Checkpoint cleared.")
        return
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(state, f)
    print("Checkpoint saved.")

def load_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        print("No checkpoint found.")
        return None
    with open(CHECKPOINT_FILE, "r") as f:
        state = json.load(f)
    print("Checkpoint loaded.")
    return state

# --- Utility Functions ---
def draw_text(text, font_obj, pos_x, pos_y, color=(255,255,255)):
    text_surface = font_obj.render(text, True, color).convert_alpha()
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

def translation_matrix(x, y, z):
    return np.array([[1,0,0,x],
                     [0,1,0,y],
                     [0,0,1,z],
                     [0,0,0,1]], dtype=np.float32)

# --- Classes for Game Assets ---
class Platform:
    def __init__(self, x, y, width, height, speed, lower_bound, upper_bound, model_loc):
        self.x = x; self.y = y; self.width = width; self.height = height
        self.speed = speed; self.direction = 1
        self.lower_bound = lower_bound; self.upper_bound = upper_bound
        vertices, indices = create_rect(-width/2, 0, width, height, [0.0, 1.0, 0.0])
        self.vao, self.count = create_object(vertices.flatten().astype(np.float32), indices)
        self.model_loc = model_loc
    def update(self, dt):
        self.y += self.speed * self.direction * dt
        if self.y > self.upper_bound or self.y < self.lower_bound:
            self.direction *= -1
    def draw(self):
        model = translation_matrix(self.x, self.y, 0)
        glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

class WinningPlatform(Platform):
    def __init__(self, x, y, width, height, speed, lower_bound, upper_bound, model_loc):
        super().__init__(x, y, width, height, speed, lower_bound, upper_bound, model_loc)
        vertices, indices = create_rect(-width/2, 0, width, height, [1.0, 0.84, 0.0])
        self.vao, self.count = create_object(vertices.flatten().astype(np.float32), indices)
    def draw(self):
        model = translation_matrix(self.x, self.y, 0)
        glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

class EvilPlatform(Platform):
    def __init__(self, x, y, width, height, speed, lower_bound, upper_bound, model_loc, flip_spike=False):
        super().__init__(x, y, width, height, speed, lower_bound, upper_bound, model_loc)
        vertices, indices = create_rect(-width/2, 0, width, height, [1.0, 0.0, 0.0])
        self.vao, self.count = create_object(vertices.flatten().astype(np.float32), indices)
        self.spikes = []
        n_spikes = 3
        spike_height = 0.05
        spike_base = width / (n_spikes * 1.5)
        for i in range(n_spikes):
            spike_center_x = -width/2 + (i+1)*width/(n_spikes+1)
            if not flip_spike:
                v1 = [spike_center_x - spike_base/2, self.height, 0]
                v2 = [spike_center_x + spike_base/2, self.height, 0]
                v3 = [spike_center_x, self.height + spike_height, 0]
            else:
                v1 = [spike_center_x - spike_base/2, 0, 0]
                v2 = [spike_center_x + spike_base/2, 0, 0]
                v3 = [spike_center_x, -spike_height, 0]
            spike_color = [1.0, 1.0, 1.0]
            spike_vertices = [v1[0], v1[1], v1[2], *spike_color,
                              v2[0], v2[1], v2[2], *spike_color,
                              v3[0], v3[1], v3[2], *spike_color]
            spike_vertices = np.array(spike_vertices, dtype=np.float32)
            spike_indices = np.array([0,1,2], dtype=np.uint32)
            vao_spike = glGenVertexArrays(1)
            glBindVertexArray(vao_spike)
            vbo_spike = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo_spike)
            glBufferData(GL_ARRAY_BUFFER, spike_vertices.nbytes, spike_vertices, GL_STATIC_DRAW)
            stride = 6 * ctypes.sizeof(ctypes.c_float)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * ctypes.sizeof(ctypes.c_float)))
            glEnableVertexAttribArray(1)
            ebo_spike = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo_spike)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, spike_indices.nbytes, spike_indices, GL_STATIC_DRAW)
            glBindVertexArray(0)
            self.spikes.append((vao_spike, len(spike_indices)))
        self.flip_spike = flip_spike
    def draw(self):
        model = translation_matrix(self.x, self.y, 0)
        glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        for spike_vao, spike_count in self.spikes:
            glBindVertexArray(spike_vao)
            glDrawElements(GL_TRIANGLES, spike_count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

class Key:
    def __init__(self, platform):
        self.platform = platform
        self.collected = False
        self.size = 0.05
        if platform.y < 0:
            self.offset = np.array([0, platform.height+0.03, 0])
        else:
            self.offset = np.array([0, -0.03, 0])
        vertices, indices = create_rect(-self.size/2, -self.size/2, self.size, self.size, [1.0, 1.0, 0.0])
        self.vao, self.count = create_object(vertices.flatten().astype(np.float32), indices)
    def draw(self, model_loc):
        if self.collected:
            return
        key_x = self.platform.x + self.offset[0]
        key_y = self.platform.y + self.offset[1]
        model = translation_matrix(key_x, key_y, 0)
        glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

class Arrow:
    def __init__(self, x, y, width, height, vx):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.vx = vx
        vertices = [
            -width/2,  height/2, 0.0, 1.0, 1.0, 1.0,
            -width/2, -height/2, 0.0, 1.0, 1.0, 1.0,
             width/2,  0.0,      0.0, 1.0, 1.0, 1.0
        ]
        indices = [0, 1, 2]
        vertices = np.array(vertices, dtype=np.float32)
        indices = np.array(indices, dtype=np.uint32)
        self.vao, self.count = create_object(vertices, indices)
    def update(self, dt):
        self.x += self.vx * dt
    def draw(self, model_loc):
        if self.vx < 0:
            scale_matrix = np.array([
                [-1,0,0,0],
                [0,1,0,0],
                [0,0,1,0],
                [0,0,0,1]
            ], dtype=np.float32)
            model = translation_matrix(self.x, self.y, 0) @ scale_matrix
        else:
            model = translation_matrix(self.x, self.y, 0)
        glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

class Player:
    def __init__(self, x, y, diameter, model_loc):
        self.x = x
        self.y = y
        self.diameter = diameter
        self.spawn_x = x
        self.spawn_y = y
        self.vy = 0.0
        self.gravity = 1.0
        self.gravity_direction = -1
        self.jump_strength = 0.75
        self.max_jumps = 2
        self.jumps_remaining = self.max_jumps
        self.on_ground = False
        self.lives = 3
        self.health = 100
        self.max_health = 100
        self.damage_cooldown = 0.0
        self.won = False
        vertices, indices = create_circle([0,0,0], diameter/2, [1.0, 0.0, 0.0], points=30)
        self.vao, self.count = create_object(vertices, indices)
        self.model_loc = model_loc
    def take_damage(self, amount):
        if self.damage_cooldown > 0:
            return
        self.health -= amount
        if self.health <= 0:
            self.lives -= 1
            self.health = self.max_health
            self.respawn()
        self.damage_cooldown = 1.0
    def respawn(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vy = 0
        self.jumps_remaining = self.max_jumps
        print("Respawning... Lives left:", self.lives)
    def update(self, dt, platforms, all_keys_collected):
        if not self.on_ground:
            self.vy += (self.gravity * self.gravity_direction)*dt
        self.y += self.vy*dt
        self.on_ground = False
        for plat in platforms:
            plat_left = plat.x - plat.width/2
            plat_right = plat.x + plat.width/2
            if self.x + self.diameter/2 >= plat_left and self.x - self.diameter/2 <= plat_right:
                if isinstance(plat, WinningPlatform):
                    if self.gravity_direction == -1:
                        player_bottom = self.y - self.diameter/2
                        plat_top = plat.y + plat.height
                        if abs(player_bottom - plat_top) < 0.02 and self.vy <= 0:
                            if all_keys_collected:
                                print("You win!")
                                self.won = True
                                return
                            else:
                                self.y = plat_top + self.diameter/2
                                self.vy = 0
                                self.on_ground = True
                                self.jumps_remaining = self.max_jumps
                    else:
                        player_top = self.y + self.diameter/2
                        plat_bottom = plat.y
                        if abs(player_top - plat_bottom) < 0.02 and self.vy >= 0:
                            if all_keys_collected:
                                print("You win!")
                                self.won = True
                                return
                            else:
                                self.y = plat_bottom - self.diameter/2
                                self.vy = 0
                                self.on_ground = True
                                self.jumps_remaining = self.max_jumps
                elif isinstance(plat, EvilPlatform):
                    if self.gravity_direction == -1:
                        player_bottom = self.y - self.diameter/2
                        plat_top = plat.y + plat.height
                        if abs(player_bottom - plat_top) < 0.02 and self.vy <= 0:
                            self.lives -= 1
                            print("Ouch! Landed on spikes. Lives left:", self.lives)
                            self.respawn()
                            return
                    else:
                        player_top = self.y + self.diameter/2
                        plat_bottom = plat.y
                        if abs(player_top - plat_bottom) < 0.02 and self.vy >= 0:
                            self.lives -= 1
                            print("Ouch! Landed on spikes. Lives left:", self.lives)
                            self.respawn()
                            return
                else:
                    if self.gravity_direction == -1:
                        player_bottom = self.y - self.diameter/2
                        plat_top = plat.y + plat.height
                        if abs(player_bottom - plat_top) < 0.02 and self.vy <= 0:
                            self.y = plat_top + self.diameter/2
                            self.vy = 0
                            self.on_ground = True
                            self.jumps_remaining = self.max_jumps
                    else:
                        player_top = self.y + self.diameter/2
                        plat_bottom = plat.y
                        if abs(player_top - plat_bottom) < 0.02 and self.vy >= 0:
                            self.y = plat_bottom - self.diameter/2
                            self.vy = 0
                            self.on_ground = True
                            self.jumps_remaining = self.max_jumps
        if self.gravity_direction == -1 and self.y - self.diameter/2 < -1:
            self.y = -1 + self.diameter/2
            self.vy = 0
            self.on_ground = True
            self.jumps_remaining = self.max_jumps
        elif self.gravity_direction == 1 and self.y + self.diameter/2 > 1:
            self.y = 1 - self.diameter/2
            self.vy = 0
            self.on_ground = True
            self.jumps_remaining = self.max_jumps
        if self.damage_cooldown > 0:
            self.damage_cooldown -= dt
            if self.damage_cooldown < 0:
                self.damage_cooldown = 0
    def jump(self):
        if self.jumps_remaining > 0:
            self.vy = self.jump_strength * (-self.gravity_direction)
            self.jumps_remaining -= 1
            self.on_ground = False
    def flip_gravity(self):
        self.gravity_direction *= -1
        self.vy = 0
    def draw(self):
        if self.damage_cooldown > 0:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                return
        model = translation_matrix(self.x, self.y, 0)
        glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

# --- Game State Initialization ---
def initialize_game_state(state_data, model_loc):
    if state_data:
        p_data = state_data.get("player", {})
        player = Player(p_data.get("x", 0), p_data.get("y", 0), 0.1, model_loc)
        player.lives = p_data.get("lives", 3)
        player.health = p_data.get("health", 100)
    else:
        player = Player(0, 0, 0.1, model_loc)
    platforms = []
    keys = []
    x_positions = [-0.8, -0.4, 0.0, 0.4, 0.8]
    if not state_data:
        for i, x in enumerate(x_positions):
            if i == len(x_positions)-1:
                p = WinningPlatform(x, -1.0, 0.4, 0.05, random.uniform(0.1,0.2), -1.0, -0.85, model_loc)
            elif i % 2 == 0:
                p = Platform(x, -1.0, 0.4, 0.05, random.uniform(0.1,0.2), -1.0, -0.85, model_loc)
            else:
                p = EvilPlatform(x, -1.0, 0.4, 0.05, random.uniform(0.2,0.4), -1.0, -0.75, model_loc, flip_spike=False)
            platforms.append(p)
        for i, x in enumerate(x_positions):
            if i % 2 == 0:
                p = Platform(x, 0.85, 0.4, 0.05, random.uniform(0.1,0.2), 0.85, 0.95, model_loc)
            else:
                p = EvilPlatform(x, 0.85, 0.4, 0.05, random.uniform(0.2,0.4), 0.75, 0.95, model_loc, flip_spike=True)
            platforms.append(p)
        candidate_indices = [i for i, p in enumerate(platforms) if not isinstance(p, EvilPlatform) and not isinstance(p, WinningPlatform)]
        key_indices = random.sample(candidate_indices, 3)
        for idx in key_indices:
            keys.append(Key(platforms[idx]))
    else:
        for plat_data in state_data.get("platforms", []):
            plat_type = plat_data.get("type", "Platform")
            x = plat_data.get("x", 0)
            y = plat_data.get("y", 0)
            speed = plat_data.get("speed", 0.1)
            lower_bound = plat_data.get("lower_bound", -1.0)
            upper_bound = plat_data.get("upper_bound", -0.85)
            if plat_type == "WinningPlatform":
                p = WinningPlatform(x, y, 0.4, 0.05, speed, lower_bound, upper_bound, model_loc)
            elif plat_type == "EvilPlatform":
                p = EvilPlatform(x, y, 0.4, 0.05, speed, lower_bound, plat_data.get("upper_bound", -0.75), model_loc, flip_spike=plat_data.get("flip_spike", False))
            else:
                p = Platform(x, y, 0.4, 0.05, speed, lower_bound, upper_bound, model_loc)
            platforms.append(p)
        for key_data in state_data.get("keys", []):
            plat_idx = key_data.get("platform_index", 0)
            k = Key(platforms[plat_idx])
            k.collected = key_data.get("collected", False)
            keys.append(k)
    return {"player": player, "platforms": platforms, "keys": keys}

# --- Game Loop Function with Integrated Pause Menu ---
def run_game_loop(wm, assets, model_loc, shader):
    player = assets["player"]
    platforms = assets["platforms"]
    keys = assets["keys"]
    arrows = []
    clock = pygame.time.Clock()
    running = True
    game_result = None  # "win" or "lose"

    # Pause menu variables.
    paused = False
    pause_options = ["New Game", "Load Game", "Select Biome", "Exit"]
    pause_selected = 0

    while running:
        dt = clock.tick(60) / 1000.0
        
        # Process events.
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
                game_result = None
            elif event.type == KEYDOWN:
                if paused:
                    # When paused, process menu navigation.
                    if event.key == pygame.K_ESCAPE:
                        paused = False  # Resume game
                    elif event.key == pygame.K_UP:
                        pause_selected = (pause_selected - 1) % len(pause_options)
                    elif event.key == pygame.K_DOWN:
                        pause_selected = (pause_selected + 1) % len(pause_options)
                    elif event.key == pygame.K_RETURN:
                        option = pause_options[pause_selected]
                        if option == "New Game":
                            new_game(wm)
                        elif option == "Load Game":
                            load_game(wm)
                        elif option == "Select Biome":
                            start_game(wm)
                        elif option == "Exit":
                            wm.quit()
                            pygame.quit()
                            sys.exit()
                else:
                    if event.key == pygame.K_ESCAPE:
                        paused = True
                    elif event.key == K_SPACE:
                        player.flip_gravity()
        
        # When not paused, process continuous key presses and update game objects.
        if not paused:
            keys_pressed = pygame.key.get_pressed()
            move_speed = 0.5
            if keys_pressed[pygame.K_a]:
                player.x -= move_speed * dt
            if keys_pressed[pygame.K_d]:
                player.x += move_speed * dt
            if player.x - player.diameter/2 < -1:
                player.x = -1 + player.diameter/2
            if player.x + player.diameter/2 > 1:
                player.x = 1 - player.diameter/2

            if random.random() < 0.02:
                if random.choice([True, False]):
                    x_arrow = -1.1
                    vx = random.uniform(0.3, 0.6)
                else:
                    x_arrow = 1.1
                    vx = -random.uniform(0.3, 0.6)
                y_arrow = random.uniform(-0.8, 0.8)
                arrow = Arrow(x_arrow, y_arrow, 0.1, 0.1, vx)
                arrows.append(arrow)
            
            for plat in platforms:
                plat.update(dt)
            for key in keys:
                if not key.collected:
                    key_x = key.platform.x + key.offset[0]
                    key_y = key.platform.y + key.offset[1]
                    dx = player.x - key_x
                    dy = player.y - key_y
                    if math.hypot(dx, dy) < (player.diameter/2 + key.size/2):
                        key.collected = True
                        print("Key collected!")
                        state = {
                            "player": {
                                "x": player.x,
                                "y": player.y,
                                "lives": player.lives,
                                "health": player.health
                            },
                            "platforms": [],
                            "keys": []
                        }
                        for idx, p in enumerate(platforms):
                            p_type = "Platform"
                            if isinstance(p, WinningPlatform):
                                p_type = "WinningPlatform"
                            elif isinstance(p, EvilPlatform):
                                p_type = "EvilPlatform"
                            state["platforms"].append({
                                "type": p_type,
                                "x": p.x,
                                "y": p.y,
                                "speed": p.speed,
                                "lower_bound": p.lower_bound,
                                "upper_bound": p.upper_bound,
                                "flip_spike": getattr(p, "flip_spike", False)
                            })
                        for idx, k in enumerate(keys):
                            state["keys"].append({
                                "platform_index": idx,
                                "collected": k.collected
                            })
                        save_checkpoint(state)
            
            all_keys_collected = all(k.collected for k in keys)
            player.update(dt, platforms, all_keys_collected)
            
            if player.won:
                game_result = "win"
                running = False
            if player.lives <= 0:
                game_result = "lose"
                running = False

            for arrow in arrows[:]:
                arrow.update(dt)
                if arrow.x < -1.2 or arrow.x > 1.2:
                    arrows.remove(arrow)
                else:
                    if (abs(player.x - arrow.x) < (player.diameter/2 + arrow.width/2) and
                        abs(player.y - arrow.y) < (player.diameter/2 + arrow.height/2)):
                        player.take_damage(10)
                        if arrow in arrows:
                            arrows.remove(arrow)
        
        # Rendering.
        glViewport(0, 0, wm.width, wm.height)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        shader.use()
        for plat in platforms:
            plat.draw()
        for key in keys:
            key.draw(model_loc)
        for arrow in arrows:
            arrow.draw(model_loc)
        player.draw()
        glUseProgram(0)
        
        # HUD rendering.
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, wm.width, 0, wm.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        hud_text = f"Lives: {'♥'*player.lives}"
        draw_text(hud_text, hud_font, 20, wm.height-70)
        health_bar_width = 200
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height-80)
        glVertex2f(20, wm.height-100)
        glVertex2f(20+health_bar_width, wm.height-100)
        glVertex2f(20+health_bar_width, wm.height-80)
        glEnd()
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height-80)
        glVertex2f(20, wm.height-100)
        glVertex2f(20+health_bar_width*(player.health/player.max_health), wm.height-100)
        glVertex2f(20+health_bar_width*(player.health/player.max_health), wm.height-80)
        glEnd()
        keys_text = f"Keys: {sum(1 for key in keys if key.collected)}/3"
        draw_text(keys_text, hud_font, 20, wm.height-130)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        # If the game is paused, render the menu overlay on top of the scene.
        if paused:
            # Draw a semi-transparent overlay.
            glViewport(0, 0, wm.width, wm.height)
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, wm.width, 0, wm.height, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glColor4f(0, 0, 0, 0.7)
            glBegin(GL_QUADS)
            glVertex2f(0, 0)
            glVertex2f(wm.width, 0)
            glVertex2f(wm.width, wm.height)
            glVertex2f(0, wm.height)
            glEnd()
            glColor4f(1, 1, 1, 1)
            # Draw the pause menu title.
            draw_text("Paused", hud_font, wm.width//2 - 50, wm.height - 200, (255,255,0))
            # Draw menu options.
            for i, option in enumerate(pause_options):
                color = (255, 255, 255)
                if i == pause_selected:
                    color = (255, 0, 0)
                draw_text(option, hud_font, wm.width//2 - 50, wm.height - 250 - i*30, color)
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
        
        wm.swap_buffers()
        
    # Game result handling.
    if game_result in ("win", "lose"):
        save_checkpoint(None)
        option = display_end_screen(wm, won=(game_result=="win"))
        print("User selected:", option)
        if option == "New Game":
            new_game(wm)
        elif option == "Select Biome":
            start_game(wm)
        else:
            wm.quit()
            pygame.quit()
            sys.exit()
    else:
        wm.quit()
        pygame.quit()
        sys.exit()

# --- Entry Points ---
def new_game(wm):
    vertex_src = """
    #version 330 core
    layout(location = 0) in vec3 aPos;
    layout(location = 1) in vec3 aColor;
    out vec3 vertexColor;
    uniform mat4 model;
    void main(){
         gl_Position = model * vec4(aPos, 1.0);
         vertexColor = aColor;
    }
    """
    fragment_src = """
    #version 330 core
    in vec3 vertexColor;
    out vec4 FragColor;
    void main(){
         FragColor = vec4(vertexColor, 1.0);
    }
    """
    shader = Shader(vertex_src, fragment_src)
    shader.use()
    model_loc = glGetUniformLocation(shader.ID, "model")
    state_data = None
    assets = initialize_game_state(state_data, model_loc)
    run_game_loop(wm, assets, model_loc, shader)

def load_game(wm):
    state_data = load_checkpoint()
    vertex_src = """
    #version 330 core
    layout(location = 0) in vec3 aPos;
    layout(location = 1) in vec3 aColor;
    out vec3 vertexColor;
    uniform mat4 model;
    void main(){
         gl_Position = model * vec4(aPos, 1.0);
         vertexColor = aColor;
    }
    """
    fragment_src = """
    #version 330 core
    in vec3 vertexColor;
    out vec4 FragColor;
    void main(){
         FragColor = vec4(vertexColor, 1.0);
    }
    """
    shader = Shader(vertex_src, fragment_src)
    shader.use()
    model_loc = glGetUniformLocation(shader.ID, "model")
    assets = initialize_game_state(state_data, model_loc)
    run_game_loop(wm, assets, model_loc, shader)

if __name__ == "__main__":
    wm = WindowManager(800,600,"Keys, Arrows & Winning Platform Example")
    new_game(wm)
