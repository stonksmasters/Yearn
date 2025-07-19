import pygame
import logging
import settings
from data import load_ores
import random

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing renderer.py")

class Renderer:
    def __init__(self, screen, settings_module):
        """Initialize the renderer with the screen and settings."""
        self.screen = screen
        self.settings = settings_module
        self.ores = load_ores()
        self.block_colors = {
            "dirt": (139, 69, 19),
            "stone": (128, 128, 128),
            "iron": (192, 192, 192),
            "gold": (255, 215, 0),
            "ruby": (255, 0, 0),
            "sapphire": (0, 0, 255),
            "emerald": (0, 255, 0),
            "mithril": (135, 206, 235),
            "cave_wall": (105, 105, 105),
            "crystal_wall": (0, 255, 255),
            "grass": (0, 128, 0),
            "unstable": (100, 100, 100)
        }
        self.crack_overlays = {
            1: (100, 100, 100, 50),  # Light cracks for stage 1
            2: (100, 100, 100, 100),  # Medium cracks for stage 2
            3: (100, 100, 100, 150)  # Heavy cracks for stage 3
        }
        logger.info("Renderer initialized")

    def draw_world(self, world, camera_x, camera_y):
        """Draw the game world with camera offset, rendering only visible tiles."""
        start_x = max(0, int(camera_x // self.settings.TILE_SIZE))
        end_x = min(self.settings.NUM_COLS, int((camera_x + self.settings.WIDTH) // self.settings.TILE_SIZE) + 1)
        start_y = max(0, int(camera_y // self.settings.TILE_SIZE))
        end_y = min(self.settings.MAX_DEPTH, int((camera_y + self.settings.HEIGHT) // self.settings.TILE_SIZE) + 1)

        for x in range(start_x, end_x):
            for y in range(start_y, end_y):
                block = world.block_at(x, y)
                if block and block != "empty":
                    screen_x = x * self.settings.TILE_SIZE - camera_x
                    screen_y = y * self.settings.TILE_SIZE - camera_y
                    color = self.ores.get(block, {}).get("color", self.block_colors.get(block, (255, 255, 255)))
                    pygame.draw.rect(
                        self.screen,
                        color,
                        (screen_x, screen_y, self.settings.TILE_SIZE, self.settings.TILE_SIZE)
                    )
                    # Draw mining progress cracks
                    block_state = world.get_block_state(x, y)
                    if block_state > 0:
                        overlay = pygame.Surface((self.settings.TILE_SIZE, self.settings.TILE_SIZE))
                        overlay.set_alpha(self.crack_overlays.get(block_state, (0, 0, 0, 0))[3])
                        overlay.fill(self.crack_overlays.get(block_state, (0, 0, 0, 0))[:3])
                        self.screen.blit(overlay, (screen_x, screen_y))

        # Draw falling rocks
        for rock in world.falling_rocks:
            if rock.active:
                screen_x = rock.x - camera_x
                screen_y = rock.y - camera_y
                if -self.settings.TILE_SIZE <= screen_x < self.settings.WIDTH and -self.settings.TILE_SIZE <= screen_y < self.settings.HEIGHT:
                    color = self.ores.get(rock.ore_type, {}).get("color", self.block_colors.get(rock.ore_type, (100, 100, 100)))
                    pygame.draw.rect(
                        self.screen,
                        color,
                        (screen_x, screen_y, self.settings.TILE_SIZE, self.settings.TILE_SIZE)
                    )

    def draw_entities(self, entity_groups, camera_x, camera_y):
        """Draw all entities with camera offset."""
        for group in entity_groups:
            for entity in group:
                entity.draw(self.screen, camera_x, camera_y)

    def draw_players(self, players, camera_x, camera_y):
        """Draw players with camera offset."""
        for i, player in enumerate(players):
            screen_x = player.rect.x - camera_x
            screen_y = player.rect.y - camera_y
            color = self.settings.PLAYER_COLOR if i == 0 else self.settings.PLAYER2_COLOR
            pygame.draw.rect(
                self.screen,
                color,
                (screen_x, screen_y, player.rect.width, player.rect.height)
            )

    def draw_ore_scanner(self, ore_scanner, camera_x, camera_y):
        """Draw the ore scanner effect."""
        ore_scanner.draw(self.screen, camera_x, camera_y)

    def draw_ui(self, ui, game):
        """Draw the UI elements, including mining fatigue and progress bars."""
        ui.draw(self.screen, game)

        # Draw mining fatigue bar
        if game.mining_fatigue > 0:
            pygame.draw.rect(self.screen, (200, 0, 0), (10, self.settings.HEIGHT - 110, 100, 10))  # Red background
            pygame.draw.rect(self.screen, (255, 165, 0), (10, self.settings.HEIGHT - 110, 100 * game.mining_fatigue, 10))  # Orange fill
            pygame.draw.rect(self.screen, self.settings.WHITE, (10, self.settings.HEIGHT - 110, 100, 10), 2)  # White border
            fatigue_text = ui.font.render("Fatigue", True, self.settings.WHITE)
            self.screen.blit(fatigue_text, (10, self.settings.HEIGHT - 130))
            logger.debug(f"Rendered fatigue bar: {game.mining_fatigue:.2f}")

        # Draw mining progress bar above targeted block
        if game.mining and game.mine_target:
            tx, ty = game.mine_target
            screen_x = tx * self.settings.TILE_SIZE - game.camera_x
            screen_y = ty * self.settings.TILE_SIZE - game.camera_y
            if 0 <= screen_x < self.settings.WIDTH and 0 <= screen_y < self.settings.HEIGHT:
                pygame.draw.rect(self.screen, (50, 50, 50), (screen_x, screen_y - 10, self.settings.TILE_SIZE, 5))  # Dark gray background
                pygame.draw.rect(self.screen, (0, 255, 0), (screen_x, screen_y - 10, self.settings.TILE_SIZE * game.mining_progress, 5))  # Green fill
                pygame.draw.rect(self.screen, self.settings.WHITE, (screen_x, screen_y - 10, self.settings.TILE_SIZE, 5), 1)  # White border
                logger.debug(f"Rendered mining progress bar at ({tx}, {ty}): {game.mining_progress:.2f}")

        logger.debug("UI rendered with fatigue and progress bars")

    def apply_effects(self, shake_timer, shake_intensity, flash_timer, flash_color):
        """Apply screen shake and flash effects."""
        if shake_timer > 0:
            offset_x = random.uniform(-shake_intensity, shake_intensity)
            offset_y = random.uniform(-shake_intensity, shake_intensity)
            self.screen.blit(self.screen, (offset_x, offset_y))
        if flash_timer > 0:
            overlay = pygame.Surface((self.settings.WIDTH, self.settings.HEIGHT))
            overlay.set_alpha(int(255 * flash_timer / 0.2))
            overlay.fill(flash_color)
            self.screen.blit(overlay, (0, 0))