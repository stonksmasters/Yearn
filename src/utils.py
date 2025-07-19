import pygame
import os
import random
import math
import logging
from settings import BASE_DIR, SOUND_VOLUME, TILE_SIZE
from entities import OreItem, Particle

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing utils.py")

def load_sound(filename, fallback="mining.wav"):
    """Load a sound file with a fallback option."""
    try:
        sound = pygame.mixer.Sound(os.path.join(BASE_DIR, "assets", filename))
        sound.set_volume(SOUND_VOLUME)
        logger.debug(f"Loaded sound: {filename}")
        return sound
    except Exception as e:
        logger.warning(f"Failed to load {filename}, using fallback {fallback}: {e}")
        sound = pygame.mixer.Sound(os.path.join(BASE_DIR, "assets", fallback))
        sound.set_volume(SOUND_VOLUME)
        return sound

def calculate_distance(pos1, pos2):
    """Calculate Euclidean distance between two points."""
    distance = math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)
    logger.debug(f"Calculated distance between {pos1} and {pos2}: {distance}")
    return distance

def trigger_screen_shake(game, duration=0.2, intensity=2):
    """Trigger a screen shake effect."""
    game.shake_timer = duration
    game.shake_intensity = intensity
    logger.debug(f"Triggered screen shake: duration={duration}, intensity={intensity}")

def trigger_screen_flash(game, duration=0.2, color=(255, 255, 255)):
    """Trigger a screen flash effect."""
    game.flash_timer = duration
    game.flash_color = color
    logger.debug(f"Triggered screen flash: duration={duration}, color={color}")

def spawn_ore_item(game, x, y, block_type, is_artifact=False):
    """Spawn an OreItem at the specified position."""
    if block_type in game.ores_cfg:
        value = game.ores_cfg[block_type]["value"]
        ore_item = OreItem(x, y, block_type, value, game.ores_cfg, is_artifact)
        game.entity_manager.add(ore_item, "ore_items")
        logger.debug(f"Spawned OreItem: {block_type} at ({x}, {y}), value=${value}, artifact={is_artifact}")
        return ore_item
    return None

def spawn_particles(game, x, y, count, sparkle=False, treasure=False, rock_chip=False):
    """Spawn particles at the specified position."""
    for _ in range(count):
        vx = random.uniform(-50, 50)
        vy = random.uniform(-50, 50)
        life = random.uniform(0.5, 1.0)
        particle = Particle(x, y, vx, vy, life, sparkle, treasure, rock_chip)
        game.entity_manager.add(particle, "particles")
    logger.debug(f"Spawned {count} particles at ({x}, {y}), sparkle={sparkle}, treasure={treasure}, rock_chip={rock_chip}")

def aoe_mining(game, center_x, center_y, radius):
    """Perform area-of-effect mining around the specified position."""
    center_tile_x = int(center_x // TILE_SIZE)
    center_tile_y = int(center_y // TILE_SIZE)
    for y in range(center_tile_y - radius, center_tile_y + radius + 1):
        for x in range(center_tile_x - radius, center_tile_x + radius + 1):
            if 0 <= x < game.world.num_cols and 0 <= y < game.world.max_depth:
                if math.sqrt((center_tile_x - x) ** 2 + (center_tile_y - y) ** 2) <= radius:
                    block = game.world.block_at(x, y)
                    if block and block != "empty":
                        game.world.break_block(x, y, game.players[0], game)
                        logger.debug(f"AOE mined block at ({x}, {y}): {block}")