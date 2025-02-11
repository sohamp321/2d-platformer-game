import sys
import os
import pygame
import numpy as np
import math
import ctypes
import random
import json
from OpenGL.GL import *
from pygame.locals import DOUBLEBUF, OPENGL, QUIT

# Import your helper modules:
from utils.window_manager import WindowManager
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_circle, create_object

# --- HUD Text Function ---
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

def load_game(wm):
    """
    This function loads a saved checkpoint and starts the game using the saved state.
    It loads:
      - Player lives and health,
      - Each platform's width and speed,
      - And which platform has a key (and its collected status).
    If no checkpoint is found, the game starts with default state.
    Press F5 to save a checkpoint and F9 to reload during the game.
    """
    # --- Helper Function ---
    def translation_matrix(x, y, z):
        return np.array([
            [1, 0, 0, x],
            [0, 1, 0, y],
            [0, 0, 1, z],
            [0, 0, 0, 1]
        ], dtype=np.float32)

    def load_shader_source(filepath):
        with open(filepath, 'r') as f:
            return f.read()

    # --- Load Background Image ---
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

    # --- Create Shader Program ---
    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")
    shader = Shader(vertex_shader_source, fragment_shader_source)
    shader.use()
    model_loc = glGetUniformLocation(shader.ID, "model")

    # --- Save & Load Checkpoint Functions ---
    def save_checkpoint(player, platforms, keys):
        data = {}
        data["player"] = {"lives": player.lives, "health": player.health}
        data["platforms"] = []
        for plat in platforms:
            if isinstance(plat, WinningPlatform):
                ptype = "winning"
            elif isinstance(plat, EvilPlatform):
                ptype = "evil"
            else:
                ptype = "normal"
            data["platforms"].append({"type": ptype, "width": plat.width, "speed": plat.speed})
        data["keys"] = []
        for key in keys:
            try:
                index = platforms.index(key.platform)
            except ValueError:
                index = -1
            data["keys"].append({"platform_index": index, "collected": key.collected})
        with open("saves/space_checkpoint.json", "w") as f:
            json.dump(data, f)
        print("Checkpoint saved.")

    def load_checkpoint():
        with open("saves/space_checkpoint.json", "r") as f:
            return json.load(f)

    # --- Platform Classes ---
    class Platform:
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound, model_loc):
            self.x = x; self.y = y; self.width = width; self.height = height
            self.speed = speed; self.direction = 1
            self.lower_bound = lower_bound; self.upper_bound = upper_bound
            vertices, indices = create_rect(-width/2, 0, width, height, [0.0, 1.0, 0.0])
            self.vao, self.count = create_object(vertices, indices)
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

    class EvilPlatform(Platform):
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound, model_loc):
            super().__init__(x, y, width, height, speed, lower_bound, upper_bound, model_loc)
            vertices, indices = create_rect(-width/2, 0, width, height, [1.0, 0.0, 0.0])
            self.vao, self.count = create_object(vertices, indices)
            self.spikes = []
            n_spikes = 3; spike_height = 0.05; spike_base = width / (n_spikes * 1.5)
            for i in range(n_spikes):
                spike_center_x = -width/2 + (i+1) * width/(n_spikes+1)
                v1 = [spike_center_x - spike_base/2, self.height, 0]
                v2 = [spike_center_x + spike_base/2, self.height, 0]
                v3 = [spike_center_x, self.height + spike_height, 0]
                spike_color = [1.0, 1.0, 1.0]
                spike_vertices = [
                    v1[0], v1[1], v1[2], *spike_color,
                    v2[0], v2[1], v2[2], *spike_color,
                    v3[0], v3[1], v3[2], *spike_color,
                ]
                spike_vertices = np.array(spike_vertices, dtype=np.float32)
                spike_indices = np.array([0, 1, 2], dtype=np.uint32)
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

    class WinningPlatform(Platform):
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound, model_loc):
            super().__init__(x, y, width, height, speed, lower_bound, upper_bound, model_loc)
            vertices, indices = create_rect(-width/2, 0, width, height, [0.0, 0.0, 1.0])
            self.vao, self.count = create_object(vertices, indices)

    # --- Key Class ---
    class Key:
        def __init__(self, platform, model_loc):
            self.platform = platform
            self.collected = False
            self.offset_x = 0
            self.offset_y = platform.height + 0.02
            self.size = 0.04
            vertices, indices = create_rect(-self.size/2, -self.size/2, self.size, self.size, [1.0, 1.0, 0.0])
            self.vao, self.count = create_object(vertices, indices)
            self.model_loc = model_loc
        def draw(self):
            if self.collected:
                return
            key_x = self.platform.x + self.offset_x
            key_y = self.platform.y + self.offset_y
            model = translation_matrix(key_x, key_y, 0)
            glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Player Class ---
    class Player:
        def __init__(self, x, y, diameter, model_loc):
            self.x = x
            self.y = y
            self.diameter = diameter
            self.spawn_x = x
            self.spawn_y = y
            self.vy = 0.0
            self.gravity = -1.0
            self.jump_strength = 0.75
            self.max_jumps = 2
            self.jumps_remaining = self.max_jumps
            self.on_ground = False
            self.lives = 3
            self.health = 100
            self.max_health = 100
            self.damage_cooldown = 0.0
            vertices, indices = create_circle([0, 0, 0], diameter/2, [1.0, 0.0, 0.0], points=30)
            self.vao, self.count = create_object(vertices, indices)
            self.model_loc = model_loc
        def update(self, dt, platforms):
            if not self.on_ground:
                self.vy += self.gravity * dt
            self.y += self.vy * dt
            self.on_ground = False
            player_bottom = self.y - self.diameter/2
            for plat in platforms:
                plat_left = plat.x - plat.width/2
                plat_right = plat.x + plat.width/2
                plat_top = plat.y + plat.height
                if (self.x + self.diameter/2 >= plat_left and self.x - self.diameter/2 <= plat_right):
                    if isinstance(plat, EvilPlatform):
                        if abs(player_bottom - plat_top) < 0.02 and self.vy <= 0:
                            self.lives -= 1
                            if self.lives > 0:
                                self.respawn()
                            return
                    else:
                        if abs(player_bottom - plat_top) < 0.02 and self.vy <= 0:
                            self.y = plat_top + self.diameter/2
                            self.vy = 0
                            self.on_ground = True
                            self.jumps_remaining = self.max_jumps
            if self.y - self.diameter/2 < -1:
                self.y = -1 + self.diameter/2
                self.vy = 0
                self.on_ground = True
                self.jumps_remaining = self.max_jumps
            if self.damage_cooldown > 0:
                self.damage_cooldown -= dt
                if self.damage_cooldown < 0:
                    self.damage_cooldown = 0
        def jump(self):
            if self.jumps_remaining > 0:
                self.vy = self.jump_strength
                self.jumps_remaining -= 1
                self.on_ground = False
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
        def draw(self):
            if self.damage_cooldown > 0:
                if (pygame.time.get_ticks() // 100) % 2 == 0:
                    return
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Asteroid Class ---
    class Asteroid:
        def __init__(self, x, y, radius, vx, model_loc):
            self.x = x
            self.y = y
            self.radius = radius
            self.vx = vx
            vertices, indices = create_circle([0, 0, 0], radius, [0.5, 0.5, 0.5], points=20)
            self.vao, self.count = create_object(vertices, indices)
            self.model_loc = model_loc
        def update(self, dt):
            self.x += self.vx * dt
        def draw(self):
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(self.model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Create Game Objects (Level Design) ---
    player = Player(0, -0.8, 0.1, model_loc)
    platforms = [
        WinningPlatform(0.8, 0.75, 0.3, 0.05, speed=0.4, lower_bound=0.75, upper_bound=1.0, model_loc=model_loc),
        Platform(-0.8, -0.75, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.8, upper_bound=-0.6, model_loc=model_loc),
        Platform(-0.5, -0.5, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.5, upper_bound=-0.3, model_loc=model_loc),
        Platform(0, -0.2, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.2, upper_bound=0.0, model_loc=model_loc),
        Platform(0.5, 0.1, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=0.1, upper_bound=0.3, model_loc=model_loc),
        Platform(0.7, 0.5, random.uniform(0.2, 0.3), 0.05, random.uniform(0.1, 0.2), lower_bound=0.1, upper_bound=0.6, model_loc=model_loc),
        EvilPlatform(random.uniform(-0.8, -0.5), 0, 0.3, 0.05, random.uniform(0.2, 0.4), lower_bound=-0.5, upper_bound=0.2, model_loc=model_loc),
        EvilPlatform(0.3, 0.5, 0.3, 0.05, random.uniform(0.2, 0.4), lower_bound=-0.5, upper_bound=0.7, model_loc=model_loc)
    ]
    # --- Key System: Randomly assign keys to 3 normal platforms ---
    normal_platforms = [p for p in platforms if type(p) == Platform]
    selected_platforms = random.sample(normal_platforms, 3)
    keys = []
    for p in selected_platforms:
        keys.append(Key(p, model_loc))
    asteroids = []
    asteroid_spawn_timer = 0

    hud_font = pygame.font.SysFont("Arial", 24)

    # --- Checkpoint Functions ---
    def save_checkpoint(player, platforms, keys):
        data = {}
        data["player"] = {"lives": player.lives, "health": player.health}
        data["platforms"] = []
        for plat in platforms:
            if isinstance(plat, WinningPlatform):
                ptype = "winning"
            elif isinstance(plat, EvilPlatform):
                ptype = "evil"
            else:
                ptype = "normal"
            data["platforms"].append({"type": ptype, "width": plat.width, "speed": plat.speed})
        data["keys"] = []
        for key in keys:
            try:
                index = platforms.index(key.platform)
            except ValueError:
                index = -1
            data["keys"].append({"platform_index": index, "collected": key.collected})
        with open("saves/space_checkpoint.json", "w") as f:
            json.dump(data, f)
        print("Checkpoint saved.")

    def load_checkpoint():
        with open("saves/space_checkpoint.json", "r") as f:
            return json.load(f)

    clock = pygame.time.Clock()
    running = True
    game_won = False

    # --- Load Checkpoint at Start ---
    try:
        data = load_checkpoint()
        player.lives = data["player"]["lives"]
        player.health = data["player"]["health"]
        for i, plat in enumerate(platforms):
            plat.width = data["platforms"][i]["width"]
            plat.speed = data["platforms"][i]["speed"]
        for i, key in enumerate(keys):
            key.collected = data["keys"][i]["collected"]
        print("Checkpoint loaded.")
    except Exception as e:
        print("No checkpoint found; starting new game.", e)

    # --- Main Game Loop ---
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()
                elif event.key == pygame.K_F5:
                    save_checkpoint(player, platforms, keys)
                elif event.key == pygame.K_F9:
                    try:
                        data = load_checkpoint()
                        player.lives = data["player"]["lives"]
                        player.health = data["player"]["health"]
                        for i, plat in enumerate(platforms):
                            plat.width = data["platforms"][i]["width"]
                            plat.speed = data["platforms"][i]["speed"]
                        for i, key in enumerate(keys):
                            key.collected = data["keys"][i]["collected"]
                        print("Checkpoint loaded.")
                    except Exception as e:
                        print("Error loading checkpoint:", e)

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

        player.update(dt, platforms)
        for plat in platforms:
            plat.update(dt)
        for key in keys:
            if not key.collected:
                key_center_x = key.platform.x + key.offset_x
                key_center_y = key.platform.y + key.offset_y
                dx = player.x - key_center_x
                dy = player.y - key_center_y
                if math.sqrt(dx*dx + dy*dy) < (player.diameter/2 + key.size/2):
                    key.collected = True
                    save_checkpoint(player, platforms, keys)
        asteroid_spawn_timer -= dt
        if asteroid_spawn_timer <= 0:
            spawn_y = random.uniform(-0.9, 0.9)
            spawn_x = 1.1
            radius = random.uniform(0.03, 0.07)
            vx = -random.uniform(0.1, 0.3)
            asteroids.append(Asteroid(spawn_x, spawn_y, radius, vx, model_loc))
            asteroid_spawn_timer = random.uniform(1.0, 3.0)
        for asteroid in asteroids[:]:
            asteroid.update(dt)
            if asteroid.x + asteroid.radius < -1:
                asteroids.remove(asteroid)
            else:
                dx = player.x - asteroid.x
                dy = player.y - asteroid.y
                if math.sqrt(dx*dx + dy*dy) < (player.diameter/2 + asteroid.radius):
                    player.take_damage(10)
                    if asteroid in asteroids:
                        asteroids.remove(asteroid)
        all_keys_collected = all(key.collected for key in keys)
        for plat in platforms:
            if isinstance(plat, WinningPlatform) and all_keys_collected:
                plat_left = plat.x - plat.width/2
                plat_right = plat.x + plat.width/2
                plat_top = plat.y + plat.height
                if (player.x + player.diameter/2 >= plat_left and
                    player.x - player.diameter/2 <= plat_right):
                    if abs((player.y - player.diameter/2) - plat_top) < 0.02:
                        if (player.y + player.diameter/2) >= 1.0:
                            game_won = True

        # --- Draw Background ---
        glUseProgram(0)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, wm.width, 0, wm.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, bg_texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(wm.width, 0)
        glTexCoord2f(1, 1); glVertex2f(wm.width, wm.height)
        glTexCoord2f(0, 1); glVertex2f(0, wm.height)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        # --- Draw Game World ---
        glViewport(0, 0, wm.width, wm.height)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        shader.use()
        for plat in platforms:
            plat.draw()
        for asteroid in asteroids:
            asteroid.draw()
        for key in keys:
            key.draw()
        player.draw()
        # --- Draw HUD Overlay ---
        glUseProgram(0)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, wm.width, 0, wm.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        hud_text = f"Lives: {'♥'*player.lives}"
        draw_text(hud_text, hud_font, 20, wm.height - 40)
        health_bar_width = 200
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height - 50)
        glVertex2f(20, wm.height - 70)
        glVertex2f(20 + health_bar_width, wm.height - 70)
        glVertex2f(20 + health_bar_width, wm.height - 50)
        glEnd()
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height - 50)
        glVertex2f(20, wm.height - 70)
        glVertex2f(20 + health_bar_width * (player.health / player.max_health), wm.height - 70)
        glVertex2f(20 + health_bar_width * (player.health / player.max_health), wm.height - 50)
        glEnd()
        keys_text = f"Keys: {sum(1 for key in keys if key.collected)}/3"
        draw_text(keys_text, hud_font, 20, wm.height - 100)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        wm.swap_buffers()

        if game_won:
            print("You Win!")
            pygame.time.wait(2000)
            running = False

        if player.lives <= 0:
            print("Game Over!")
            pygame.time.wait(2000)
            running = False

    wm.quit()
    pygame.font.quit()
    pygame.quit()
    sys.exit()


def new_game(wm):
    """
    A space-themed platformer using normalized coordinates.
    Level design:
      - 1 WinningPlatform (blue) on the right.
      - Several normal platforms.
      - 2 EvilPlatforms.
      - Asteroids spawn randomly.
      - 3 keys (yellow squares) are attached to random normal platforms.
    The player starts with 3 lives and 100 health.
    Asteroid collisions reduce health by 10; if health drops to 0, a life is lost.
    After a hit, the player is immune for 1 second (blinks).
    The player wins only if all keys are collected and then they reach the winning platform.
    A background image (from assets/textures/space.jpg) is rendered behind the game.
    Press F5 to save a checkpoint and F9 to load a checkpoint.
    The provided window manager (wm) is used.
    """
    # --- Helper Function ---
    def translation_matrix(x, y, z):
        return np.array([
            [1, 0, 0, x],
            [0, 1, 0, y],
            [0, 0, 1, z],
            [0, 0, 0, 1]
        ], dtype=np.float32)



    def load_shader_source(filepath):
        with open(filepath, 'r') as f:
            return f.read()
        
    
    
    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")


    shader = Shader(vertex_shader_source, fragment_shader_source)
    shader.use()
    model_loc = glGetUniformLocation(shader.ID, "model")

    # --- Save & Load Checkpoint Functions ---
    def save_checkpoint(player, platforms, keys):
        data = {}
        data["player"] = {"lives": player.lives, "health": player.health}
        data["platforms"] = []
        for plat in platforms:
            if isinstance(plat, WinningPlatform):
                ptype = "winning"
            elif isinstance(plat, EvilPlatform):
                ptype = "evil"
            else:
                ptype = "normal"
            data["platforms"].append({"type": ptype, "width": plat.width, "speed": plat.speed})
        data["keys"] = []
        for key in keys:
            try:
                index = platforms.index(key.platform)
            except ValueError:
                index = -1
            data["keys"].append({"platform_index": index, "collected": key.collected})
        with open("saves/space_checkpoint.json", "w") as f:
            json.dump(data, f)
        print("Checkpoint saved.")

    def load_checkpoint():
        with open("saves/space_checkpoint.json", "r") as f:
            return json.load(f)

    # --- Platform Classes ---
    class Platform:
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound):
            self.x = x; self.y = y; self.width = width; self.height = height
            self.speed = speed; self.direction = 1
            self.lower_bound = lower_bound; self.upper_bound = upper_bound
            vertices, indices = create_rect(-width/2, 0, width, height, [0.0, 1.0, 0.0])
            self.vao, self.count = create_object(vertices, indices)
        def update(self, dt):
            self.y += self.speed * self.direction * dt
            if self.y > self.upper_bound or self.y < self.lower_bound:
                self.direction *= -1
        def draw(self):
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    class EvilPlatform(Platform):
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound):
            super().__init__(x, y, width, height, speed, lower_bound, upper_bound)
            vertices, indices = create_rect(-width/2, 0, width, height, [1.0, 0.0, 0.0])
            self.vao, self.count = create_object(vertices, indices)
            self.spikes = []
            n_spikes = 3; spike_height = 0.05; spike_base = width / (n_spikes * 1.5)
            for i in range(n_spikes):
                spike_center_x = -width/2 + (i+1) * width/(n_spikes+1)
                v1 = [spike_center_x - spike_base/2, self.height, 0]
                v2 = [spike_center_x + spike_base/2, self.height, 0]
                v3 = [spike_center_x, self.height + spike_height, 0]
                spike_color = [1.0, 1.0, 1.0]
                spike_vertices = [
                    v1[0], v1[1], v1[2], *spike_color,
                    v2[0], v2[1], v2[2], *spike_color,
                    v3[0], v3[1], v3[2], *spike_color,
                ]
                spike_vertices = np.array(spike_vertices, dtype=np.float32)
                spike_indices = np.array([0, 1, 2], dtype=np.uint32)
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
        def draw(self):
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
            for spike_vao, spike_count in self.spikes:
                glBindVertexArray(spike_vao)
                glDrawElements(GL_TRIANGLES, spike_count, GL_UNSIGNED_INT, None)
                glBindVertexArray(0)

    class WinningPlatform(Platform):
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound):
            super().__init__(x, y, width, height, speed, lower_bound, upper_bound)
            vertices, indices = create_rect(-width/2, 0, width, height, [0.0, 0.0, 1.0])
            self.vao, self.count = create_object(vertices, indices)

    # --- Key Class ---
    class Key:
        def __init__(self, platform):
            self.platform = platform
            self.collected = False
            self.offset_x = 0
            self.offset_y = platform.height + 0.02
            self.size = 0.04
            vertices, indices = create_rect(-self.size/2, -self.size/2, self.size, self.size, [1.0, 1.0, 0.0])
            self.vao, self.count = create_object(vertices, indices)
        def draw(self):
            if self.collected:
                return
            key_x = self.platform.x + self.offset_x
            key_y = self.platform.y + self.offset_y
            model = translation_matrix(key_x, key_y, 0)
            glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Player Class with Lives, Health, Cooldown, and Blinking ---
    class Player:
        def __init__(self, x, y, diameter):
            self.x = x
            self.y = y
            self.diameter = diameter
            self.spawn_x = x
            self.spawn_y = y
            self.vy = 0.0
            self.gravity = -1.0
            self.jump_strength = 0.75
            self.max_jumps = 2
            self.jumps_remaining = self.max_jumps
            self.on_ground = False
            self.lives = 3
            self.health = 100
            self.max_health = 100
            self.damage_cooldown = 0.0
            vertices, indices = create_circle([0, 0, 0], diameter/2, [1.0, 0.0, 0.0], points=30)
            self.vao, self.count = create_object(vertices, indices)
        def update(self, dt, platforms):
            if not self.on_ground:
                self.vy += self.gravity * dt
            self.y += self.vy * dt
            self.on_ground = False
            player_bottom = self.y - self.diameter/2
            for plat in platforms:
                plat_left = plat.x - plat.width/2
                plat_right = plat.x + plat.width/2
                plat_top = plat.y + plat.height
                if (self.x + self.diameter/2 >= plat_left and self.x - self.diameter/2 <= plat_right):
                    if isinstance(plat, EvilPlatform):
                        if abs(player_bottom - plat_top) < 0.02 and self.vy <= 0:
                            self.lives -= 1
                            if self.lives > 0:
                                self.respawn()
                            return
                    else:
                        if abs(player_bottom - plat_top) < 0.02 and self.vy <= 0:
                            self.y = plat_top + self.diameter/2
                            self.vy = 0
                            self.on_ground = True
                            self.jumps_remaining = self.max_jumps
            if self.y - self.diameter/2 < -1:
                self.y = -1 + self.diameter/2
                self.vy = 0
                self.on_ground = True
                self.jumps_remaining = self.max_jumps

        def jump(self):
            if self.jumps_remaining > 0:
                self.vy = self.jump_strength
                self.jumps_remaining -= 1
                self.on_ground = False
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
        def draw(self):
            if self.damage_cooldown > 0:
                if (pygame.time.get_ticks() // 100) % 2 == 0:
                    return
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Asteroid Class ---
    class Asteroid:
        def __init__(self, x, y, radius, vx):
            self.x = x
            self.y = y
            self.radius = radius
            self.vx = vx
            vertices, indices = create_circle([0, 0, 0], radius, [0.5, 0.5, 0.5], points=20)
            self.vao, self.count = create_object(vertices, indices)
        def update(self, dt):
            self.x += self.vx * dt
        def draw(self):
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Create Game Objects (Level Design) ---
    player = Player(0, -0.8, 0.1)
    platforms = [
        WinningPlatform(0.8, 0.75, 0.3, 0.05, speed=0.4, lower_bound=0.75, upper_bound=1.0),
        Platform(-0.8, -0.75, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.8, upper_bound=-0.6),
        Platform(-0.5, -0.5, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.5, upper_bound=-0.3),
        Platform(0, -0.2, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.2, upper_bound=0.0),
        Platform(0.5, 0.1, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=0.1, upper_bound=0.3),
        Platform(0.7, 0.5, random.uniform(0.2, 0.3), 0.05, random.uniform(0.1, 0.2), lower_bound=0.1, upper_bound=0.6),
        EvilPlatform(random.uniform(-0.8, -0.5), 0, 0.3, 0.05, random.uniform(0.2, 0.4), lower_bound=-0.5, upper_bound=0.2),
        EvilPlatform(0.3, 0.5, 0.3, 0.05, random.uniform(0.2, 0.4), lower_bound=-0.5, upper_bound=0.7)
    ]
    # --- Key System: Randomly assign keys to 3 normal platforms ---
    normal_platforms = [p for p in platforms if type(p) == Platform]
    selected_platforms = random.sample(normal_platforms, 3)
    keys = []
    for p in selected_platforms:
        keys.append(Key(p))
    asteroids = []
    asteroid_spawn_timer = 0

    hud_font = pygame.font.SysFont("Arial", 24)


    clock = pygame.time.Clock()
    running = True
    game_won = False

    # --- Main Game Loop ---
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()

                elif event.key == pygame.K_F9:
                    data = load_checkpoint()
                    player.lives = data["player"]["lives"]
                    player.health = data["player"]["health"]
                    for i, plat in enumerate(platforms):
                        plat.width = data["platforms"][i]["width"]
                        plat.speed = data["platforms"][i]["speed"]
                    for i, key in enumerate(keys):
                        key.collected = data["keys"][i]["collected"]
                    print("Checkpoint loaded.")

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

        player.update(dt, platforms)
        for plat in platforms:
            plat.update(dt)
        for key in keys:
            if not key.collected:
                key_center_x = key.platform.x + key.offset_x
                key_center_y = key.platform.y + key.offset_y
                dx = player.x - key_center_x
                dy = player.y - key_center_y
                if math.sqrt(dx*dx + dy*dy) < (player.diameter/2 + key.size/2):
                    key.collected = True
                    save_checkpoint(player, platforms, keys)

        asteroid_spawn_timer -= dt
        if asteroid_spawn_timer <= 0:
            spawn_y = random.uniform(-0.9, 0.9)
            spawn_x = 1.1
            radius = random.uniform(0.03, 0.07)
            vx = -random.uniform(0.1, 0.3)
            asteroids.append(Asteroid(spawn_x, spawn_y, radius, vx))
            asteroid_spawn_timer = random.uniform(1.0, 3.0)

        for asteroid in asteroids[:]:
            asteroid.update(dt)
            if asteroid.x + asteroid.radius < -1:
                asteroids.remove(asteroid)
            else:
                dx = player.x - asteroid.x
                dy = player.y - asteroid.y
                if math.sqrt(dx*dx + dy*dy) < (player.diameter/2 + asteroid.radius):
                    player.take_damage(10)
                    if asteroid in asteroids:
                        asteroids.remove(asteroid)

        all_keys_collected = all(key.collected for key in keys)
        for plat in platforms:
            if isinstance(plat, WinningPlatform) and all_keys_collected:
                plat_left = plat.x - plat.width/2
                plat_right = plat.x + plat.width/2
                plat_top = plat.y + plat.height
                if (player.x + player.diameter/2 >= plat_left and
                    player.x - player.diameter/2 <= plat_right):
                    if abs((player.y - player.diameter/2) - plat_top) < 0.02:
                        if (player.y + player.diameter/2) >= 1.0:
                            game_won = True

        # --- Draw Background (if needed, comment out if not using) ---
        # For now, we're keeping background aside as per request.
        # --- Draw Game World ---
        glViewport(0, 0, wm.width, wm.height)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        shader.use()
        for plat in platforms:
            plat.draw()
        for asteroid in asteroids:
            asteroid.draw()
        for key in keys:
            key.draw()
        player.draw()
        # --- Draw HUD Overlay ---
        glUseProgram(0)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, wm.width, 0, wm.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        hud_text = f"Lives: {'♥'*player.lives}"
        draw_text(hud_text, hud_font, 20, wm.height - 40)
        health_bar_width = 200
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height - 50)
        glVertex2f(20, wm.height - 70)
        glVertex2f(20 + health_bar_width, wm.height - 70)
        glVertex2f(20 + health_bar_width, wm.height - 50)
        glEnd()
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height - 50)
        glVertex2f(20, wm.height - 70)
        glVertex2f(20 + health_bar_width * (player.health / player.max_health), wm.height - 70)
        glVertex2f(20 + health_bar_width * (player.health / player.max_health), wm.height - 50)
        glEnd()
        keys_text = f"Keys: {sum(1 for key in keys if key.collected)}/3"
        draw_text(keys_text, hud_font, 20, wm.height - 100)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        wm.swap_buffers()

        if game_won:
            print("You Win!")
            pygame.time.wait(2000)
            running = False

        if player.lives <= 0:
            print("Game Over!")
            pygame.time.wait(2000)
            running = False

    wm.quit()
    pygame.font.quit()
    pygame.quit()
    sys.exit()
