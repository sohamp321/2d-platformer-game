import sys
import pygame
from pygame.locals import KEYDOWN, K_UP, K_DOWN, K_RETURN, QUIT
import OpenGL.GL as gl

def draw_text(text, font_obj, pos_x, pos_y, color=(255, 255, 255)):
    text_surface = font_obj.render(text, True, color).convert_alpha()
    text_width, text_height = text_surface.get_size()
    text_data = pygame.image.tostring(text_surface, 'RGBA', True)
    
    texture = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, text_width, text_height,
                    0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, text_data)
    
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glColor4f(1, 1, 1, 1)
    
    gl.glEnable(gl.GL_TEXTURE_2D)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
    gl.glBegin(gl.GL_QUADS)
    gl.glTexCoord2f(0, 0); gl.glVertex2f(pos_x, pos_y)
    gl.glTexCoord2f(1, 0); gl.glVertex2f(pos_x + text_width, pos_y)
    gl.glTexCoord2f(1, 1); gl.glVertex2f(pos_x + text_width, pos_y + text_height)
    gl.glTexCoord2f(0, 1); gl.glVertex2f(pos_x, pos_y + text_height)
    gl.glEnd()
    gl.glDisable(gl.GL_TEXTURE_2D)
    gl.glDeleteTextures([texture])

def display_pause_screen(wm):
    """
    Displays a pause menu overlay.
    Options: Continue, New Game, Load Game, Select Biome, Exit.
    Returns the selected option as a string.
    """
    width, height = wm.width, wm.height
    try:
        font = pygame.font.Font("assets/fonts/minecraft_font.ttf", 28)
    except Exception as e:
        print("Custom font not found, using default.", e)
        font = pygame.font.SysFont("Arial", 32)
    
    message = "Game Paused"
    options = ["Continue", "New Game", "Load Game", "Select Biome", "Exit"]
    selected = 0

    running = True
    while running:
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
                    return options[selected]
                elif event.key == pygame.K_ESCAPE:
                    # If Escape is pressed again, resume game.
                    running = False
                    return "Continue"
        
        # Clear screen with a dark overlay.
        gl.glClearColor(0.1, 0.1, 0.1, 0.8)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        
        # Setup 2D orthographic projection.
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(0, width, 0, height, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        
        # Draw pause title.
        title_surface = font.render(message, True, (255, 255, 255))
        title_width, _ = title_surface.get_size()
        draw_text(message, font, (width - title_width) // 2, height - 150)
        
        # Draw options.
        for i, option in enumerate(options):
            color = (255, 255, 0) if i == selected else (255, 255, 255)
            option_surface = font.render(option, True, color)
            opt_width, _ = option_surface.get_size()
            y_position = height // 2 - i * 50
            draw_text(option, font, (width - opt_width) // 2, y_position, color=color)
        
        wm.swap_buffers()
