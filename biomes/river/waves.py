import random
from assets.objects.objects import create_object, create_rect

class Wave:
    def __init__(self, x, speed, color=[0.0, 0.0, 1.0], width=0.1, height=1.8):
        self.pos = [x, 0.0, 0.0]
        self.speed = speed
        self.width = width
        self.height = height
        vertices, indices = create_rect(0, -1, self.width, self.height, color)
        self.vao, self.count = create_object(vertices, indices)
        
    def reset_position(self, x=None):
        if x is None:
            x = -0.65
        self.pos = [x, 0.0, 0.0]
        self.speed = random.uniform(0.05, 0.2)
        self.width = random.uniform(0.1, 0.2)
        self.height = random.uniform(1.2, 2.0)
        
    def update(self, dt):
        self.pos[0] += self.speed * dt
        if self.pos[0] + self.width > 0.68:
            self.reset_position()
            
    def collides_with_player(self, player_x, player_y):
        return (self.pos[0] - self.width/2 <= player_x <= self.pos[0] + self.width/2)