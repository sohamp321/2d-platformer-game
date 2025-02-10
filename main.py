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
from assets.objects.objects import create_rect, create_lilypad, create_square, create_circle

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
        self.vertices, self.indices = create_lilypad(self.pos, self.radius, [0.4, 0.8, 0.4], points=30)
        self.vao, self.count = create_object(self.vertices, self.indices)
        self.right_bound = right_bound
        self.left_bound = left_bound

    def update(self, dt):
        self.pos[0] += self.direction * self.speed * dt
        if self.pos[0] > self.right_bound:
            self.direction = -self.direction  # Change direction
        elif self.pos[0] < self.left_bound:
            self.direction = -self.direction  # Change direction
            
    def collides_with(self, x, y):
        # Check if player position is within lily pad radius
        print(f"Player: {x}, {y}")
        print(f"Lily Pad: {self.pos[0]}, {self.pos[1]}")
        dx = x - self.pos[0]
        dy = y - self.pos[1]*2
        distance = np.sqrt(dx*dx + dy*dy)
        print(distance)
        return distance < (self.radius+0.05)
    
# Add after LilyPad class

class Wave:
    def __init__(self, x, speed, color=[0.0, 0.0, 1.0], width=0.1, height=1.8):
        self.pos = [x, 0.0, 0.0]  # Waves move horizontally
        self.speed = speed
        self.width = width
        self.height = height
        
        # Create wave vertices (vertical rectangle)
        vertices, indices = create_rect(0, -1, self.width, self.height, color)
        self.vao, self.count = create_object(vertices, indices)
        
    def reset_position(self, x=None):
        """Reset wave to a new or default position with random attributes"""
        if x is None:
            # Start at left shore with some randomization
            x = -0.7
        self.pos = [x, 0.0, 0.0]
        # Randomize speed each time wave resets
        self.speed = random.uniform(0.05, 0.2)
        self.width = random.uniform(0.1, 0.2)
        self.height = random.uniform(1.2, 2.0)
        self.color = [0.0, 0.0, random.uniform(0.5, 0.9)]
        # Randomize color each time wave resets

        
    def update(self, dt):
        self.pos[0] += self.speed * dt
        # Reset wave with new random attributes when it reaches shore
        if self.pos[0] + self.width > 0.7:
            self.reset_position()
            
    def collides_with_player(self, player_x, player_y):
        # Check if player is within wave bounds
        return (self.pos[0] - self.width/2 <= player_x <= self.pos[0] + self.width/2)

def main():
    width, height = 800, 800
    wm = WindowManager(width, height, "Player Movement with Lily Pad Collision")

    imgui.create_context()
    imgui_impl = PygameRenderer()
    
    io = imgui.get_io()
    io.display_size = width, height
    io.font_global_scale = 1.0
    
    style = imgui.get_style()
    style.colors[imgui.COLOR_WINDOW_BACKGROUND] = (0.1, 0.1, 0.1, 0.9)
    style.colors[imgui.COLOR_TEXT] = (1.0, 1.0, 1.0, 1.0)

    vertex_shader_source = load_shader_source("assets/shaders/default.vert")
    fragment_shader_source = load_shader_source("assets/shaders/default.frag")
    shader_program = Shader(vertex_shader_source, fragment_shader_source)

    modelLoc = glGetUniformLocation(shader_program.ID, "model")

    # Create environment objects.
    left_grass_vertices, left_grass_indices = create_rect(-1.0, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    left_grass_vao, left_grass_count = create_object(left_grass_vertices, left_grass_indices)

    river_vertices, river_indices = create_rect(-0.7, -1.0, 1.4, 2.0, [0.0, 0.0, 0.7])
    river_vao, river_count = create_object(river_vertices, river_indices)

    right_grass_vertices, right_grass_indices = create_rect(0.7, -1.0, 0.3, 2.0, [0.0, 0.8, 0.0])
    right_grass_vao, right_grass_count = create_object(right_grass_vertices, right_grass_indices)

    # Spawn lily pads at fixed y positions.
    fixed_y_positions = [-0.1, 0.15, -0.25, 0.3, -0.4, 0.45]
    # fixed_y_positions = [-0.3]
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
    
    key_size = 0.03
    key_color = [1.0, 1.0, 0.0]  # Yellow
    selected_lily_pads = random.sample(lily_pads, 3)  # Select 3 random lily pads
    
    keys = []
    for lily_pad in selected_lily_pads:
        key_vertices, key_indices = create_square([0, 0, 0], key_size, key_color)
        key_vao, key_count = create_object(key_vertices, key_indices)
        keys.append({
            'vao': key_vao,
            'count': key_count,
            'lily_pad': lily_pad,
            'collected': False
        })
        
    waves = [
        Wave(-0.7 + i * 0.4, 
                random.uniform(0.05, 0.1),
             [0.0, 0.0, 1.0],
             random.uniform(0.1,0.3),
             2.5)  # Spread waves across river
        for i in range(2)
    ]
    
    game_messages = []
    message_duration = 3.0  # Messages stay for 3 seconds
    current_message_time = 0.0

    def show_message(message):
        game_messages.append(message)
        if len(game_messages) > 5:  # Keep only last 5 messages
            game_messages.pop(0)

    # Player variables.
    player_pos = [-0.8, 0.0, 0.0]
    player_radius = 0.05
    player_vertices, player_indices = create_circle([0, 0, 0], player_radius, [1.0, 0.5, 0.0], points=30)
    player_vao, player_count = create_object(player_vertices, player_indices)

    speed = 0.8  # Normal movement speed.
    jump_duration = 30  # Frames.
    jump_height = 0.3  # Maximum jump offset.
    jump_time = 0
    is_jumping = False

    clock = pygame.time.Clock()
    running = True
    
    shadow_vertices, shadow_indices = create_circle([0, 0, 0], 0.05, [0.2, 0.2, 0.2], points=30)
    shadow_vao, shadow_count = create_object(shadow_vertices, shadow_indices)
    
    lives = 3
    health = 100
    health_cooldown = 0
    blink_interval = 0.05 # Blink every 0.2 seconds
    blink_timer = 0
    player_visible = True    

    while running:
        dt = clock.tick(60) / 1000.0
        running = wm.process_events(lambda event: None)
        
        io = imgui.get_io()
        io.display_size = width, height

        keyboard = pygame.key.get_pressed()

        # Use reduced speed when jumping.
        movement_speed = speed * 0.5 if is_jumping else speed

        # Horizontal movement (WASD).
        if keyboard[pygame.K_a]:
            player_pos[0] -= movement_speed * dt
        if keyboard[pygame.K_d]:
            player_pos[0] += movement_speed * dt
        if keyboard[pygame.K_w]:
            player_pos[1] += movement_speed * dt
        if keyboard[pygame.K_s]:
            player_pos[1] -= movement_speed * dt

        # Jump logic.
        if keyboard[pygame.K_SPACE] and not is_jumping:
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
            
        if health_cooldown > 0:
            health_cooldown -= dt
            blink_timer += dt
            if blink_timer >= blink_interval:
                player_visible = not player_visible
                blink_timer = 0
        else:
            player_visible = True
            


        # Keep player within bounds.
        player_pos[0] = max(-1.0, min(1.0, player_pos[0]))
        player_pos[1] = max(-1.0, min(1.0, player_pos[1]))

        effective_y = player_pos[1] + jump_offset
        
        for wave in waves:
            wave.update(dt)
            if wave.collides_with_player(player_pos[0], effective_y) and health_cooldown <= 0:
                health -= 5
                health_cooldown = 0.5  # 1 second cooldown
                print(f"Hit by wave! Health: {health}")
                if health <= 0:
                    lives -= 1
                    if lives == 0:
                        print("Game Over! Player ran out of health!")
                        wm.quit()
                        sys.exit()
                    else:
                        print(f"Player ran out of health! Remaining lives: {lives}")
                        player_pos = [-0.8, 0.0, 0.0]
                        health = 100

        if -0.7 <= player_pos[0] <= 0.7:  
            on_lily_pad = False
            for lily_pad in lily_pads:
                distance = np.sqrt((player_pos[0] - lily_pad.pos[0])**2 + (effective_y - lily_pad.pos[1]*2)**2)
                if distance < 0.15:
                    on_lily_pad = True
                    for key in keys:
                        if not key['collected'] and key['lily_pad'] == lily_pad:
                            if distance < 0.1:  # Smaller radius for key collection
                                key['collected'] = True
                                show_message("Key collected!")
                    break

            if not on_lily_pad and not is_jumping:
                lives-=1
                if(lives == 0):
                    print("Game Over! Player fell into the river.")
                    wm.quit()
                    sys.exit()
                else:
                    print(f"Player fell into the river! Remaining lives: {lives}")
                    player_pos = [-0.8, 0.0, 0.0]

        if player_pos[0] > 0.7:
            all_keys_collected = all(key['collected'] for key in keys)
            if all_keys_collected:
                print("You Won! Player reached the other side with all keys!")
                wm.quit()
                sys.exit()
            else:
                # Push player back if trying to win without all keys
                player_pos[0] = min(0.75, player_pos[0])
                show_message("Collect all keys before crossing!")
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

        for wave in waves:
            wave_model = translation_matrix(wave.pos[0], wave.pos[1], wave.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, wave_model)
            glBindVertexArray(wave.vao)
            glDrawElements(GL_TRIANGLES, wave.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)    
        for lily_pad in lily_pads:
            model = translation_matrix(lily_pad.pos[0], lily_pad.pos[1], lily_pad.pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(lily_pad.vao)
            glDrawElements(GL_TRIANGLES, lily_pad.count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
            
        for key in keys:
            if not key.get('collected', False):
                # Position key slightly above its lily pad
                key_pos = key['lily_pad'].pos
                key_model = translation_matrix(key_pos[0], key_pos[1]*2, key_pos[2])
                glUniformMatrix4fv(modelLoc, 1, GL_TRUE, key_model)
                glBindVertexArray(key['vao'])
                glDrawElements(GL_TRIANGLES, key['count'], GL_UNSIGNED_INT, None)
                glBindVertexArray(0)    
                

        shadow_scale = max(0.3, 1.0 - jump_offset/jump_height)
        shadow_model = np.array([
            [shadow_scale, 0, 0, player_pos[0]],
            [0, shadow_scale, 0, player_pos[1] - 0.01],  # Slightly below player
            [0, 0, 1, player_pos[2]],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
        if player_visible:
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, shadow_model)
            glBindVertexArray(shadow_vao)
            glDrawElements(GL_TRIANGLES, shadow_count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

            model = translation_matrix(player_pos[0], effective_y, player_pos[2])
            glUniformMatrix4fv(modelLoc, 1, GL_TRUE, model)
            glBindVertexArray(player_vao)
            glDrawElements(GL_TRIANGLES, player_count, GL_UNSIGNED_INT, None)
            glBindVertexArray(0)

        # imgui.new_frame()
        
        imgui.set_next_window_position(10, 10)
        imgui.set_next_window_size(200, 100)
        imgui.begin("Game Stats", True, imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE)
        
        # Display lives and health
        imgui.text(f"Lives: {'❤' * lives}")
        imgui.text(f"Health: {health}%")
        
        # Display collected keys count
        keys_collected = sum(1 for key in keys if key['collected'])
        imgui.text(f"Keys: {keys_collected}/3")
        
        imgui.end()
        
        # Game messages window
        if len(game_messages) > 0:
            imgui.set_next_window_position(width/2 - 100, 10, imgui.ONCE)
            imgui.set_next_window_size(200, 60, imgui.ONCE)
            imgui.begin("Messages", True)
            imgui.text(game_messages[-1])  # Show most recent message
            imgui.end()
        
        # Render ImGui
        imgui.render()
        imgui_impl.render(imgui.get_draw_data())
        wm.swap_buffers()

    imgui_impl.shutdown()
    imgui.destroy_context()
    shader_program.delete()
    wm.quit()
    sys.exit()

if __name__ == "__main__":
    main()
