import json
from enum import Enum

import pygame
from pygame.sprite import Sprite

from spaceinvaders.helpers import Direction
from spaceinvaders.sprites import SpriteSheet, SpaceInvadersSprite, PlayerSprite, BarrierSprite, PlayerBulletSprite, EnemySprite


PLAYER_SHIP_TAG = 'PLAYER_SHIP'
BARRIER_TAG = 'BARRIER'
BULLET_PLAYER_TAG = 'BULLET_PLAYER'
BULLET_ENEMY_TAG = 'BULLET_ENEMY'
ENEMY_CONEHEAD_TAG = 'ENEMY_CONEHEAD'
ENEMY_ANTENNA_TAG = 'ENEMY_ANTENNA'
ENEMY_EARS_TAG = 'ENEMY_EARS'

SPEED_TAG = 'speed'
COLOR_TAG = 'color'
IMAGE_INDEXES_TAG = 'image_indexes'
IMAGES_TAG = 'images'

SPRITESHEET_PATH = 'res/spritesheets/space_invaders.png'
SPRITEMAP_PATH = 'res/spritesheets/space_invaders.json'
ENTITYINFO_PATH = 'res/entity_info.json'

class SpaceInvaders:    
    def __init__(self):
        # initialize pygame
        pygame.init()
        
        # set up window stuff
        self.WINDOW_WIDTH = 224
        self.WINDOW_HEIGHT = 256
        self.FPS = 60
        self.VSYNC_ON = True
        self.screen = pygame.display.set_mode(
            (self.WINDOW_WIDTH, self.WINDOW_HEIGHT),
            pygame.SCALED,
            vsync=self.VSYNC_ON,
        )
        
        # set up clock-related stuff
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0
        self.ms_elapsed_since_start = 0
        
        # set up sprite objects
        self.sprite_sheet = SpriteSheet(
            SPRITESHEET_PATH, 
            SPRITEMAP_PATH
        )
        self.all_sprites = pygame.sprite.Group()
        self.wall_sprites = pygame.sprite.Group()
        self.player_sprite = None
        self.left_wall_sprite = None
        self.right_wall_sprite = None
        self.player_bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()

        data = json.load(open(ENTITYINFO_PATH))
        self.entity_dict = data
        for k in self.entity_dict.keys():
            # convert the color from list (JSON compatible) to tuple (Python)
            self.entity_dict[k][COLOR_TAG] = tuple(self.entity_dict[k][COLOR_TAG])
            self.entity_dict[k][IMAGES_TAG] = [self.sprite_sheet.get_image_by_num(int(i)) for i in self.entity_dict[k][IMAGE_INDEXES_TAG]]
            # image indexes no longer relevant
            self.entity_dict[k].pop(IMAGE_INDEXES_TAG)
        
        # reset and create sprites
        self.setup_new_game()
        
        # kick off the main loop
        self.game_loop()        
        
        
    def setup_new_game(self):
        # ----- newgame sprite creation -----
        # create the left wall
        self.left_wall_sprite = Sprite()
        self.left_wall_sprite.image = pygame.Surface([100, self.WINDOW_HEIGHT])
        self.left_wall_sprite.image.fill((0, 0, 0))
        self.left_wall_sprite.rect = self.left_wall_sprite.image.get_rect()
        # put the right edge of the left wall on the left edge of the screen
        self.left_wall_sprite.rect.right = 0
        self.wall_sprites.add(self.left_wall_sprite)
        self.all_sprites.add(self.left_wall_sprite)

        # create the right wall
        self.right_wall_sprite = Sprite()
        self.right_wall_sprite.image = pygame.Surface([100, self.WINDOW_HEIGHT])
        self.right_wall_sprite.image.fill((0, 0, 0))
        self.right_wall_sprite.rect = self.right_wall_sprite.image.get_rect()
        # put the left edge of the right wall on the right edge of the screen
        self.right_wall_sprite.rect.left = self.screen.get_width()
        self.wall_sprites.add(self.right_wall_sprite)
        self.all_sprites.add(self.right_wall_sprite)
        
        # create the player sprite
        self.player_sprite = PlayerSprite(
            images = self.entity_dict[PLAYER_SHIP_TAG][IMAGES_TAG],
            color = self.entity_dict[PLAYER_SHIP_TAG][COLOR_TAG],
            speed = self.entity_dict[PLAYER_SHIP_TAG][SPEED_TAG],
            x_pos = self.screen.get_width() // 2,
            y_pos = (7 / 4) * self.screen.get_height() // 2,
            groups = (self.all_sprites,))

        # create the barrier sprites
        for x in range(self.screen.get_width() // 5, 4 * self.screen.get_width() // 5, self.screen.get_width() // 5):
            BarrierSprite(
                images = self.entity_dict[BARRIER_TAG][IMAGES_TAG],
                color=self.entity_dict[BARRIER_TAG][COLOR_TAG],
                speed=self.entity_dict[BARRIER_TAG][SPEED_TAG],
                x_pos = x,
                y_pos = 200,
                groups = (self.all_sprites, self.barrier_sprites))
            
        # create top row of enemies
        top_row_y = 60
        y_increment = 16
        x_increment = self.screen.get_width() // 14
        for row in range(6):
            # 1st enemy row - Conehead
            if row == 0: enemy = ENEMY_CONEHEAD_TAG
            # 2nd and 3rd enemy rows - Antenna
            elif 1 <= row <= 2: enemy = ENEMY_ANTENNA_TAG
            # 4th and 5th enemy rows - Ears
            else: enemy = ENEMY_EARS_TAG
            for x in range(2 * x_increment, 13 * x_increment, x_increment):
                EnemySprite(
                    images = self.entity_dict[enemy][IMAGES_TAG],
                    color = self.entity_dict[enemy][COLOR_TAG],
                    speed = self.entity_dict[enemy][SPEED_TAG],
                    x_pos = x, 
                    y_pos = top_row_y + (row * y_increment),
                    groups = (self.all_sprites, self.enemy_sprites))
        
        # DEBUG: create three enemy sprites in the middle of the screen
        # if __debug__:
        #     # print one of each enemy to the middle of the screen
        #     # enemy_image = self.sprite_sheet.get_image_by_num(1)
        #     enemy_sprite = SpaceInvadersSprite(
        #         self.entity_dict['ENEMY_CONEHEAD'],
        #         self.screen.get_width() // 2, 
        #         self.screen.get_height() // 2,
        #     )
        #     self.enemy_sprites.add(enemy_sprite)
        #     self.all_sprites.add(enemy_sprite)
        # 
        #     enemy_sprite = SpaceInvadersSprite(
        #         self.entity_dict['ENEMY_ANTENNA'],
        #         self.screen.get_width() // 4,
        #         self.screen.get_height() // 2,
        #     )
        #     self.enemy_sprites.add(enemy_sprite)
        #     self.all_sprites.add(enemy_sprite)
        # 
        #     enemy_sprite = SpaceInvadersSprite(
        #         self.entity_dict['ENEMY_EARS'],
        #         3 * self.screen.get_width() // 4,
        #         self.screen.get_height() // 2,
        #     )
        #     self.enemy_sprites.add(enemy_sprite)
        #     self.all_sprites.add(enemy_sprite)
           
    def player_shoot(self):
        # if no player bullet exists, create a bullet sprite at the player's location
        if len(self.player_bullet_sprites.sprites()) == 0:
            PlayerBulletSprite(
                images = self.entity_dict[BULLET_PLAYER_TAG][IMAGES_TAG], 
                color = self.entity_dict[BULLET_PLAYER_TAG][COLOR_TAG],
                speed = self.entity_dict[BULLET_PLAYER_TAG][SPEED_TAG],
                x_pos = self.player_sprite.rect.centerx, 
                y_pos = self.player_sprite.rect.centery,
                groups = (self.all_sprites, self.player_bullet_sprites)
            )
        
    def check_collision(self):
        enemy_died = pygame.sprite.groupcollide(self.enemy_sprites, self.player_bullet_sprites, True, True, collided=pygame.sprite.collide_mask)
        if enemy_died:
            for enemy in self.enemy_sprites.sprites():
                enemy.move_time_threshold = len(self.enemy_sprites.sprites()) * 20
        
    def handle_input(self):
        # poll for pressed keys during this frame
        keys = pygame.key.get_pressed()
        # A or Left arrow
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            if not self.player_sprite.is_at_edge(self.screen, Direction.LEFT):
                self.player_sprite.should_move = True
                self.player_sprite.direction = Direction.LEFT
            else:
                self.player_sprite.should_move = False
                self.player_sprite.direction = None
        # D or Right arrow
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            if not self.player_sprite.is_at_edge(self.screen, Direction.RIGHT):
                self.player_sprite.should_move = True
                self.player_sprite.direction = Direction.RIGHT
            else:
                self.player_sprite.should_move = False
                self.player_sprite.direction = None                
        # Neither A nor D nor Left nor Right is pressed
        else:
            self.player_sprite.should_move = False
            self.player_sprite.direction = None
            
        # Spacebar
        if keys[pygame.K_SPACE]:
            self.player_shoot()
        # Escape
        if keys[pygame.K_ESCAPE]:
            self.running = False
            

    def game_loop(self):
        while self.running:
            # poll for events
            for event in pygame.event.get():
                # pygame.QUIT event means the user clicked X to close your window
                if event.type == pygame.QUIT:
                    # cause the gameloop to end
                    self.running = False
                    
            # check for collisions
            self.check_collision()
            
            # see if the enemies have reached the edge
            if len(self.enemy_sprites) > 0:
                if pygame.sprite.spritecollide(self.left_wall_sprite, self.enemy_sprites, False) and self.enemy_sprites.sprites()[0].ms_since_move < 100:
                    for sprite in self.enemy_sprites:
                        sprite.shift_down()
                        sprite.direction = sprite.direction.RIGHT
                if pygame.sprite.spritecollide(self.right_wall_sprite, self.enemy_sprites, False) and self.enemy_sprites.sprites()[0].ms_since_move < 100:
                    for sprite in self.enemy_sprites:
                        sprite.shift_down()
                        sprite.direction = sprite.direction.LEFT

            # call every sprite's update()
            self.all_sprites.update(self.dt, self.ms_elapsed_since_start)

            # fill the screen with a color to wipe away anything from last frame
            self.screen.fill("black")

            # draw all the sprites
            self.all_sprites.draw(self.screen)

            # handle the keyboard and mouse input
            self.handle_input()

            # flip() the display to put your work on screen
            pygame.display.flip()

            # limits FPS to 60
            # dt is delta time in seconds since last frame, used for framerate-
            # independent physics.
            ms_elapsed = self.clock.tick(self.FPS)
            self.dt = ms_elapsed / 1000
            self.ms_elapsed_since_start += ms_elapsed

        pygame.quit()


if __name__ == '__main__':
    game = SpaceInvaders()
