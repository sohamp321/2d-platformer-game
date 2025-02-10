import pygame
import numpy as np
from OpenGL.GL import *
import ctypes
from assets.objects.objects import create_circle

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

class Player:
    def __init__(self, initial_pos):
        # Position as a list [x, y, z].
        self.pos = initial_pos
        vertices, indices = create_circle([0,0,0], 0.08, [1.0, 0.5, 0.0], points=30)
        self.vao, self.count = create_object(vertices, indices)
        self.speed = 2.0  # Slower speed
    
    def update(self, dt):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            self.pos[1] += self.speed * dt
        if keys[pygame.K_s]:
            self.pos[1] -= self.speed * dt
        if keys[pygame.K_a]:
            self.pos[0] -= self.speed * dt
        if keys[pygame.K_d]:
            self.pos[0] += self.speed * dt
        
        # Clamp the player's position to remain within [-1, 1] for x and y.
        self.pos[0] = max(-1, min(self.pos[0], 1))
        self.pos[1] = max(-1, min(self.pos[1], 1))
    
    def get_model_matrix(self):
        return translation_matrix(self.pos[0], self.pos[1], self.pos[2])
    
    def render(self):
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, self.count, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
    
    def cleanup(self):
        glDeleteVertexArrays(1, [self.vao])
