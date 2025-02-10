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

# Lily pad logic with horizontal bounds.
class LilyPad:
    def __init__(self, x, y, speed, direction, right_bound, left_bound, radius=0.1):
        self.pos = [x, y, 0.0]
        self.speed = speed
        self.direction = direction  # 1 = right, -1 = left
        self.radius = radius
        self.vertices, self.indices = create_circle(self.pos, self.radius, [0.4, 0.8, 0.4], points=30)
        self.vao, self.count = create_object(self.vertices, self.indices)
        self.right_bound = right_bound
        self.left_bound = left_bound

    def update(self, dt):
        self.pos[0] += self.direction * self.speed * dt
        if self.pos[0] > self.right_bound:
            self.direction = -self.direction  # Change direction
        elif self.pos[0] < self.left_bound:
            self.direction = -self.direction  # Change direction

    def collides_with(self, player_x, effective_y):
        # Calculate distance between player and lily pad center
        distance = np.sqrt((player_x - self.pos[0])**2 + (effective_y - self.pos[1])**2)
        return distance < self.radius+0.1

def main():
    width, height = 800, 800
    wm = WindowManager(width, height, "Player Movement with Lily Pad Collision")

    imgui.create_context()
    imgui_impl = PygameRenderer()

    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")
    shader_program = Shader(vertex_shader_source, fragment_shader_source)

    modelLoc = glGetUniformLocation(shader_program.ID, "model")

    # Create environment objects.
    left_grass_vertices, left_grass_indices = create_rect(-1.0, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    left_grass_vao, left_grass_count = create_object(left_grass_vertices, left_grass_indices)

    river_vertices, river_indices = create_rect(-0.7, -1.0, 1.4, 2.0, [0.0, 0.0, 0.8])
    river_vao, river_count = create_object(river_vertices, river_indices)

    right_grass_vertices, right_grass_indices = create_rect(0.7, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    right_grass_vao, right_grass_count = create_object(right_grass_vertices, right_grass_indices)

    # Spawn lily pads at fixed y positions.
    fixed_y_positions = [-0.1, 0.15, -0.25, 0.3, -0.4, 0.45]
    lily_pads = [
        LilyPad(
            x=random.uniform(-0.05, 0.05),  # X spawn within a small range around 0.
            y=y_val,
            speed=random.uniform(0.1, 0.3),
            direction=random.choice([-1, 1]),
            right_bound=0.59,
            left_bound=-0.59
        )
        for y_val in fixed_y_positions
    ]

    # Player variables.
    player_pos = [-0.8, 0.0, 0.0]
    player_vertices, player_indices = create_circle([0, 0, 0], 0.05, [1.0, 0.5, 0.0], points=30)
    player_vao, player_count = create_object(player_vertices, player_indices)

    speed = 1  # Normal movement speed.
    jump_duration = 30  # Frames.
    jump_height = 0.3  # Maximum jump offset.
    jump_time = 0
    is_jumping = False

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        running = wm.process_events(lambda event: None)

        keys = pygame.key.get_pressed()

        # Use reduced speed when jumping.
        movement_speed = speed * 0.5 if is_jumping else speed

        # Horizontal movement (WASD).
        if keys[pygame.K_a]:
            player_pos[0] -= movement_speed * dt
        if keys[pygame.K_d]:
            player_pos[0] += movement_speed * dt
        if keys[pygame.K_w]:
            player_pos[1] += movement_speed * dt
        if keys[pygame.K_s]:
            player_pos[1] -= movement_speed * dt

        # Jump logic.
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

        # Keep player within bounds.
        player_pos[0] = max(-1.0, min(1.0, player_pos[0]))
        player_pos[1] = max(-1.0, min(1.0, player_pos[1]))

        # Compute effective y for collision (base y + jump offset).
        effective_y = player_pos[1] + jump_offset

        # Collision Detection:
        # Only perform collision check if the player is near the ground (i.e. jump_offset is small)
        # This allows mid-air movement without triggering game over.
        if -0.7 <= player_pos[0] <= 0.7:  # Only check when player is over river
            player_safe = False
            
            if is_jumping and jump_offset > 0.05:  # If player is high in jump, they're safe
                player_safe = True
            else:
                for lily_pad in lily_pads:
                    if lily_pad.collides_with(player_pos[0], effective_y):
                        player_safe = True
                        break
            
            if not player_safe:
                # Only end game if player is close to water level
                if not is_jumping or (is_jumping and jump_offset < 0.05):
                    print("Game Over! Player fell into the river.")
                    wm.quit()
                    sys.exit()

        # Win Condition: If Player Reaches the Right Grass.
        if player_pos[0] > 0.7:
            print("You Won! Player reached the other side.")
            wm.quit()
            sys.exit()

        # Update lily pad positions.
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
        glBindVertexArray(0)

        glBindVertexArray(river_vao)
        glDrawElements(GL_TRIANGLES, river_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        glBindVertexArray(right_grass_vao)
        glDrawElements(GL_TRIANGLES, right_grass_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        for lily_pad in lily_pads:
            model = translation_matrix(lily_pad.pos[0], lily_pad.pos[1], lily_pad.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(lily_pad.vao)
            glDrawElements(GL_TRIANGLES, lily_pad.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

        model = translation_matrix(player_pos[0], effective_y, player_pos[2])
        glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
        glBindVertexArray(player_vao)
        glDrawElements(GL_TRIANGLES, player_count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        wm.swap_buffers()

    shader_program.delete()
    wm.quit()
    sys.exit()

if __name__ == "__main__":
    main()
