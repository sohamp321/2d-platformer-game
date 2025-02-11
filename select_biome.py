# src/biome_menu.py

import sys
import pygame
from pygame.locals import KEYDOWN, K_UP, K_DOWN, K_RETURN, QUIT
import OpenGL.GL as gl
import numpy as np
import ctypes
from utils.window_manager import WindowManager

def draw_text(text, font_obj, pos_x, pos_y, color=(255,255,255)):
    """
    Renders text using pygame's font and draws it as a textured quad
    with its bottom-left corner at (pos_x, pos_y).
    """
    # Render text to a pygame surface.
    text_surface = font_obj.render(text, True, color).convert_alpha()
    text_width, text_height = text_surface.get_size()
    text_data = pygame.image.tostring(text_surface, 'RGBA', True)
    
    # Create and bind a texture.
    texture = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, text_width, text_height,
                    0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, text_data)
    
    # Enable blending and set color.
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glColor4f(1, 1, 1, 1)
    
    # Draw a textured quad.
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    gl.glBegin(gl.GL_QUADS)
    gl.glTexCoord2f(0, 0); gl.glVertex2f(pos_x, pos_y)
    gl.glTexCoord2f(1, 0); gl.glVertex2f(pos_x + text_width, pos_y)
    gl.glTexCoord2f(1, 1); gl.glVertex2f(pos_x + text_width, pos_y + text_height)
    gl.glTexCoord2f(0, 1); gl.glVertex2f(pos_x, pos_y + text_height)
    gl.glEnd()
    gl.glDisable(gl.GL_TEXTURE_2D)
    
    # Delete the texture.
    gl.glDeleteTextures([texture])

def display_biome_menu():
    """
    Displays the biome selection menu. The menu shows a title ("Select Your Biome")
    and three options: River, Forest, and Desert. The user navigates with UP/DOWN and
    selects an option with ENTER. Returns the selected biome as a string.
    """
    width, height = 800, 800
    wm = WindowManager(width, height, "Select Biome")
    
    # Attempt to load the custom Minecraft-like font.
    try:
        font = pygame.font.Font("assets/fonts/minecraft_font.ttf", 28)
    except Exception as e:
        print("Custom font not found, using default.", e)
        font = pygame.font.SysFont("Arial", 28)
    
    # Define biome options.
    options = ["River", "Forest", "Desert"]
    selected = 0
    
    running = True
    while running:
        # Process events.
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == K_DOWN:
                    selected = (selected + 1) % len(options)
                elif event.key == K_RETURN:
                    running = False
                    break
        
        # Clear the screen with a dark gray background.
        gl.glClearColor(0.1, 0.1, 0.1, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        
        # Set up a 2D orthographic projection.
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, 0, height, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        
        # Draw the title at the top.
        title = "Select Your Biome"
        title_surface = font.render(title, True, (255,255,255))
        title_width, title_height = title_surface.get_size()
        draw_text(title, font, (width - title_width) // 2, height - 150)
        
        # Draw the biome options (centered vertically).
        for i, option in enumerate(options):
            col = (255, 255, 0) if i == selected else (255, 255, 255)
            option_surface = font.render(option, True, col)
            opt_width, opt_height = option_surface.get_size()
            # Arrange options vertically (e.g., centered with 50 pixels spacing).
            y_position = height // 2 - i * 50
            draw_text(option, font, (width - opt_width) // 2, y_position, color=col)
        
        wm.swap_buffers()
    
    wm.quit()
    return options[selected]

if __name__ == "__main__":
    biome = display_biome_menu()
    print("Biome selected:", biome)
