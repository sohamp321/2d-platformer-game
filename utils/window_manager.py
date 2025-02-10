# import pygame
# from pygame.locals import DOUBLEBUF, OPENGL, QUIT

# class WindowManager:
#     def __init__(self, width, height, title="Game"):
#         pygame.init()
#         self.width = width
#         self.height = height
#         self.screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
#         pygame.display.set_caption(title)
    
#     def process_events(self, event_handler):
#         """
#         Processes all pygame events.
#         Calls the provided event_handler for each event.
#         Returns False if a QUIT event is encountered; otherwise, True.
#         """
#         for event in pygame.event.get():
#             if event.type == QUIT:
#                 return False
#             event_handler(event)
#         # Ensure pygame updates key states.
#         pygame.event.pump()
#         return True

#     def swap_buffers(self):
#         pygame.display.flip()
    
#     def quit(self):
#         pygame.quit()


import pygame
from pygame.locals import DOUBLEBUF, OPENGL, QUIT

class WindowManager:
    def __init__(self, width, height, title="Game"):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption(title)
    
    def process_events(self, event_handler):
        """
        Processes all pygame events and calls the provided event_handler for each event.
        Returns False if a QUIT event is encountered; otherwise, True.
        """
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            event_handler(event)
        # Update internal event state.
        pygame.event.pump()
        return True

    def swap_buffers(self):
        pygame.display.flip()
    
    def quit(self):
        pygame.quit()
        

