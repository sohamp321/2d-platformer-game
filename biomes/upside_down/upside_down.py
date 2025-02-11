import sys
import pygame
import numpy as np
import math
import ctypes
import random
from OpenGL.GL import *
from pygame.locals import DOUBLEBUF, OPENGL, QUIT, KEYDOWN, K_SPACE, K_g

# Initialize pygame and font module.
pygame.init()
# Use a font that supports Unicode heart symbols. Change the font name if necessary.
hud_font = pygame.font.SysFont("Segoe UI Symbol", 24)

# Import your helper modules (assumed to be part of your project structure)
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

# --- Helper Function ---
def translation_matrix(x, y, z):
    """Creates a 4x4 translation matrix."""
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ], dtype=np.float32)

# --- Platform Class (unchanged) ---
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

# --- WinningPlatform Class ---
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

# --- EvilPlatform Class (with spikes) ---
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
            spike_center_x = -width/2 + (i+1) * width/(n_spikes+1)
            if not flip_spike:
                v1 = [spike_center_x - spike_base/2, self.height, 0]
                v2 = [spike_center_x + spike_base/2, self.height, 0]
                v3 = [spike_center_x, self.height + spike_height, 0]
            else:
                v1 = [spike_center_x - spike_base/2, 0, 0]
                v2 = [spike_center_x + spike_base/2, 0, 0]
                v3 = [spike_center_x, -spike_height, 0]
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

# --- Key Class ---
class Key:
    def __init__(self, platform):
        self.platform = platform
        self.collected = False
        self.size = 0.05
        if platform.y < 0:
            self.offset = np.array([0, platform.height + 0.03, 0])
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

# --- Arrow Class (rotated to point horizontally) ---
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
                [-1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            model = translation_matrix(self.x, self.y, 0) @ scale_matrix
        else:
            model = translation_matrix(self.x, self.y, 0)
        glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

# --- Player Class (with health, damage, and win/damage conditions) ---
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
        vertices, indices = create_circle([0, 0, 0], diameter/2, [1.0, 0.0, 0.0], points=30)
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
            self.vy += (self.gravity * self.gravity_direction) * dt
        self.y += self.vy * dt
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
                                sys.exit()
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
                                sys.exit()
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

# --- Main Game Function ---
def new_game(wm):
    """
    Creates a world with 10 moving platforms (5 bottom, 5 top) and a player.
    Every alternating platform is evil (with spikes); for top evil platforms, spikes are rendered on the bottom.
    The bottom right platform is the winning platform.
    Three keys are placed on randomly selected non-evil, non-winning platforms.
    White triangular arrows randomly spawn and move horizontally.
    If an arrow touches the player, 10 health is deducted.
    The player only wins if all keys are collected and the winning platform is landed on.
    Press SPACE to jump and G to flip gravity.
    """
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

    platforms = []
    x_positions = [-0.8, -0.4, 0.0, 0.4, 0.8]
    
    # Create bottom platforms (spikes on top). The last one (x=0.8) is the winning platform.
    for i, x in enumerate(x_positions):
        if i == len(x_positions) - 1:
            p = WinningPlatform(x, -1.0, 0.4, 0.05, random.uniform(0.1, 0.2), -1.0, -0.85, model_loc)
        elif i % 2 == 0:
            p = Platform(x, -1.0, 0.4, 0.05, random.uniform(0.1, 0.2), -1.0, -0.85, model_loc)
        else:
            p = EvilPlatform(x, -1.0, 0.4, 0.05, random.uniform(0.2, 0.4), -1.0, -0.75, model_loc, flip_spike=False)
        platforms.append(p)
    
    # Create top platforms (spikes on bottom).
    for i, x in enumerate(x_positions):
        if i % 2 == 0:
            p = Platform(x, 0.85, 0.4, 0.05, random.uniform(0.1, 0.2), 0.85, 0.95, model_loc)
        else:
            p = EvilPlatform(x, 0.85, 0.4, 0.05, random.uniform(0.2, 0.4), 0.75, 0.95, model_loc, flip_spike=True)
        platforms.append(p)
    
    # Candidate indices for keys: only choose from normal platforms (exclude EvilPlatform and WinningPlatform).
    candidate_indices = [i for i, p in enumerate(platforms) if not isinstance(p, EvilPlatform) and not isinstance(p, WinningPlatform)]
    key_indices = random.sample(candidate_indices, 3)
    keys = []
    for idx in key_indices:
        keys.append(Key(platforms[idx]))
    
    player = Player(0, 0, 0.1, model_loc)

    arrows = []

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        # Spawn a new arrow with a small probability.
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

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_SPACE:
                    player.jump()
                elif event.key == K_g:
                    player.flip_gravity()

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
        all_keys_collected = all(key.collected for key in keys)
        player.update(dt, platforms, all_keys_collected)

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

        # --- Draw HUD ---
        glUseProgram(0)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, wm.width, 0, wm.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        hud_text = f"Lives: {'♥'*player.lives}"
        draw_text(hud_text, hud_font, 20, wm.height - 70)
        health_bar_width = 200
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height - 80)
        glVertex2f(20, wm.height - 100)
        glVertex2f(20 + health_bar_width, wm.height - 100)
        glVertex2f(20 + health_bar_width, wm.height - 80)
        glEnd()
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_QUADS)
        glVertex2f(20, wm.height - 80)
        glVertex2f(20, wm.height - 100)
        glVertex2f(20 + health_bar_width * (player.health / player.max_health), wm.height - 100)
        glVertex2f(20 + health_bar_width * (player.health / player.max_health), wm.height - 80)
        glEnd()
        keys_text = f"Keys: {sum(1 for key in keys if key.collected)}/3"
        draw_text(keys_text, hud_font, 20, wm.height - 130)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        wm.swap_buffers()

    wm.quit()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    wm = WindowManager(800, 600, "Keys, Arrows & Winning Platform Example")
    new_game(wm)
