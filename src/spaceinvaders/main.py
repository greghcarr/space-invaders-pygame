import json
from enum import Enum

import pygame
from pygame.sprite import Sprite

from spaceinvaders.helpers import Direction
from spaceinvaders.sprites import SpriteSheet, SpaceInvadersSprite, PlayerSprite, BarrierSprite, PlayerBulletSprite, \
    EnemySprite, ConeheadEnemySprite, AntennaEnemySprite, EarsEnemySprite

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
SCORE_FONT_PATH = 'res/fonts/space-invaders.otf'

# colors
SCORE_COLOR = (255, 255, 255)

class SpaceInvaders:    
    def __init__(self):
        # initialize pygame
        pygame.init()
        self.game_is_over = False
        
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
        # window title
        pygame.display.set_caption('Space Invaders')
        
        # set up clock-related stuff
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0
        self.ms_elapsed_since_start = 0
        
        # ----- SPRITE STUFF -----
        # sprite sheet
        self.sprite_sheet = SpriteSheet(
            SPRITESHEET_PATH, 
            SPRITEMAP_PATH
        )
        
        # sprite groups
        self.all_sprites = pygame.sprite.Group()
        self.player_sprite = None
        self.left_wall_sprite = None
        self.right_wall_sprite = None
        self.wall_sprites = pygame.sprite.Group()
        self.player_bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()

        # load up the data about the game entities (player, enemy, bullet, barrier, etc.
        data = json.load(open(ENTITYINFO_PATH))
        self.entity_dict = data
        for k in self.entity_dict.keys():
            # data cleanup
            # convert the color from list (JSON compatible) to tuple (Python)
            self.entity_dict[k][COLOR_TAG] = tuple(self.entity_dict[k][COLOR_TAG])
            # create images in dict based on image_indexes
            self.entity_dict[k][IMAGES_TAG] = [self.sprite_sheet.get_image_by_num(int(i)) for i in self.entity_dict[k][IMAGE_INDEXES_TAG]]
            # image indexes no longer relevant
            self.entity_dict[k].pop(IMAGE_INDEXES_TAG)
        
        # reset and create sprites
        self.setup_new_game_sprites()
        
        # ----- GAME VARIABLE STUFF -----
        # initialize the score variable
        self.score_player = 0
        
        # ----- TEXT STUFF -----
        # set up the font
        self.TEXT_ANTIALIASING = False
        self.score_font = pygame.font.Font(SCORE_FONT_PATH, 8)

        # set the positions for the score, score label
        self.score_label_surface_pos = (self.screen.width // 5, self.screen.height // 20)
        self.score_value_surface_pos = (self.screen.width // 5, self.screen.height // 10)
        self.gameover_surface_pos = (self.screen.width // 2, self.screen.height // 4)
        
        # initialize the scoreboard objects
        # label "SCORE P1"
        self.score_label_surface = self.score_font.render('SCORE P1', self.TEXT_ANTIALIASING, SCORE_COLOR)
        self.score_label_rect = self.score_label_surface.get_rect()
        self.score_label_rect.center = self.score_label_surface_pos
        # score number
        self.score_value_surface, self.score_value_rect = None, None
        self._update_score_surface()
        
        # initialize game over text
        self.gameover_surface = self.score_font.render('GAME OVER', self.TEXT_ANTIALIASING, SCORE_COLOR)
        self.gameover_rect = self.gameover_surface.get_rect()
        self.gameover_rect.center = self.gameover_surface_pos
        
        # kick off the main loop
        self.game_loop()
        
    def draw_game_over(self):
        self.screen.blit(self.gameover_surface, self.gameover_rect)
        
    def add_to_score(self, num):
        self.score_player += num
        self._update_score_surface()
        
    def _update_score_surface(self):
        self.score_value_surface = self.score_font.render(f'{self.score_player:08d}', self.TEXT_ANTIALIASING,
                                                          SCORE_COLOR)
        self.score_value_rect = self.score_value_surface.get_rect()
        self.score_value_rect.center = self.score_value_surface_pos
        
    def draw_score(self):
        # draw the score label "SCORE P1"
        self.screen.blit(self.score_label_surface, self.score_label_rect)
        # draw the numeric score
        self.screen.blit(self.score_value_surface, self.score_value_rect)
        
    def setup_new_game_sprites(self):
        # ----- newgame sprite creation -----
        
        # create the side walls for the enemies to bounce off
        self.left_wall_sprite = Sprite(self.wall_sprites, self.all_sprites)
        self.right_wall_sprite = Sprite(self.wall_sprites, self.all_sprites)
        for wall in self.wall_sprites.sprites():
            wall.image = pygame.Surface([100, self.WINDOW_HEIGHT])
            wall.image.fill((0, 0, 0))
            wall.rect = wall.image.get_rect()
        # put the right edge of the left wall on the left edge of the screen
        self.left_wall_sprite.rect.right = 0
        # put the left edge of the right wall on the right edge of the screen
        self.right_wall_sprite.rect.left = self.screen.get_width()
        
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
            
        # create five rows of enemy sprites
        y_initial = 60
        y_increment = 16
        x_increment = self.screen.get_width() // 14
        enemy_sprites = {
            ENEMY_CONEHEAD_TAG: ConeheadEnemySprite,
            ENEMY_ANTENNA_TAG: AntennaEnemySprite,
            ENEMY_EARS_TAG: EarsEnemySprite,
        }
        for row in range(5):
            # 1st enemy row - Conehead
            if row == 0: enemy_name = ENEMY_CONEHEAD_TAG
            # 2nd and 3rd enemy rows - Antenna
            elif row == 1 or row == 2: enemy_name = ENEMY_ANTENNA_TAG
            # 4th and 5th enemy rows - Ears
            # elif row == 3 or row == 4: enemy = ENEMY_EARS_TAG
            else: enemy_name = ENEMY_EARS_TAG
            for x in range(2 * x_increment, 13 * x_increment, x_increment):
                enemy_sprites[enemy_name](
                    images = self.entity_dict[enemy_name][IMAGES_TAG],
                    color = self.entity_dict[enemy_name][COLOR_TAG],
                    speed = self.entity_dict[enemy_name][SPEED_TAG],
                    x_pos = x, 
                    y_pos = y_initial + (row * y_increment),
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
            
    def _check_enemy_bullet_collision(self):
        enemies_shot = pygame.sprite.groupcollide(self.player_bullet_sprites, self.enemy_sprites, True, True,
                                                collided=pygame.sprite.collide_mask)
        if enemies_shot:
            print(enemies_shot)
            print(enemies_shot.keys())
            # {<PlayerBulletSprite Sprite(in 0 groups)>: [<EnemySprite Sprite(in 0 groups)>]}
            # find the value to add to the score and add it
            for enemies in enemies_shot.values():
                for enemy in enemies:
                    self.add_to_score(enemy.score_for_kill)
                
            # speed up each enemy by setting their "time per move" proportional to the number of enemies left
            # fewer enemies = lower threshold = more moves per time
            for enemy in self.enemy_sprites.sprites():
                enemy.move_time_threshold = len(self.enemy_sprites.sprites()) * 20
                
    def _check_enemy_wall_collision(self):
        # see if the enemies have reached the edge
        if len(self.enemy_sprites) > 0:
            ms_since_move_threshold = 100
            for wall, direction in [
                (self.left_wall_sprite, Direction.RIGHT), 
                (self.right_wall_sprite, Direction.LEFT)]:
                # if an enemy has collided with a wall AND
                # if the top left Sprite (or the first one in the enemy_sprites array if the top left has been destroyed)
                # has moved very recently
                # the second 'if' statement exists because we need to make sure all of the enemies have moved
                # toward the wall before reversing them all
                if pygame.sprite.spritecollide(wall, self.enemy_sprites, False) and \
                        self.enemy_sprites.sprites()[0].ms_since_move < ms_since_move_threshold:
                    for sprite in self.enemy_sprites:
                        sprite.shift_down()
                        sprite.direction = direction
                        
    def _check_enemy_player_collision(self):
        if len(self.enemy_sprites) > 0:
            if pygame.sprite.spritecollide(self.player_sprite, self.enemy_sprites, False):
                self.game_is_over = True
        
    def check_collisions(self):
        self._check_enemy_bullet_collision()
        self._check_enemy_wall_collision()
        self._check_enemy_player_collision()
        
    def handle_input(self):
        # poll for pressed keys during this frame
        keys = pygame.key.get_pressed()
        # check A, D, Left Arrow, Right Arrow
        for k_letter, k_arrow, direction in [
            (keys[pygame.K_a], keys[pygame.K_LEFT], Direction.LEFT), 
            (keys[pygame.K_d], keys[pygame.K_RIGHT], Direction.RIGHT),]:
            if k_letter or k_arrow:
                if not self.player_sprite.is_at_edge(self.screen, direction):
                    self.player_sprite.start_moving(direction)
                else:
                    self.player_sprite.stop_moving()
                break           
        # Neither A nor D nor Left nor Right is pressed
        else:
            self.player_sprite.should_move = False
            self.player_sprite.direction = None
            
        # Spacebar - shoot
        if keys[pygame.K_SPACE]:
            self.player_shoot()
        # Escape - quit
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
            self.check_collisions()

            # call every sprite's update() if the game's not over
            if not self.game_is_over: self.all_sprites.update(self.dt, self.ms_elapsed_since_start)

            # fill the screen with a color to wipe away anything from last frame
            self.screen.fill("black")
            
            # if the game's over, draw GAME OVER
            if self.game_is_over: self.draw_game_over()
            
            # draw the score label and score
            self.draw_score()

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