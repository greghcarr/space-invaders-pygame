import json
from typing import List

import pygame
from pygame import Vector2

from spaceinvaders.helpers import Direction


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

        self.initial_color = color

        # colorize the images based on the color we were provided
        self.images = colorize_surfaces(self.images, color)

        # initialize animation frame
        self.image_frame = 0
        # set current image to corresponding frame image
        self.image = self.images[self.image_frame]

        # if this is an animated sprite, these will be set later
        self.animation_interval_ms: int
        self.elapsed_since_animation_ms: int

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

    # this method is used for the PlayerSprite but could be useful in the future
    # it differs from the wall collision checking
    def is_at_edge(self, screen: pygame.Surface, direction: Direction):
        match direction:
            case Direction.UP:
                return self.rect.top <= 0
            case Direction.LEFT:
                return self.rect.left <= 0
            case Direction.DOWN:
                return self.rect.bottom >= screen.get_height()
            case Direction.RIGHT:
                return self.rect.right >= screen.get_width()

    def animate(self):
        self.image_frame = (self.image_frame + 1) % len(self.images)
        self.image = self.images[self.image_frame]
        
    def set_position(self, pos):
        self.pos.x, self.pos.y = pos
        self.rect.center = round(self.pos.x), round(self.pos.y)

    def update(self, dt_ms, ms_elapsed_since_start):
        # update velocity to equal speed depending on direction of movement
        for direction, axis, sign in zip((Direction.LEFT, Direction.RIGHT, Direction.UP, Direction.DOWN),
                                         ('x', 'x', 'y', 'y'),
                                         (-1, 1, -1, 1)):
            if self.direction == direction:
                setattr(self.vel, axis, sign * self.speed)
                break
        else:
            # if self.direction is None:
            self.vel.x, self.vel.y = 0, 0

        # update the pos field, only time dt should be used
        if self.should_move:
            self.pos += self.vel * (dt_ms / 1000)
            self.rect.center = round(self.pos.x), round(self.pos.y)


class BarrierSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.barrier_health = 10
        self.color = self.initial_color

    def reduce_health(self, num):
        self.barrier_health -= num
        self.color = tuple([(c / 10) * self.barrier_health for c in self.initial_color])
        self.image = colorize_surface(self.image, self.color)
        if self.barrier_health <= 0:
            self.kill()


class PlayerSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.time_since_shoot_ms = 0
        self.min_shoot_interval_ms = 500

    def update(self, dt_ms, ms_elapsed_since_start):
        super().update(dt_ms, ms_elapsed_since_start)
        self.time_since_shoot_ms += dt_ms


class PlayerBulletSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.should_move = True
        self.direction = Direction.UP

    def update(self, dt_ms, ms_elapsed_since_start):
        super().update(dt_ms, ms_elapsed_since_start)
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

    def update(self, dt_ms, ms_elapsed_since_start):
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
            self.ms_since_move += dt_ms

        # call super update after all this
        super().update(dt_ms, ms_elapsed_since_start)


class MainGridEnemySprite(EnemySprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, initial_grid_position,
                 groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.initial_grid_position = initial_grid_position
        self.shoot_ms_interval = 1000

    def update(self, dt_ms, ms_elapsed_since_start):
        # call super update after all this
        super().update(dt_ms, ms_elapsed_since_start)


class ConeheadEnemySprite(MainGridEnemySprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, initial_grid_position,
                 groups):
        super().__init__(images, color, speed, x_pos, y_pos, initial_grid_position, groups)
        self.score_for_kill = 30


class AntennaEnemySprite(MainGridEnemySprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, initial_grid_position,
                 groups):
        super().__init__(images, color, speed, x_pos, y_pos, initial_grid_position, groups)
        self.score_for_kill = 20


class EarsEnemySprite(MainGridEnemySprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, initial_grid_position,
                 groups):
        super().__init__(images, color, speed, x_pos, y_pos, initial_grid_position, groups)
        self.score_for_kill = 10


class GridEnemyBulletSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.should_move = True
        self.direction = Direction.DOWN
        self.animation_interval_ms = 50
        self.elapsed_since_animation_ms = 0

    def update(self, dt_ms, ms_elapsed_since_start):
        super().update(dt_ms, ms_elapsed_since_start)
        if self.elapsed_since_animation_ms >= self.animation_interval_ms:
            self.animate()
            self.elapsed_since_animation_ms = 0
        else:
            self.elapsed_since_animation_ms += dt_ms
        if self.rect.top > 256:
            self.kill()
        
      
class ExplosionSprite(SpaceInvadersSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, time_should_exist_ms: int, groups):
        super().__init__(images, color, speed, x_pos, y_pos, groups)
        self.time_since_creation_ms: int = 0
        self.time_should_exist_ms = time_should_exist_ms
        
    def update(self, dt_ms, ms_elapsed_since_start):
        super().update(dt_ms, ms_elapsed_since_start)
        self.time_since_creation_ms += dt_ms
        if self.time_since_creation_ms >= self.time_should_exist_ms:
            self.kill()
            

class PlayerExplosionSprite(ExplosionSprite):
    def __init__(self, images: List[pygame.Surface], color: tuple, speed: int, x_pos, y_pos, time_should_exist_ms: int, groups):
        super().__init__(images, color, speed, x_pos, y_pos, time_should_exist_ms, groups)
        self.animation_interval_ms = 100
        self.elapsed_since_animation_ms = 0
        
    def update(self, dt_ms, ms_elapsed_since_start):
        super().update(dt_ms, ms_elapsed_since_start)
        if self.elapsed_since_animation_ms >= self.animation_interval_ms:
            self.animate()
            self.elapsed_since_animation_ms = 0
        else:
            self.elapsed_since_animation_ms += dt_ms

