import sys
import pygame
import random
from OpenGL.GL import *
import numpy as np
import ctypes
import imgui
from imgui.integrations.pygame import PygameRenderer

from utils.window_manager import WindowManager
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_circle

# Load shader source
def load_shader_source(filepath):
    with open(filepath, 'r') as f:
        return f.read()

# Create an OpenGL object (VAO, VBO, EBO)
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

# Matrix transformation for movement
def translation_matrix(x, y, z):
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ], dtype=np.float32)

# Lily pad logic
class LilyPad:
    def __init__(self, x, y, speed, direction):
        self.pos = [x, y, 0.0]
        self.speed = speed
        self.direction = direction  # 1 = right, -1 = left
        self.vertices, self.indices = create_circle(self.pos, 0.1, [0.4, 0.8, 0.4], points=30)
        self.vao, self.count = create_object(self.vertices, self.indices)

    def update(self, dt):
        self.pos[0] += self.direction * self.speed * dt

        # **Keep movement within river bounds**
        if self.pos[0] > 0.59:
            # self.pos[0] = -0.7  # Wrap around to left
            self.direction = -self.direction  # Change direction
        elif self.pos[0] < -0.59:
            # self.pos[0] = 0.7  # Wrap around to right
            self.direction = -self.direction  # Change direction

def main():
    width, height = 800, 800
    wm = WindowManager(width, height, "Player Movement with Moving Lily Pads")

    imgui.create_context()
    imgui_impl = PygameRenderer()

    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")
    shader_program = Shader(vertex_shader_source, fragment_shader_source)

    modelLoc = glGetUniformLocation(shader_program.ID, "model")

    # Create environment objects
    left_grass_vertices, left_grass_indices = create_rect(-1.0, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    left_grass_vao, left_grass_count = create_object(left_grass_vertices, left_grass_indices)

    river_vertices, river_indices = create_rect(-0.7, -1.0, 1.4, 2.0, [0.0, 0.0, 0.8])
    river_vao, river_count = create_object(river_vertices, river_indices)

    right_grass_vertices, right_grass_indices = create_rect(0.7, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    right_grass_vao, right_grass_count = create_object(right_grass_vertices, right_grass_indices)

    # Generate moving lily pads **within the river bounds**
    lily_pads = [
        LilyPad(
            x=random.uniform(-0.05, 0.05),  # X spawn within river
            y=random.uniform(-0.5, 0.5),  # Y spread across river
            speed=random.uniform(0.3, 0.6),
            direction=random.choice([-1, 1])
        )
        for _ in range(5)
    ]

    # Player variables
    player_pos = [-0.8, 0.0, 0.0]
    player_vertices, player_indices = create_circle([0, 0, 0], 0.08, [1.0, 0.5, 0.0], points=30)
    player_vao, player_count = create_object(player_vertices, player_indices)

    speed = 1.5
    jump_duration = 30
    jump_height = 0.3
    jump_time = 0
    is_jumping = False

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        running = wm.process_events(lambda event: None)

        keys = pygame.key.get_pressed()

        # Reduce movement speed when jumping
        movement_speed = speed * 0.5 if is_jumping else speed  

        if keys[pygame.K_a]:
            player_pos[0] -= movement_speed * dt
        if keys[pygame.K_d]:
            player_pos[0] += movement_speed * dt
        if keys[pygame.K_w]:
            player_pos[1] += movement_speed * dt
        if keys[pygame.K_s]:
            player_pos[1] -= movement_speed * dt

        # Jump Logic
        if keys[pygame.K_SPACE] and not is_jumping:
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

        # Keep player within bounds
        player_pos[0] = max(-1.0, min(1.0, player_pos[0]))
        player_pos[1] = max(-1.0, min(1.0, player_pos[1]))

        # 🚨 Game Over Condition: If Player Touches the River
        if -0.7 <= player_pos[0] <= 0.7 and jump_offset == 0:
            print("Game Over! Player fell into the river.")
            wm.quit()
            sys.exit()

        # 🎉 Win Condition: If Player Reaches the Right Grass
        if player_pos[0] > 0.7:
            print("You Won! Player reached the other side.")
            wm.quit()
            sys.exit()

        # Update lily pad positions
        for lily_pad in lily_pads:
            lily_pad.update(dt)

        glViewport(0, 0, width, height)
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        shader_program.use()

        identity = np.eye(4, dtype=np.float32)
        glUniformMatrix4fv(modelLoc, 1, GL_TRUE, identity)

        glBindVertexArray(left_grass_vao)
        glDrawElements(GL_TRIANGLES, left_grass_count, GL_UNSIGNED_INT, None)

        glBindVertexArray(river_vao)
        glDrawElements(GL_TRIANGLES, river_count, GL_UNSIGNED_INT, None)

        glBindVertexArray(right_grass_vao)
        glDrawElements(GL_TRIANGLES, right_grass_count, GL_UNSIGNED_INT, None)

        for lily_pad in lily_pads:
            model = translation_matrix(lily_pad.pos[0], lily_pad.pos[1], lily_pad.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(lily_pad.vao)
            glDrawElements(GL_TRIANGLES, lily_pad.count, GL_UNSIGNED_INT, None)

        model = translation_matrix(player_pos[0], player_pos[1] + jump_offset, player_pos[2])
        glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
        glBindVertexArray(player_vao)
        glDrawElements(GL_TRIANGLES, player_count, GL_UNSIGNED_INT, None)

        wm.swap_buffers()

    shader_program.delete()
    wm.quit()
    sys.exit()

if __name__ == "__main__":
    main()


