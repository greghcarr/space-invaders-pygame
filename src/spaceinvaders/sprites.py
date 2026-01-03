import json
from enum import Enum, auto
from typing import List
from unittest import case

import pygame
from pygame import Vector2

from spaceinvaders.helpers import Direction

# SPACE_INVADER_GREEN = (32, 255, 32)


class SpriteSheet:
    def __init__(self, spritesheet_filename, spritemap_filename):
        """Load the sprite sheet image and the map JSON."""
        try:
            self.sheet = pygame.image.load(spritesheet_filename).convert_alpha()  # Use convert_alpha() for transparency
        except pygame.error as e:
            print(f"Unable to load spritesheet image: {spritesheet_filename}")
            raise e
        try:
            self.map = json.load(open(spritemap_filename))
        except json.decoder.JSONDecodeError as e:
            print(f"Unable to load map: {spritemap_filename}")
            raise e

    def get_image_by_num(self, num: int):
        # if user provides "1" for sprite1, that is index 0 on the map, get the dict
        sprite_meta = self.map[num - 1]
        return self._get_image_by_pos(
            sprite_meta['x'],
            sprite_meta['y'],
            sprite_meta['width'],
            sprite_meta['height'],
        )

    def _get_image_by_pos(self, x, y, width, height):
        """Should not be called directly. Use get_image_by_num method.
        
        Extract a single image from the sheet."""
        # Create a new blank surface for the individual sprite
        image = pygame.Surface([width, height], pygame.SRCALPHA).convert_alpha()
        image.set_colorkey((0, 0, 0))
        # Copy the desired portion of the large sheet onto the new surface
        image.blit(self.sheet, (0, 0), (x, y, width, height))

        # Return the extracted image
        return image


# Example usage in a game:
# ss = SpriteSheet("my_spritesheet.png")
# player_idle_frame_1 = ss.get_image(0, 0, 32, 32) # Get the sprite at (0,0) with size 32x32

def colorize_surface(image, new_color):
    image = image.copy()
    # Zero out RGB values, preserving alpha
    image.fill((0, 0, 0, 255), None, pygame.BLEND_RGBA_MULT)
    # Add in the new RGB values
    image.fill(new_color + (0,), None, pygame.BLEND_RGBA_ADD)
    return image

def colorize_surfaces(images, new_color):
    images_edited = [colorize_surface(image, new_color) for image in images]
    return images_edited

class SpaceInvadersSprite(pygame.sprite.Sprite):
    def __init__(
            self, 
            images: List[pygame.Surface], 
            color: tuple, 
            speed: int, 
            x_pos, 
            y_pos, 
            groups):
        super().__init__(groups)
        # placeholder: using only one image right now
        self.images = images
        self.images = colorize_surfaces(self.images, color)
        self.image_frame = 0
        self.image = self.images[self.image_frame]
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.rect.center = (x_pos, y_pos)
        self.pos = Vector2(x_pos, y_pos)
        self.vel = Vector2(0, 0)
        self.speed = speed
        self.direction = None
        self.should_move = False

    def is_at_edge(self, screen: pygame.Surface, direction: Direction):
        match direction:
            case Direction.LEFT:
                return self.rect.left <= 0
            case Direction.RIGHT:
                return self.rect.right >= screen.get_width()
            case Direction.UP:
                return self.rect.top <= 0
            case Direction.DOWN:
                return self.rect.bottom >= screen.get_height()
        return False
    
    def animate(self):
        self.image_frame = (self.image_frame + 1) % len(self.images)
        self.image = self.images[self.image_frame]
            
    def update(self, dt, ms_elapsed_since_start):
        # update velocity to equal speed depending on direction of movement
        if self.direction == Direction.LEFT:
            self.vel.x = -self.speed
        elif self.direction == Direction.RIGHT:
            self.vel.x = self.speed
        elif self.direction == Direction.UP:
            self.vel.y = -self.speed
        elif self.direction == Direction.DOWN:
            self.vel.y = self.speed
        elif self.direction is None:
            self.vel.x, self.vel.y = 0, 0
        
        # update the pos field, only time dt should be used
        if self.should_move:
            self.pos += self.vel * dt
            self.rect.center = round(self.pos.x), round(self.pos.y)
            
            
class PlayerSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)

    def update(self, dt, ms_elapsed_since_start):
        super().update(dt, ms_elapsed_since_start)
        
        
class BarrierSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        
        
class PlayerBulletSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.should_move = True
        self.direction = Direction.UP
        
    def update(self, dt, ms_elapsed_since_start):
        super().update(dt, ms_elapsed_since_start)
        if self.rect.bottom < 0:
            self.kill()
            
        
class EnemySprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.direction = Direction.RIGHT
        self.ms_since_move = 0
        self.move_time_threshold = 1000

    def shift_down(self):
        self.pos.y += 1
        
    def update(self, dt, ms_elapsed_since_start):
        super().update(dt, ms_elapsed_since_start)
        if self.ms_since_move >= self.move_time_threshold:
            self.should_move = True
            self.animate()
            self.ms_since_move = 0
        else:
            self.should_move = False
            self.ms_since_move += dt * 1000
        