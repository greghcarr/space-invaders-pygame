import functools
import json
import random

import pygame
from pygame.sprite import Sprite

from spaceinvaders.helpers import Direction
from spaceinvaders.sprites import SpriteSheet, PlayerSprite, BarrierSprite, PlayerBulletSprite, \
    EnemySprite, ConeheadEnemySprite, AntennaEnemySprite, EarsEnemySprite, GridEnemyBulletSprite, ExplosionSprite, \
    PlayerExplosionSprite

# name tags used in entity_info.json and entity_info within the program
PLAYER_SHIP_TAG = 'PLAYER_SHIP'
BARRIER_TAG = 'BARRIER'
BULLET_PLAYER_TAG = 'BULLET_PLAYER'
BULLET_GRID_ENEMY_1_TAG = 'BULLET_GRID_ENEMY_1'
BULLET_GRID_ENEMY_2_TAG = 'BULLET_GRID_ENEMY_2'
BULLET_GRID_ENEMY_3_TAG = 'BULLET_GRID_ENEMY_3'
ENEMY_CONEHEAD_TAG = 'ENEMY_CONEHEAD'
ENEMY_ANTENNA_TAG = 'ENEMY_ANTENNA'
ENEMY_EARS_TAG = 'ENEMY_EARS'
EXPLOSION_PLAYER_TAG = 'EXPLOSION_PLAYER'
EXPLOSION_GRID_ENEMY_TAG = 'EXPLOSION_GRID_ENEMY'
EXPLOSION_BULLET_PLAYER_TAG = "EXPLOSION_BULLET_PLAYER"
EXPLOSION_BULLET_ENEMY_TAG = "EXPLOSION_BULLET_ENEMY"
# attribute tags
SPEED_TAG = 'speed'
COLOR_TAG = 'color'
IMAGE_INDEXES_TAG = 'image_indexes'
IMAGES_TAG = 'images'

# important filepaths
SPRITESHEET_PATH = 'res/spritesheets/space_invaders.png'
SPRITEMAP_PATH = 'res/spritesheets/space_invaders.json'
ENTITYINFO_PATH = 'res/entity_info.json'
SCORE_FONT_PATH = 'res/fonts/space-invaders.otf'

# colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (222, 58, 53)
GREEN = (32, 255, 32)
BG_COLOR = BLACK
FG_COLOR = WHITE

EXPLOSION_LENGTH_MS = 300
PLAYER_EXPLOSION_LENGTH_MS = 1000

PLAYER_STARTING_POS = (15, 212)
STARTING_LIVES = 3
MAX_EXTRA_LIVES = 4


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
        self.dt_ms = 0
        self.ms_elapsed_since_start = 0

        # ----- SPRITE STUFF -----
        # rows and columns of enemies
        self.enemy_rows = 5
        self.enemy_columns = 11

        # sprite sheet
        self.sprite_sheet = SpriteSheet(
            SPRITESHEET_PATH,
            SPRITEMAP_PATH
        )

        # sprite groups
        self.all_sprites = pygame.sprite.Group()
        self.current_player_sprite = None
        self.extra_player_sprites = pygame.sprite.Group()
        self.left_wall_sprite = None
        self.right_wall_sprite = None
        self.top_wall_sprite = None
        self.bottom_wall_sprite = None
        self.wall_sprites = pygame.sprite.Group()
        self.player_bullet_sprites = pygame.sprite.Group()
        self.enemy_bullet_sprites = pygame.sprite.Group()
        self.grid_enemy_sprites = pygame.sprite.Group()
        self.grid_enemy_sprites_columns = [pygame.sprite.Group() for _ in range(self.enemy_columns)]
        self.all_enemy_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()

        # load up the data about the game entities (player, enemy, bullet, barrier, etc.
        data = json.load(open(ENTITYINFO_PATH))
        self.entity_info = data
        for k in self.entity_info.keys():
            # data cleanup
            # convert the color from list (JSON compatible) to tuple (Python)
            self.entity_info[k][COLOR_TAG] = tuple(self.entity_info[k][COLOR_TAG])
            # create images in dict based on image_indexes
            self.entity_info[k][IMAGES_TAG] = [self.sprite_sheet.get_image_by_num(int(i)) for i in
                                               self.entity_info[k][IMAGE_INDEXES_TAG]]
            # image indexes no longer relevant
            self.entity_info[k].pop(IMAGE_INDEXES_TAG)

        # reset and create sprites
        self.setup_new_game_sprites()

        # ----- GAME VARIABLE STUFF -----
        # set the interval for main grid enemy shooting
        self.time_since_enemy_shoot_ms = 0
        # set the intial interval, but we're going to alter it to make it a bit more random
        self.base_enemy_shoot_interval_ms = 1000
        # set the initial interval for time gap between enemy shots to the base value
        self.enemy_shoot_interval_ms = self.base_enemy_shoot_interval_ms
        
        # variable for seeing if the game should be frozen after a player death
        self.pause_time_after_player_death_ms = 2000
        self.time_since_player_death_ms = self.pause_time_after_player_death_ms
        
        # number of grid clears, used to set speed on subsequent levels
        self.enemy_grid_clears = 0

        # initialize the score variable
        self.score_player = 0

        # ----- TEXT STUFF -----
        # set up the font
        self.TEXT_ANTIALIASING = False
        self.font = pygame.font.Font(SCORE_FONT_PATH, 8)

        # initialize the scoreboard objects
        # set the positions for the score, score label
        self.score_label_surface_pos = (self.screen.width // 5, self.screen.height // 20)
        self.score_value_surface_pos = (self.screen.width // 5, self.screen.height // 10)
        self.game_over_surface_pos = (self.screen.width // 2, 2 * self.screen.height // 5)
        self.extra_life_counter_surface_pos = (14, 240)
        # label "SCORE P1"
        self.score_label_surface = self.font.render('SCORE P1', self.TEXT_ANTIALIASING, FG_COLOR)
        self.score_label_rect = self.score_label_surface.get_rect()
        self.score_label_rect.center = self.score_label_surface_pos
        # score number e.g. "00002370"
        self.score_value_surface, self.score_value_rect = None, None
        self.setup_score_surface()

        # initialize game over text and background
        self.game_over_surface = self.font.render('GAME OVER', self.TEXT_ANTIALIASING, FG_COLOR)
        self.game_over_rect = self.game_over_surface.get_rect()
        self.game_over_rect.center = self.game_over_surface_pos
        
        # initialize extra life counter
        self.extra_life_counter_surface = self.font.render('0', self.TEXT_ANTIALIASING, FG_COLOR)
        self.extra_life_counter_rect = self.extra_life_counter_surface.get_rect()
        self.extra_life_counter_rect.center = self.extra_life_counter_surface_pos

        # kick off the main loop
        self.game_loop()
        
    def should_be_frozen_after_player_death(self):
        return self.time_since_player_death_ms < self.pause_time_after_player_death_ms

    def reset(self):
        self.game_is_over = False
        self.ms_elapsed_since_start = 0

        self.all_sprites.empty()
        self.current_player_sprite = None
        self.extra_player_sprites = pygame.sprite.Group()
        self.left_wall_sprite = None
        self.right_wall_sprite = None
        self.top_wall_sprite = None
        self.bottom_wall_sprite = None
        self.wall_sprites = pygame.sprite.Group()
        self.player_bullet_sprites = pygame.sprite.Group()
        self.enemy_bullet_sprites = pygame.sprite.Group()
        self.grid_enemy_sprites = pygame.sprite.Group()
        self.grid_enemy_sprites_columns = [pygame.sprite.Group() for _ in range(self.enemy_columns)]
        self.all_enemy_sprites = pygame.sprite.Group()
        self.barrier_sprites = pygame.sprite.Group()

        # reset and create sprites
        self.setup_new_game_sprites()

        # initialize the score variable
        self.reset_score()
        
    def setup_grid_enemies(self):
        self.grid_enemy_sprites = pygame.sprite.Group()
        self.grid_enemy_sprites_columns = [pygame.sprite.Group() for _ in range(self.enemy_columns)]
        self.all_enemy_sprites = pygame.sprite.Group()
        
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
            if row == 0:
                enemy_name = ENEMY_CONEHEAD_TAG
            # 2nd and 3rd enemy rows - Antenna
            elif row == 1 or row == 2:
                enemy_name = ENEMY_ANTENNA_TAG
            # 4th and 5th enemy rows - Ears
            # elif row == 3 or row == 4: enemy = ENEMY_EARS_TAG
            else:
                enemy_name = ENEMY_EARS_TAG
            for column, x in zip(range(self.enemy_columns), range(2 * x_increment, 13 * x_increment, x_increment)):
                # print(f'Row: {row} Column: {column}')
                enemy_sprites[enemy_name](
                    images=self.entity_info[enemy_name][IMAGES_TAG],
                    color=self.entity_info[enemy_name][COLOR_TAG],
                    speed=self.entity_info[enemy_name][SPEED_TAG],
                    x_pos=x,
                    y_pos=y_initial + (row * y_increment),
                    initial_grid_position=(row, column),
                    groups=(self.all_sprites, self.grid_enemy_sprites, self.grid_enemy_sprites_columns[column],
                            self.all_enemy_sprites))

    def setup_new_game_sprites(self):
        # ----- newgame sprite creation -----
        # create the top, bottom, right and left walls for the bullets to hit and the enemies to bounce off, respectively
        self.left_wall_sprite = Sprite(self.wall_sprites, self.all_sprites)
        self.right_wall_sprite = Sprite(self.wall_sprites, self.all_sprites)
        for wall_sprite in [self.left_wall_sprite, self.right_wall_sprite]:
            # just give the wall 100 width, will give some leeway for frame drops etc.
            wall_sprite.image = pygame.Surface([100, self.screen.height])
            wall_sprite.image.fill(BG_COLOR)
            wall_sprite.rect = wall_sprite.image.get_rect()
        # put the right edge of the left wall on the left edge of the screen
        self.left_wall_sprite.rect.right = 0
        # put the left edge of the right wall on the right edge of the screen
        self.right_wall_sprite.rect.left = self.screen.get_width()

        self.top_wall_sprite = Sprite(self.wall_sprites, self.all_sprites)
        self.bottom_wall_sprite = Sprite(self.wall_sprites, self.all_sprites)
        for wall_sprite in [self.top_wall_sprite, self.bottom_wall_sprite]:
            wall_sprite.image = pygame.Surface([self.screen.width, 1])
            wall_sprite.rect = wall_sprite.image.get_rect()
        self.top_wall_sprite.image.fill(BG_COLOR)
        self.bottom_wall_sprite.image.fill(GREEN)
        self.top_wall_sprite.rect.bottom = 36
        self.bottom_wall_sprite.rect.top = 232
        
        # player extra lives and 
        for _ in range(STARTING_LIVES):
            self.increment_player_extra_lives()

        # create the barrier sprites
        for x in range(self.screen.get_width() // 5, 4 * self.screen.get_width() // 5, self.screen.get_width() // 5):
            BarrierSprite(
                images=self.entity_info[BARRIER_TAG][IMAGES_TAG],
                color=self.entity_info[BARRIER_TAG][COLOR_TAG],
                speed=self.entity_info[BARRIER_TAG][SPEED_TAG],
                x_pos=x,
                y_pos=190,
                groups=(self.all_sprites, self.barrier_sprites))
            
        self.setup_grid_enemies()

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

    def increment_player_extra_lives(self):
        initial_x_pos = 30
        x_spacing = 16
        y_pos = 240
        num_extra_lives = len(self.extra_player_sprites.sprites())
        if num_extra_lives < MAX_EXTRA_LIVES:
            PlayerSprite(
                images=self.entity_info[PLAYER_SHIP_TAG][IMAGES_TAG],
                color=self.entity_info[PLAYER_SHIP_TAG][COLOR_TAG],
                speed=self.entity_info[PLAYER_SHIP_TAG][SPEED_TAG],
                x_pos=initial_x_pos + ((num_extra_lives) * x_spacing),
                y_pos=y_pos,
                groups=(self.all_sprites, self.extra_player_sprites))

    def replace_player_sprite(self) -> bool:
        if self.current_player_sprite:
            return False
        if len(self.extra_player_sprites.sprites()) <= 0:
            return False
        else:
            self.current_player_sprite = self.extra_player_sprites.sprites()[len(self.extra_player_sprites.sprites()) - 1]
            self.current_player_sprite.set_position(PLAYER_STARTING_POS)
            self.extra_player_sprites.remove(self.current_player_sprite)
            return True

    def draw_game_over(self):
        border_thickness = 1
        bg_rect = pygame.Rect(0, 0, self.game_over_rect.width * 1.5, self.game_over_rect.height * 2)
        bg_rect.center = self.game_over_rect.center
        bg_rect_frame = bg_rect.inflate(border_thickness * 2, border_thickness * 2)
        pygame.draw.rect(self.screen,
                         FG_COLOR,
                         bg_rect_frame,
                         0)
        pygame.draw.rect(self.screen,
                         BG_COLOR,
                         bg_rect,
                         0)
        self.screen.blit(self.game_over_surface, self.game_over_rect)

    @staticmethod
    def update_score_surface(func):
        @functools.wraps(func)
        def wrapper(calling_instance, *args, **kwargs):
            # change the score variable etc. before changing the visual
            result = func(calling_instance, *args, **kwargs)
            # change the visual
            calling_instance.score_value_surface = (calling_instance.font.render(
                f'{calling_instance.score_player:08d}',
                calling_instance
                .TEXT_ANTIALIASING,
                FG_COLOR))
            return result

        return wrapper

    def setup_score_surface(self):
        self.score_value_surface = self.font.render(f'{self.score_player:08d}',
                                                    self.TEXT_ANTIALIASING,
                                                    FG_COLOR)
        self.score_value_rect = self.score_value_surface.get_rect()
        self.score_value_rect.center = self.score_value_surface_pos

    @update_score_surface
    def reset_score(self):
        self.score_player = 0

    @update_score_surface
    def add_to_score(self, num):
        self.score_player += num

    def draw_score(self):
        # draw the score label "SCORE P1"
        self.screen.blit(self.score_label_surface, self.score_label_rect)
        # draw the numeric score
        self.screen.blit(self.score_value_surface, self.score_value_rect)
        
    def draw_extra_life_counter(self):
        lives = len(self.extra_player_sprites.sprites())
        if self.current_player_sprite is not None: lives += 1
        self.extra_life_counter_surface = self.font.render(f'{lives}', self.TEXT_ANTIALIASING, FG_COLOR)
        # draw the extra life number
        self.screen.blit(self.extra_life_counter_surface, self.extra_life_counter_rect)

    def player_shoot(self):
        # if no player bullet exists, create a bullet sprite at the player's location
        if len(self.player_bullet_sprites.sprites()) == 0:
            if self.current_player_sprite.time_since_shoot_ms >= self.current_player_sprite.min_shoot_interval_ms:
                PlayerBulletSprite(
                    images=self.entity_info[BULLET_PLAYER_TAG][IMAGES_TAG],
                    color=self.entity_info[BULLET_PLAYER_TAG][COLOR_TAG],
                    speed=self.entity_info[BULLET_PLAYER_TAG][SPEED_TAG],
                    x_pos=self.current_player_sprite.rect.centerx,
                    y_pos=self.current_player_sprite.rect.centery,
                    groups=(self.all_sprites, self.player_bullet_sprites)
                )
                self.current_player_sprite.time_since_shoot_ms = 0

    def enemy_shoot(self, enemy: EnemySprite):
        random_bullet_tag = random.choice([BULLET_GRID_ENEMY_1_TAG, BULLET_GRID_ENEMY_2_TAG, BULLET_GRID_ENEMY_3_TAG])
        GridEnemyBulletSprite(
            images=self.entity_info[random_bullet_tag][IMAGES_TAG],
            color=self.entity_info[random_bullet_tag][COLOR_TAG],
            speed=self.entity_info[random_bullet_tag][SPEED_TAG],
            x_pos=enemy.rect.centerx,
            y_pos=enemy.rect.centery,
            groups=(self.all_sprites, self.enemy_bullet_sprites)
        )

    def handle_enemy_shoot(self):
        if self.time_since_enemy_shoot_ms > self.enemy_shoot_interval_ms:
            # shoot, reset counter
            # if there is at least one grid enemy left
            if self.grid_enemy_sprites.sprites():
                # this list will contain the enemy at the bottom of each column that still exists
                possible_enemies = []
                # in each column of the enemy grid
                for column_sprite_group in self.grid_enemy_sprites_columns:
                    # if the column group has one sprite or more
                    if len(column_sprite_group.sprites()) > 0:
                        # add the enemy at the end of the group to the list of possibles
                        possible_enemies.append(column_sprite_group.sprites()[len(column_sprite_group) - 1])
                # trigger a shot from a random enemy from the possibles array
                self.enemy_shoot(random.choice(possible_enemies))
            # randomize the interval a little bit, but keep it rooted by the base value
            self.enemy_shoot_interval_ms = self.base_enemy_shoot_interval_ms * random.uniform(0.6, 1.2)
            # an enemy shot, so reset the counter
            self.time_since_enemy_shoot_ms = 0
        else:
            # don't shoot, increment counter
            self.time_since_enemy_shoot_ms += self.dt_ms

    def handle_collision(self):
        def _handle_grid_enemy_and_wall_collision():
            # see if the enemies have reached the edge
            if len(self.grid_enemy_sprites) > 0:
                ms_since_move_threshold = 100
                for wall, direction in [
                    (self.left_wall_sprite, Direction.RIGHT),
                    (self.right_wall_sprite, Direction.LEFT)]:
                    # if an enemy has collided with a wall AND
                    # if the top left Sprite (or the first one in the enemy_sprites array if the top left has been destroyed)
                    # has moved very recently
                    # the second 'if' statement exists because we need to make sure all of the enemies have moved
                    # toward the wall before reversing them all
                    if pygame.sprite.spritecollide(wall, self.all_enemy_sprites, False) and \
                            self.all_enemy_sprites.sprites()[0].ms_since_move < ms_since_move_threshold:
                        for sprite in self.all_enemy_sprites:
                            sprite.shift_down()
                            sprite.direction = direction

        def _handle_player_and_bullet_collision():
            if self.current_player_sprite is not None:
                collided = pygame.sprite.spritecollide(self.current_player_sprite, self.enemy_bullet_sprites, True)
                if collided:
                    # wipe enemy bullets
                    self.enemy_bullet_sprites.empty()
                    
                    # reset "time since player death" variable
                    self.time_since_player_death_ms = 0
                    
                    # make explosion
                    PlayerExplosionSprite(
                        images=self.entity_info[EXPLOSION_PLAYER_TAG][IMAGES_TAG],
                        color=self.entity_info[EXPLOSION_PLAYER_TAG][COLOR_TAG],
                        speed=self.entity_info[EXPLOSION_PLAYER_TAG][SPEED_TAG],
                        x_pos=self.current_player_sprite.rect.centerx,
                        y_pos=self.current_player_sprite.rect.centery,
                        time_should_exist_ms=PLAYER_EXPLOSION_LENGTH_MS,
                        groups=(self.all_sprites,)
                    )
                    self.current_player_sprite.kill()
                    self.current_player_sprite = None

        def _handle_enemy_and_bullet_collision():
            enemies_shot = pygame.sprite.groupcollide(self.player_bullet_sprites, self.grid_enemy_sprites,
                                                      True, True, collided=pygame.sprite.collide_mask)
            # {<PlayerBulletSprite Sprite(in 0 groups)>: [<EnemySprite Sprite(in 0 groups)>]}
            # find the value to add to the score and add it
            for enemies in enemies_shot.values():
                for enemy_sprite in enemies:
                    # print(f'Enemy killed - grid position {enemy.initial_grid_position}')
                    # give the player score depending on the enemy
                    self.add_to_score(enemy_sprite.score_for_kill)

                    # create an explosion at the place where the enemy died
                    ExplosionSprite(
                        images=self.entity_info[EXPLOSION_GRID_ENEMY_TAG][IMAGES_TAG],
                        color=self.entity_info[EXPLOSION_GRID_ENEMY_TAG][COLOR_TAG],
                        speed=self.entity_info[EXPLOSION_GRID_ENEMY_TAG][SPEED_TAG],
                        x_pos=enemy_sprite.rect.centerx,
                        y_pos=enemy_sprite.rect.centery,
                        time_should_exist_ms=EXPLOSION_LENGTH_MS,
                        groups=(self.all_sprites,)
                    )

            # speed up each grid enemy by setting their "time per move" proportional to the number of enemies left
            # fewer enemies = lower threshold = more moves per time
            for enemy_sprite in self.grid_enemy_sprites.sprites():
                # enemies get faster after each grid clear
                enemy_sprite.move_time_threshold = len(self.grid_enemy_sprites.sprites()) * max(10, (20 - self.enemy_grid_clears))
                

        def _handle_enemy_and_player_collision():
            if len(self.all_enemy_sprites) > 0 and self.current_player_sprite is not None:
                if pygame.sprite.spritecollide(self.current_player_sprite, self.all_enemy_sprites, False):
                    self.game_is_over = True

        def _handle_barrier_and_bullet_collision():
            collided = {}
            for bullet_group in (self.enemy_bullet_sprites, self.player_bullet_sprites):
                collided |= pygame.sprite.groupcollide(self.barrier_sprites, bullet_group,
                                                       False, True, collided=pygame.sprite.collide_mask)
            for barrier in collided:
                barrier.reduce_health(1)

        def _handle_double_bullet_collision():
            collided = pygame.sprite.groupcollide(self.player_bullet_sprites, self.enemy_bullet_sprites,
                                                  True, True, collided=pygame.sprite.collide_mask)
            for player_bullet, enemy_bullet in collided.items():
                # player bullet explosion
                ExplosionSprite(
                    images=self.entity_info[EXPLOSION_BULLET_PLAYER_TAG][IMAGES_TAG],
                    color=self.entity_info[EXPLOSION_BULLET_PLAYER_TAG][COLOR_TAG],
                    speed=self.entity_info[EXPLOSION_BULLET_PLAYER_TAG][SPEED_TAG],
                    x_pos=player_bullet.rect.centerx,
                    y_pos=player_bullet.rect.centery,
                    time_should_exist_ms=EXPLOSION_LENGTH_MS,
                    groups=(self.all_sprites,)
                )
                # enemy bullet explosion
                ExplosionSprite(
                    images=self.entity_info[EXPLOSION_BULLET_ENEMY_TAG][IMAGES_TAG],
                    color=self.entity_info[EXPLOSION_BULLET_ENEMY_TAG][COLOR_TAG],
                    speed=self.entity_info[EXPLOSION_BULLET_ENEMY_TAG][SPEED_TAG],
                    x_pos=enemy_bullet[0].rect.centerx,
                    y_pos=enemy_bullet[0].rect.centery,
                    time_should_exist_ms=EXPLOSION_LENGTH_MS,
                    groups=(self.all_sprites,)
                )

        def _handle_player_bullet_wall_collision():
            collided = pygame.sprite.groupcollide(self.player_bullet_sprites, self.wall_sprites,
                                                  True, False, collided=pygame.sprite.collide_mask)
            for player_bullet in collided.keys():
                # player bullet explosion
                ExplosionSprite(
                    images=self.entity_info[EXPLOSION_BULLET_ENEMY_TAG][IMAGES_TAG],
                    color=RED,
                    speed=self.entity_info[EXPLOSION_BULLET_PLAYER_TAG][SPEED_TAG],
                    x_pos=player_bullet.rect.centerx,
                    y_pos=player_bullet.rect.centery,
                    time_should_exist_ms=EXPLOSION_LENGTH_MS,
                    groups=(self.all_sprites,)
                )

        def _handle_enemy_bullet_wall_collision():
            collided = pygame.sprite.groupcollide(self.enemy_bullet_sprites, self.wall_sprites,
                                                  True, False, collided=pygame.sprite.collide_mask)
            for enemy_bullet in collided.keys():
                # enemy bullet explosion
                ExplosionSprite(
                    images=self.entity_info[EXPLOSION_BULLET_PLAYER_TAG][IMAGES_TAG],
                    color=GREEN,
                    speed=self.entity_info[EXPLOSION_BULLET_ENEMY_TAG][SPEED_TAG],
                    x_pos=enemy_bullet.rect.centerx,
                    y_pos=enemy_bullet.rect.centery - 1.5,
                    time_should_exist_ms=EXPLOSION_LENGTH_MS,
                    groups=(self.all_sprites,)
                )
        
        # Enemy collides with PlayerBullet
        _handle_enemy_and_bullet_collision()

        # Player collides with EnemyBullet
        _handle_player_and_bullet_collision()

        # Barrier collides with Bullet of any kind
        _handle_barrier_and_bullet_collision()

        # Enemy collides with Player
        _handle_enemy_and_player_collision()

        # GridEnemy collides with side wall
        _handle_grid_enemy_and_wall_collision()

        # EnemyBullet collides with PlayerBullet
        _handle_double_bullet_collision()

        # Player or Enemy Bullet collides with wall
        _handle_player_bullet_wall_collision()
        _handle_enemy_bullet_wall_collision()

    def handle_input(self):
        # poll for pressed keys during this frame
        keys = pygame.key.get_pressed()

        # everything within this if statement only happens if the game is not over
        if not self.game_is_over and self.current_player_sprite:
            # check A, D, Left Arrow, Right Arrow
            for k_letter, k_arrow, direction in [
                (keys[pygame.K_a], keys[pygame.K_LEFT], Direction.LEFT),
                (keys[pygame.K_d], keys[pygame.K_RIGHT], Direction.RIGHT), ]:
                if k_letter or k_arrow:
                    if not self.current_player_sprite.is_at_edge(self.screen, direction):
                        self.current_player_sprite.start_moving(direction)
                    else:
                        self.current_player_sprite.stop_moving()
                    break
                    # Neither A nor D nor Left nor Right is pressed
            else:
                self.current_player_sprite.stop_moving()

            # Spacebar - shoot
            if keys[pygame.K_SPACE]:
                self.player_shoot()
                
        # N for new game - DEBUG
        # TODO remove debug N mapping to newgame
        if keys[pygame.K_n]:
            self.reset()

        # Escape - quit
        if keys[pygame.K_ESCAPE]:
            self.running = False

    def update_sprite_group_except_groups(self, group_to_update: pygame.sprite.Group, *exception_groups):
        for sprite in group_to_update.sprites():
            should_update = True
            for exception_group in exception_groups:
                if sprite in exception_group:
                    should_update = False
            if should_update: 
                sprite.update(self.dt_ms, self.ms_elapsed_since_start)
    
    def game_loop(self):
        while self.running:
            # poll for events
            for event in pygame.event.get():
                # pygame.QUIT event means the user clicked X to close your window
                if event.type == pygame.QUIT:
                    # cause the gameloop to end
                    self.running = False

            # handle the keyboard and mouse input
            self.handle_input()

            # wipe away anything from last frame
            self.screen.fill(BG_COLOR)

            # things in this section only happen if the game is not over
            if not self.game_is_over:
                # if there are no grid enemies, increment the clear counter and re-populate the grid
                if len(self.grid_enemy_sprites.sprites()) <= 0:
                    self.enemy_grid_clears += 1
                    self.setup_grid_enemies()
                
                # check for collisions
                self.handle_collision()

                # in the if statement, we are frozen after a player death
                if self.should_be_frozen_after_player_death():
                    # update everything except the enemy sprites
                    self.update_sprite_group_except_groups(self.all_sprites, self.all_enemy_sprites)
                # for the else, we are not frozen after player death
                else:
                    # if the player has no sprite
                    if self.current_player_sprite is None:
                        # replace the player sprite if possible, otherwise end the game
                        replaced_player = self.replace_player_sprite()
                        if not replaced_player:
                            self.game_is_over = True
                    # decide if an enemy should shoot, and if so, handle it
                    self.handle_enemy_shoot()
                    # call every sprite's update() if the game's not over
                    self.all_sprites.update(self.dt_ms, self.ms_elapsed_since_start)

            # draw all the sprites (excluding text)
            self.all_sprites.draw(self.screen)

            # draw the score label and score
            self.draw_score()
            
            # draw extra life counter
            self.draw_extra_life_counter()

            # show the GAME OVER text on top of everything
            if self.game_is_over:
                self.draw_game_over()

            # flip() the display to put your work on screen
            pygame.display.flip()

            # limits FPS to 60
            # the number of milliseconds passed since the last .tick() call
            # multiply movements by dt to create framerate-independence (real-time dependence)
            self.dt_ms = self.clock.tick(self.FPS)
            # add elapsed milliseconds to milliseconds since start
            self.ms_elapsed_since_start += self.dt_ms
            self.time_since_player_death_ms += self.dt_ms

        pygame.quit()


if __name__ == '__main__':
    game = SpaceInvaders()
