import numpy as np
import ctypes
from OpenGL.GL import *
from assets.objects.objects import create_rect, create_circle

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

class Environment:
    def __init__(self):
        # Left Grass: x from -1.0 to -0.7 (width 0.3), y from -1.0 to 1.0.
        left_vertices, left_indices = create_rect(-1.0, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
        self.left_grass = create_object(left_vertices, left_indices)
        # River: x from -0.7 to 0.7 (width 1.4).
        river_vertices, river_indices = create_rect(-0.7, -1.0, 1.4, 2.0, [0.0, 0.0, 0.8])
        self.river = create_object(river_vertices, river_indices)
        # Right Grass: x from 0.7 to 1.0 (width 0.3).
        right_vertices, right_indices = create_rect(0.7, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
        self.right_grass = create_object(right_vertices, right_indices)
        # Lily Pads.
        self.lily_pads = []
        lily_positions = [[-0.1, -0.3, 0.0], [0.0, 0.4, 0.0], [0.2, -0.2, 0.0]]
        for pos in lily_positions:
            vertices, indices = create_circle(pos, 0.1, [0.4, 0.8, 0.4], points=30)
            vao, count = create_object(vertices, indices)
            self.lily_pads.append((vao, count))
    
    def render(self):
        # Render left grass.
        glBindVertexArray(self.left_grass[0])
        glDrawElements(GL_TRIANGLES, self.left_grass[1], GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        # Render river.
        glBindVertexArray(self.river[0])
        glDrawElements(GL_TRIANGLES, self.river[1], GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        # Render right grass.
        glBindVertexArray(self.right_grass[0])
        glDrawElements(GL_TRIANGLES, self.right_grass[1], GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        # Render lily pads.
        for vao, count in self.lily_pads:
            glBindVertexArray(vao)
            glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
    
    def cleanup(self):
        glDeleteVertexArrays(1, [self.left_grass[0]])
        glDeleteVertexArrays(1, [self.river[0]])
        glDeleteVertexArrays(1, [self.right_grass[0]])
        for vao, count in self.lily_pads:
            glDeleteVertexArrays(1, [vao])
