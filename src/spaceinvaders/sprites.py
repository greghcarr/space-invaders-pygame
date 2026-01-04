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
        # Load the spritesheet image
        try:
            self.sheet = pygame.image.load(spritesheet_filename).convert_alpha()  # Use convert_alpha() for transparency
        except pygame.error as e:
            print(f"Unable to load spritesheet image: {spritesheet_filename}")
            raise e
        
        # Load the spritemap JSON
        try:
            self.map = json.load(open(spritemap_filename))
        except json.decoder.JSONDecodeError as e:
            print(f"Unable to load spritemap: {spritemap_filename}")
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
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(groups)
        # we were given an array of images for animation
        # if this Sprite has no animation, the array has a single image
        self.images = images
        
        # colorize the images based on the color we were provided
        self.images = colorize_surfaces(self.images, color)
        
        # initialize animation frame
        self.image_frame = 0
        # set current image to corresponding frame image
        self.image = self.images[self.image_frame]
        
        # set mask for collision
        self.mask = pygame.mask.from_surface(self.image)
        
        # set rect to image
        self.rect = self.image.get_rect()
        
        # initial rect positioning
        self.rect.center = (x_pos, y_pos)
        
        # initialize pos field
        self.pos = Vector2(x_pos, y_pos)
        
        # ----- TO MOVE AN OBJECT, CHANGE should_move AND direction -----
        self.should_move = False
        self.direction = None
        
        # ----- THE TWO VARIABLES BELOW, speed AND vel, SHOULD NOT BE CHANGED BY ANTHING OTHER THAN UPDATE() -----
        # speed is not used to calculate current movement
        # speed is the speed of the Sprite WHEN it's moving
        # speed is set when the Sprite is initialized, and probably not changed
        # it is internally used (in combination with dt) to set vel to move the Sprite
        self.speed = speed
        
        # velocity is an internal field used to compute distance traveled each frame if should_move=True
        self.vel = Vector2(0, 0)
        
    def start_moving(self, direction: Direction):
        self.should_move = True
        self.direction = direction
        
    def stop_moving(self):
        self.should_move = False
        self.direction = None

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
        self.score_for_kill = 0
        self.ms_since_move = 0
        self.move_time_threshold = 1000

    def shift_down(self):
        self.pos.y += 1.5
        
    def update(self, dt, ms_elapsed_since_start):
        # enemies use a time-based stepwise movement
        # if it has been over 1000 ms (value assigned to move_time_threshold)
        if self.ms_since_move >= self.move_time_threshold:
            # set up a move on this frame
            self.should_move = True
            # shift to the next frame of the Sprite's array
            self.animate()
            # reset the time since move, because we're about to move
            self.ms_since_move = 0
        # ms_since_move has not accumulated to 1000 (value assigned to move_time_threshold) or more
        else:
            # don't move
            self.should_move = False
            # add the elapsed time in the last frame to the ms_since_move
            self.ms_since_move += dt * 1000
            
        # call super update after all this
        super().update(dt, ms_elapsed_since_start)
        
class ConeheadEnemySprite(EnemySprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.score_for_kill = 30
        
class AntennaEnemySprite(EnemySprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.score_for_kill = 20
        
class EarsEnemySprite(EnemySprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.score_for_kill = 10
        

        