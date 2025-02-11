from OpenGL.GL import *
import numpy as np
import math
import ctypes
from assets.objects.objects import  create_object

def create_lilypad(center, radius, color, points=30):
    """
    Creates a circle (triangle fan) centered at 'center' with the given radius and color.
    'center' is a list of 3 floats.
    Returns (vertices, indices) as numpy arrays.
    """
    vertices = []
    indices = []
    # Center vertex.
    vertices.extend(center + color)
    # Perimeter vertices.
    for i in range(points + 1):
        angle = 2 * math.pi * i / points
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        z = center[2]
        vertices.extend([x, y, z] + color)
    # Build indices for the fan.
    for i in range(1, points):
        indices.extend([0, i, i+1])
    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)

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
        dy = y - self.pos[1] * 2
        return np.sqrt(dx*dx + dy*dy) < (self.radius + 0.05)