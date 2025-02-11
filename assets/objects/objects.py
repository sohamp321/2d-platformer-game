import numpy as np
import math

def create_rect(x, y, width, height, color):
    """
    Creates a rectangle (two triangles) with lower‐left corner at (x,y) and the given width and height.
    'color' is a list [r, g, b]. Coordinates are assumed to be in normalized device coordinates.
    Returns (vertices, indices) as numpy arrays.
    """
    vertices = [
        x,      y,       0.0, *color,
        x+width, y,       0.0, *color,
        x+width, y+height,0.0, *color,
        x,      y+height,0.0, *color
    ]
    indices = [0, 1, 2, 0, 2, 3]
    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)

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

def create_circle(center, radius, color, points=30):
    """
    Creates a circle centered at 'center' with the given radius and color.
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
    indices.extend([0, points, 1])
    return np.array(vertices, dtype=np.float32), np.array(indices, dtype=np.uint32)


def create_square(pos, size, color):
    # Create a square centered at pos with given size
    vertices = np.array([
        # positions        # colors
        pos[0]-size, pos[1]-size, pos[2], *color,  # bottom left
        pos[0]+size, pos[1]-size, pos[2], *color,  # bottom right
        pos[0]+size, pos[1]+size, pos[2], *color,  # top right
        pos[0]-size, pos[1]+size, pos[2], *color,  # top left
    ], dtype=np.float32)
    
    indices = np.array([
        0, 1, 2,  # first triangle
        2, 3, 0   # second triangle
    ], dtype=np.uint32)
    
    return vertices.reshape(-1, 6), indices
