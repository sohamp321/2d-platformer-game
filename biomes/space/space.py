import sys
import pygame
import numpy as np
import math
import ctypes
from OpenGL.GL import *
from pygame.locals import DOUBLEBUF, OPENGL, QUIT

# Import your helper modules:
from utils.window_manager import WindowManager
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_circle, create_object


def new_game(wm):
    """
    A space-themed platformer that uses normalized coordinates only.
    The window manager (wm) instance is provided externally.
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
    # The vertex shader now uses only the model matrix.
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

    # --- Define Game Object Classes using normalized coordinates ---
    class Platform:
        def __init__(self, x, y, width, height, speed, lower_bound, upper_bound):
            """
            x, y: center position of the platform (for x) and y position of its bottom edge.
            width, height: dimensions in normalized coordinates.
            lower_bound, upper_bound: vertical limits (in normalized coordinates) for its movement.
            """
            self.x = x
            self.y = y
            self.width = width
            self.height = height
            self.speed = speed
            self.direction = 1  # 1 = moving upward; -1 = moving downward
            self.lower_bound = lower_bound
            self.upper_bound = upper_bound
            # Create geometry: rectangle defined with bottom-left at (-width/2, 0)
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

    class Player:
        def __init__(self, x, y, diameter):
            """
            x, y: center of the circle.
            diameter: the full width of the circle.
            """
            self.x = x
            self.y = y
            self.diameter = diameter
            self.vy = 0.0
            self.gravity = -1.0       # Gravity (adjusted for normalized coordinates)
            self.jump_strength = 0.2  # Jump strength in normalized units
            self.on_ground = False
            # Create geometry: a red circle with radius = diameter/2.
            vertices, indices = create_circle([0, 0, 0], diameter/2, [1.0, 0.0, 0.0], points=30)
            self.vao, self.count = create_object(vertices, indices)

        def update(self, dt, platforms):
            if not self.on_ground:
                self.vy += self.gravity * dt
            self.y += self.vy * dt
            self.on_ground = False

            # For a circle, treat (x, y) as the center.
            player_bottom = self.y - self.diameter/2
            for plat in platforms:
                plat_left = plat.x - plat.width/2
                plat_right = plat.x + plat.width/2
                plat_top = plat.y + plat.height
                # Check horizontal overlap and if the circle's bottom is at or near the platform top.
                if (self.x + self.diameter/2 >= plat_left and self.x - self.diameter/2 <= plat_right):
                    if player_bottom <= plat_top and ((self.y - self.vy*dt) - self.diameter/2) > plat_top - 0.05 and self.vy <= 0:
                        self.y = plat_top + self.diameter/2
                        self.vy = 0
                        self.on_ground = True

            # Prevent falling below the bottom of the screen (normalized y = -1)
            if self.y - self.diameter/2 < -1:
                self.y = -1 + self.diameter/2
                self.vy = 0
                self.on_ground = True

        def jump(self):
            if self.on_ground:
                self.vy = self.jump_strength
                self.on_ground = False

        def draw(self):
            model = translation_matrix(self.x, self.y, 0)
            glUniformMatrix4fv(model_loc, 1, GL_TRUE, model)
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

    # --- Create Game Objects (using normalized coordinates) ---
    # For example, the player is centered at (0, -0.8) with a diameter of 0.2.
    player = Player(0, -0.8, 0.2)
    # Create a few moving platforms with positions and sizes in the range [-1, 1].
    platforms = [
        Platform(0, 0, 0.5, 0.05, speed=0.2, lower_bound=-1, upper_bound=0.5),
        Platform(-0.7, -0.4, 0.4, 0.05, speed=0.15, lower_bound=-0.5, upper_bound=-0.3),
        Platform(0.7, 0.2, 0.4, 0.05, speed=0.1, lower_bound=0.1, upper_bound=0.3)
    ]

    clock = pygame.time.Clock()
    running = True

    # --- Main Game Loop ---
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()

        player.update(dt, platforms)
        for plat in platforms:
            plat.update(dt)

        glViewport(0, 0, wm.width, wm.height)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        shader.use()

        for plat in platforms:
            plat.draw()
        player.draw()

        wm.swap_buffers()

    wm.quit()
    pygame.font.quit()
    pygame.quit()
    sys.exit()
