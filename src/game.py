import numpy as np
from OpenGL.GL import *
import imgui
from imgui.integrations.pygame import PygameRenderer
from utils.graphics import Shader
from assets.objects.objects import create_rect, create_circle
from src.environment import Environment
from src.player import Player

def load_shader_source(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def identity_matrix():
    return np.eye(4, dtype=np.float32)

class Game:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # Load shader sources.
        vertex_shader_source = load_shader_source("assets/shaders/default.vert")
        fragment_shader_source = load_shader_source("assets/shaders/default.frag")
        self.shader = Shader(vertex_shader_source, fragment_shader_source)
        self.modelLoc = glGetUniformLocation(self.shader.ID, "model")
        # Create the environment and player.
        self.environment = Environment()
        self.player = Player(initial_pos=[-0.8, 0.0, 0.0])
        # Initialize ImGui (the PygameRenderer was already set up in main.py).
    
    def update(self, dt):
        self.player.update(dt)
    
    def render(self):
        glViewport(0, 0, self.width, self.height)
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        self.shader.use()
        
        # Render static environment with identity model matrix.
        glUniformMatrix4fv(self.modelLoc, 1, GL_TRUE, identity_matrix())
        self.environment.render()
        
        # Render player with its translation.
        glUniformMatrix4fv(self.modelLoc, 1, GL_TRUE, self.player.get_model_matrix())
        self.player.render()
        
        io = imgui.get_io()
        io.display_size = (self.width, self.height)
        imgui.new_frame()
        # (Optional: add UI elements here)
        imgui.render()
    
    def cleanup(self):
        self.shader.delete()
        self.environment.cleanup()
        self.player.cleanup()
