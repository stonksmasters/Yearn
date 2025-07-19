import os
import pygame

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Data directory for JSON files
DATA_DIR = os.path.join(BASE_DIR, "data")

# Game constants
WIDTH = 1280
HEIGHT = 720
FPS = 60
TILE_SIZE = 32
NUM_COLS = 100
MAX_DEPTH = 100000
MOVE_SPEED = 200
JUMP_VELOCITY = -400
GRAVITY = 800
FONT_NAME = "arial"
FONT_SIZE = 24
SOUND_VOLUME = 0.5
QUOTA_BASE = 1000
QUOTA_INCREASE = 1.2
DAY_DURATION = 300  # 5 minutes in seconds
PLAYER_COLOR = (0, 0, 255)
PLAYER2_COLOR = (255, 0, 0)
WHITE = (255, 255, 255)
BLOCK_PITCHES = {
    "dirt": 0.8,
    "stone": 1.0,
    "iron": 1.2,
    "gold": 1.4,
    "ruby": 1.6,
    "sapphire": 1.8,
    "emerald": 2.0,
    "mithril": 2.2,
    "cave_wall": 0.9,
    "crystal_wall": 1.1
}
ENEMY_DROPS = {
    "bat_drop": [
        {"ore_type": "bat_wing", "value": 50, "chance": 0.5, "color": (128, 128, 128)}
    ],
    "goblin_drop": [
        {"ore_type": "goblin_tooth", "value": 100, "chance": 0.3, "color": (0, 255, 0)}
    ]
}
KEYS = {
    "PAUSE": pygame.K_p,
    "UPGRADE": pygame.K_u,
    "INVENTORY": pygame.K_i,
    "DEBUG": pygame.K_F1,
    "MINIMAP": pygame.K_m,
    "SECOND_PLAYER": pygame.K_2,
    "LEFT": pygame.K_LEFT,
    "RIGHT": pygame.K_RIGHT,
    "JUMP": pygame.K_UP,
    "THROW": pygame.K_t,
    "P2_LEFT": pygame.K_a,
    "P2_RIGHT": pygame.K_d,
    "P2_JUMP": pygame.K_w,
    "P2_THROW": pygame.K_g,
    "DYNAMITE": pygame.K_d,
    "HEALTH_PACK": pygame.K_h,
    "EARTHQUAKE": pygame.K_e,
    "DEPTH_CHARGE": pygame.K_f,
    "DROP_ORE": pygame.K_o,
    "MELEE": pygame.K_SPACE
}