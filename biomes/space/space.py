import sys
import pygame
import numpy as np
import math
import ctypes
import random
from OpenGL.GL import *
from pygame.locals import DOUBLEBUF, OPENGL, QUIT

# Import your helper modules:
from utils.window_manager import WindowManager
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_circle, create_object


def new_game(wm):
    """
    A space-themed platformer using normalized coordinates.
    Level design:
      - 1 WinningPlatform (blue) on the right (y=0.75, height=0.25 so top=1.0).
      - 3 Normal Platforms.
      - 2 Evil Platforms.
    When the player is on the WinningPlatform and their top touches y>=1.0, they win.
    The player starts with 3 lives. Touching an EvilPlatform causes loss of one life and a respawn.
    On losing all lives, the game ends.
    The provided window manager (wm) is used.
    """
    # --- Helper Function ---
    def translation_matrix(x, y, z):
        """Creates a 4x4 translation matrix."""
        return np.array([
            [1, 0, 0, x],
            [0, 1, 0, y],
            [0, 0, 1, z],
            [0, 0, 0, 1]
        ], dtype=np.float32)

    # --- Create Shader Program ---
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

    # --- Define Platform Classes ---

    class Platform:
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound):
            """
            x, y: For a normal platform, x is the center and y is the bottom edge.
            width, height: Dimensions in normalized coordinates.
            lower_bound, upper_bound: Vertical limits for its movement.
            """
            self.x = x
            self.y = y
            self.width = width
            self.height = height
            self.speed = speed
            self.direction = 1  # 1 = moving upward; -1 = moving downward.
            self.lower_bound = lower_bound
            self.upper_bound = upper_bound
            # Create a green rectangle.
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
            """
            An evil platform with spikes. Landing on it causes the player to lose a life.
            """
            super().__init__(x, y, width, height, speed, lower_bound, upper_bound)
            # Override base color to red.
            vertices, indices = create_rect(-width/2, 0, width, height, [1.0, 0.0, 0.0])
            self.vao, self.count = create_object(vertices, indices)
            # Create spikes along the top.
            self.spikes = []  # List of (VAO, spike_count) tuples.
            n_spikes = 3
            spike_height = 0.05
            spike_base = width / (n_spikes * 1.5)
            for i in range(n_spikes):
                spike_center_x = -width/2 + (i+1) * width/(n_spikes+1)
                # Define triangle vertices (local coordinates)
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
                # Create and bind EBO for indices.
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
            """
            A blue winning platform. When the player is on this platform and their top touches
            the top of the screen, they win.
            """
            super().__init__(x, y, width, height, speed, lower_bound, upper_bound)
            vertices, indices = create_rect(-width/2, 0, width, height, [0.0, 0.0, 1.0])
            self.vao, self.count = create_object(vertices, indices)

    class Player:
        def __init__(self, x, y, diameter):
            """
            x, y: center of the circle.
            diameter: the full width of the circle.
            """
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
            self.health = 100
            self.lives = 3  # Player starts with 3 lives.
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
                    # Check collision for EvilPlatform first.
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

        def respawn(self):
            self.x = self.spawn_x
            self.y = self.spawn_y
            self.vy = 0
            self.jumps_remaining = self.max_jumps

        def draw(self):
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Create Game Objects (Level Design) ---
    # Player: centered at (0, -0.8) with a diameter of 0.1.
    player = Player(0, -0.8, 0.1)
    # Level design: 6+ platforms total.
    platforms = [
        # 1 WinningPlatform (blue): placed on the right side; bottom at 0.75, height 0.25 so top=1.0.
        WinningPlatform(0.8, 0.75, 0.3, 0.05, speed=0.4, lower_bound=0.75, upper_bound=1.0),
        # 3 Normal Platforms (randomized).
        Platform(-0.8, -0.75, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.8, upper_bound=-0.6),
        Platform(-0.5, -0.5, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.5, upper_bound=-0.3),
        Platform(0, -0.2, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=-0.2, upper_bound=0.0),
        Platform(0.5, 0.1, random.uniform(0.4, 0.6), 0.05, random.uniform(0.1, 0.2), lower_bound=0.1, upper_bound=0.3),
        Platform(0.7, 0.5, random.uniform(0.2, 0.3), 0.05, random.uniform(0.1, 0.2), lower_bound=0.1, upper_bound=0.6),
        # 2 Evil Platforms (randomized).
        EvilPlatform(random.uniform(-0.8, -0.5), 0, 0.3, 0.05, random.uniform(0.2, 0.4), lower_bound=-0.5, upper_bound=0.2),
        EvilPlatform(0.3, 0.5, 0.3, 0.05, random.uniform(0.2, 0.4), lower_bound=-0.5, upper_bound=0.7)
    ]

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

        # Horizontal movement with A and D keys.
        keys = pygame.key.get_pressed()
        move_speed = 0.5
        if keys[pygame.K_a]:
            player.x -= move_speed * dt
        if keys[pygame.K_d]:
            player.x += move_speed * dt

        # Clamp player within screen bounds.
        if player.x - player.diameter/2 < -1:
            player.x = -1 + player.diameter/2
        if player.x + player.diameter/2 > 1:
            player.x = 1 - player.diameter/2

        player.update(dt, platforms)
        for plat in platforms:
            plat.update(dt)

        # Check win condition: if the player is on a WinningPlatform and their top (y+diameter/2) >=1.0.
        for plat in platforms:
            if isinstance(plat, WinningPlatform):
                plat_left = plat.x - plat.width/2
                plat_right = plat.x + plat.width/2
                plat_top = plat.y + plat.height
                if (player.x + player.diameter/2 >= plat_left and
                    player.x - player.diameter/2 <= plat_right):
                    if abs((player.y - player.diameter/2) - plat_top) < 0.02:
                        if (player.y + player.diameter/2) >= 1.0:
                            game_won = True

        glViewport(0, 0, wm.width, wm.height)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        shader.use()

        for plat in platforms:
            plat.draw()
        player.draw()

        wm.swap_buffers()

        if game_won:
            print("You Win!")
            pygame.time.wait(2000)
            running = False

        # Check if lives are exhausted.
        if player.lives <= 0:
            print("Game Over!")
            pygame.time.wait(2000)
            running = False

    wm.quit()
    pygame.font.quit()
    pygame.quit()
    sys.exit()
