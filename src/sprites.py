# sprites.py
import pygame

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, spritesheet):
        super().__init__()
        self.frames = load_frames(spritesheet, rows=…)
        self.image = self.frames['idle'][0]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.anim_timer = 0

    def update(self, dt, keys_pressed):
        dx = dy = 0
        if keys_pressed[pygame.K_a]: dx = -1
        …  # handle movement
        self.rect.x += dx * speed * dt
        # switch animation set based on state: 'walk', 'mine', 'idle'
        self.animate(dt)

    def animate(self, dt):
        self.anim_timer += dt
        # pick correct frame list and loop…
