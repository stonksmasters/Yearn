import pygame
import random
import math
import time
import logging
import settings
from settings import WIDTH, HEIGHT, TILE_SIZE, NUM_COLS, MAX_DEPTH, ENEMY_DROPS

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing entities.py")

class Particle:
    def __init__(self, x, y, vx, vy, life, sparkle=False, treasure=False, rock_chip=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.sparkle = sparkle
        self.treasure = treasure
        self.rock_chip = rock_chip

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, screen, camera_x, camera_y):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            if self.treasure:
                color = (255, 215, 0)
                size = 5
            elif self.sparkle:
                color = (255, 255, 0)
                size = 3
            elif self.rock_chip:
                color = (80, 80, 80)
                size = 2
            else:
                color = (100, 100, 100)
                size = 3
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.fill((*color, alpha))
            screen.blit(surf, (self.x - camera_x, self.y - camera_y))

class OreItem:
    def __init__(self, x, y, ore_type, value, ores_cfg, is_artifact=False):
        self.rect = pygame.Rect(x, y, TILE_SIZE // 2, TILE_SIZE // 2)
        self.ore_type = ore_type
        self.base_value = value  # Base value from ores_cfg, no multipliers
        self.color = ores_cfg.get(ore_type, {'color': (100, 100, 100)})['color']
        self.life = 10.0
        self.vx = random.uniform(-50, 50)
        self.vy = random.uniform(-50, 50)
        self.creation_time = time.time()
        self.is_artifact = is_artifact
        self.float_timer = 0.0
        self.rotation = 0.0
        self.pulse_timer = 0.0
        self.collected = False  # Flag to prevent multiple collections
        self.collecting = False  # Flag for animation toward player
        self.target_player = None  # Player to move toward during collection
        self.collect_speed = 200  # Pixels per second for collection animation
        self.collect_timer = 0.5  # Duration of collection animation
        self.id = id(self)  # Unique ID for debugging
        logger.debug(f"Spawned OreItem {self.id}: {ore_type} at ({x}, {y}), base_value=${value:.2f}")

    def update(self, dt, game):
        if self.collected:
            logger.debug(f"OreItem {self.id} already collected, marking for removal")
            return True, None  # Already collected, mark for removal

        if self.collecting and self.target_player:
            # Move toward target player
            dx = self.target_player.rect.centerx - self.rect.centerx
            dy = self.target_player.rect.centery - self.rect.centery
            distance = math.sqrt(dx**2 + dy**2)
            if distance > 0:
                speed = self.collect_speed
                self.vx = (dx / distance) * speed
                self.vy = (dy / distance) * speed
                self.rect.x += self.vx * dt
                self.rect.y += self.vy * dt
            self.collect_timer -= dt
            if distance < 10 or self.collect_timer <= 0:
                # Collect when close to player or timer expires
                depth_zone = game.world.get_depth_zone(int(self.rect.centery // settings.TILE_SIZE))
                value_per_unit = self.base_value
                total_value = self.base_value * depth_zone["value_scale"]
                if self.is_artifact or self.ore_type == "diamond":
                    total_value *= 2
                if self.target_player.lucky_miner and random.random() < 0.1:
                    total_value *= 2
                total_value *= self.target_player.cash_multiplier * game.bonus_multiplier
                ore_pos = (self.rect.x, self.rect.y)
                if self.target_player.add_ore(self.ore_type, value_per_unit, 1, ore_pos):
                    self.collected = True
                    logger.debug(f"Collected OreItem {self.id}: {self.ore_type} into inventory, value_per_unit=${value_per_unit:.2f}, total_value=${total_value:.2f}, pos={ore_pos}")
                    return True, self.target_player
                else:
                    self.target_player.cash += total_value
                    game.cash_earned_today += total_value
                    if self.is_artifact:
                        self.target_player.artifacts = getattr(self.target_player, 'artifacts', 0) + 1
                    self.collected = True
                    logger.debug(f"Inventory full for OreItem {self.id}, added ${total_value:.2f} to cash for {self.ore_type}, pos={ore_pos}")
                    return True, self.target_player
            return False, None

        self.life -= dt
        self.float_timer += dt
        self.pulse_timer += dt
        self.rotation += dt * 2
        self.vy += 300 * dt  # Apply gravity
        self.rect.y += math.sin(self.float_timer * 3) * 10 * dt
        closest_player = None
        min_distance = float('inf')
        for player in game.players:
            if player.ore_magnet:
                dx = player.rect.centerx - self.rect.centerx
                dy = player.rect.centery - self.rect.centery
                distance = math.sqrt(dx**2 + dy**2)
                if distance < min_distance:
                    min_distance = distance
                    closest_player = player
        if closest_player and closest_player.ore_magnet:
            dx = closest_player.rect.centerx - self.rect.centerx
            dy = closest_player.rect.centery - self.rect.centery
            distance = math.sqrt(dx**2 + dy**2)
            if distance > 0:
                speed = 100
                self.vx += (dx / distance) * speed * dt
                self.vy += (dy / distance) * speed * dt
        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt
        # Check collision with world blocks
        for block in game.world.get_surrounding_blocks(self.rect):
            if self.rect.colliderect(block):
                if self.vy > 0:  # Moving down
                    self.rect.bottom = block.top
                    self.vy = -self.vy * 0.5  # Bounce with reduced velocity
                elif self.vy < 0:  # Moving up
                    self.rect.top = block.bottom
                    self.vy = -self.vy * 0.5
                if self.vx > 0:  # Moving right
                    self.rect.right = block.left
                    self.vx = -self.vx * 0.5
                elif self.vx < 0:  # Moving left
                    self.rect.left = block.right
                    self.vx = -self.vx * 0.5
        for player in game.players:
            if self.life <= 0 or (time.time() - self.creation_time > 0.5 and self.rect.colliderect(player.rect)):
                depth_zone = game.world.get_depth_zone(int(self.rect.centery // settings.TILE_SIZE))
                value_per_unit = self.base_value
                total_value = self.base_value * depth_zone["value_scale"]
                if self.is_artifact or self.ore_type == "diamond":
                    total_value *= 2
                if player.lucky_miner and random.random() < 0.1:
                    total_value *= 2
                total_value *= player.cash_multiplier * game.bonus_multiplier
                ore_pos = (self.rect.x, self.rect.y)
                if player.add_ore(self.ore_type, value_per_unit, 1, ore_pos):
                    self.collected = True
                    logger.debug(f"Collected OreItem {self.id}: {self.ore_type} into inventory, value_per_unit=${value_per_unit:.2f}, total_value=${total_value:.2f}, pos={ore_pos}")
                    return True, player
                else:
                    player.cash += total_value
                    game.cash_earned_today += total_value
                    if self.is_artifact:
                        player.artifacts = getattr(player, 'artifacts', 0) + 1
                    self.collected = True
                    logger.debug(f"Inventory full for OreItem {self.id}, added ${total_value:.2f} to cash for {self.ore_type}, pos={ore_pos}")
                    return True, player
        return False, None

    def draw(self, screen, camera_x, camera_y):
        if self.collected:
            return  # Skip drawing if collected
        if self.rect.x - camera_x + self.rect.width > 0 and self.rect.x - camera_x < WIDTH and self.rect.y - camera_y + self.rect.height > 0 and self.rect.y - camera_y < HEIGHT:
            color = (255, 215, 0) if self.is_artifact else self.color
            size = TILE_SIZE if self.is_artifact else TILE_SIZE // 2
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            scale = 1.0 + 0.2 * math.sin(self.rotation)
            scaled_size = int(size * scale)
            alpha = 255 if not self.is_artifact else int(200 + 55 * math.sin(self.pulse_timer * 4))
            scaled_surf = pygame.transform.scale(surf, (scaled_size, scaled_size))
            scaled_surf.fill((*color, alpha))
            if self.is_artifact or self.ore_type in ["ruby", "sapphire", "emerald", "mithril"]:
                pygame.draw.rect(scaled_surf, (255, 255, 255), (0, 0, scaled_size, scaled_size), 2)
            screen.blit(scaled_surf, (self.rect.x - camera_x - (scaled_size - size) // 2, self.rect.y - camera_y - (scaled_size - size) // 2))

class FallingRock:
    def __init__(self, x, y, velocity, block_type):
        self.rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
        self.vy = velocity
        self.block_type = block_type
        self.warning_timer = 2.0
        self.active = False
        logger.debug(f"FallingRock spawned at ({x}, {y}) with type {block_type}")

    def update(self, dt, game):
        if self.warning_timer > 0:
            self.warning_timer -= dt
            if self.warning_timer <= 0:
                self.active = True
        if not self.active:
            return
        self.rect.y += self.vy * dt
        for block in game.world.get_surrounding_blocks(self.rect):
            if self.rect.colliderect(block):
                self.vy = 0
                self.rect.bottom = block.top
                logger.debug(f"FallingRock stopped at ({self.rect.x}, {self.rect.y})")
                return
        for player in game.players:
            if self.rect.colliderect(player.rect):
                damage = 10 * (1.0 - player.rock_damage_reduction)
                player.health -= damage
                self.vy = 0
                logger.debug(f"FallingRock hit player at ({self.rect.x}, {self.rect.y}), dealt {damage} damage")
                return
        if self.rect.y > game.world.get_surface_y(self.rect.x // TILE_SIZE) * TILE_SIZE + 1000:
            self.vy = 0
            logger.debug(f"FallingRock despawned at ({self.rect.x}, {self.rect.y})")

    def draw(self, screen, camera_x, camera_y):
        if self.warning_timer > 0:
            alpha = int(255 * (self.warning_timer / 2.0))
            surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            surf.fill((255, 0, 0, alpha))
            screen.blit(surf, (self.rect.x - camera_x, self.rect.y - camera_y))
        elif self.active:
            color = game.ores_cfg.get(self.block_type, {"color": (100, 100, 100)})["color"]
            pygame.draw.rect(screen, color, (self.rect.x - camera_x, self.rect.y - camera_y, TILE_SIZE, TILE_SIZE))

class Explosion:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.timer = 0.5
        logger.debug(f"Explosion created at ({x}, {y}) with radius {radius}")

    def update(self, dt, game):
        self.timer -= dt
        return self.timer <= 0

    def draw(self, screen, camera_x, camera_y):
        if self.timer > 0:
            alpha = int(255 * (self.timer / 0.5))
            surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 165, 0, alpha), (self.radius, self.radius), self.radius)
            screen.blit(surf, (self.x - self.radius - camera_x, self.y - self.radius - camera_y))

class OreScanner:
    def __init__(self, player, world):
        self.player = player
        self.world = world
        self.active = False
        self.timer = 0.0
        self.ores = []
        self.radius = 10
        logger.debug("Initialized OreScanner")

    def scan(self, duration):
        self.active = True
        self.timer = duration
        center_x = int(self.player.rect.centerx // TILE_SIZE)
        center_y = int(self.player.rect.centery // TILE_SIZE)
        self.ores = []
        for y in range(center_y - self.radius, center_y + self.radius + 1):
            for x in range(center_x - self.radius, center_x + self.radius + 1):
                if 0 <= x < NUM_COLS and 0 <= y < MAX_DEPTH:
                    block = self.world.block_at(x, y)
                    if block in ["ruby", "sapphire", "emerald", "mithril"]:
                        self.ores.append((x, y))
        logger.debug(f"OreScanner activated, found {len(self.ores)} valuable ores")

    def update(self, current_time):
        if self.active:
            self.timer -= (current_time - self.player.last_update_time)
            if self.timer <= 0:
                self.active = False
                logger.debug("OreScanner deactivated")

    def draw(self, screen, camera_x, camera_y):
        if self.active:
            for x, y in self.ores:
                surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                surf.fill((255, 255, 0, 128))
                screen.blit(surf, (x * TILE_SIZE - camera_x, y * TILE_SIZE - camera_y))

class Enemy:
    def __init__(self, x, y, enemy_type):
        self.rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
        self.type = enemy_type
        self.vx = random.choice([-150, 150]) if enemy_type == "goblin" else random.choice([-100, 100])
        self.vy = 0
        self.health = 10 if enemy_type == "bat" else 15
        self.active = True
        self.dropped_items = []
        self.stolen_cash = 0

    def update(self, dt, game):
        if not self.active:
            return
        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt
        for block in game.world.get_surrounding_blocks(self.rect):
            if self.rect.colliderect(block):
                self.vx *= -1
                self.rect.x += self.vx * dt
                break
        for player in game.players:
            if self.rect.colliderect(player.rect) and not player.active_effects.get("shield_generator", {}).get("active", False):
                player.health -= 5
                dropped = player.drop_inventory()
                self.dropped_items.extend(dropped)
                if random.random() < 0.2:
                    stolen = player.cash * 0.05
                    player.cash = max(0, player.cash - stolen)
                    self.stolen_cash += stolen
                    logger.debug(f"{self.type} stole ${stolen:.2f} from player")
                self.vx *= -1
                logger.debug(f"{self.type} hit player at ({self.rect.x}, {self.rect.y}), dropped: {dropped}")
        if self.health <= 0:
            self.active = False
            drop_key = "bat_drop" if self.type == "bat" else "goblin_drop"
            for drop in ENEMY_DROPS.get(drop_key, []):
                if random.random() < drop["chance"]:
                    game.entity_manager.add(OreItem(self.rect.x, self.rect.y, drop["ore_type"], drop["value"], game.ores_cfg), "ore_items")
            logger.debug(f"{self.type} defeated at ({self.rect.x}, {self.rect.y})")

    def draw(self, screen, camera_x, camera_y):
        if self.active:
            drop_key = "bat_drop" if self.type == "bat" else "goblin_drop"
            color = ENEMY_DROPS.get(drop_key, {"color": (128, 128, 128)})["color"]
            pygame.draw.rect(screen, color, (self.rect.x - camera_x, self.rect.y - camera_y, TILE_SIZE, TILE_SIZE))

class BlasterShot:
    def __init__(self, x, y, vx, vy):
        self.rect = pygame.Rect(x, y, TILE_SIZE // 4, TILE_SIZE // 4)
        self.vx = vx
        self.vy = vy
        self.life = 2.0
        logger.debug(f"BlasterShot spawned at ({x}, {y}) with velocity ({vx}, {vy})")

    def update(self, dt, game):
        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt
        self.life -= dt
        for enemy in game.entity_manager.entities["enemies"]:
            if self.rect.colliderect(enemy.rect):
                enemy.health -= 5
                self.life = 0
                logger.debug(f"BlasterShot hit enemy at ({self.rect.x}, {self.rect.y})")
                return
        for block in game.world.get_surrounding_blocks(self.rect):
            if self.rect.colliderect(block):
                self.life = 0
                logger.debug(f"BlasterShot hit block at ({self.rect.x}, {self.rect.y})")
                return

    def draw(self, screen, camera_x, camera_y):
        if self.life > 0:
            pygame.draw.rect(screen, (255, 0, 0), (self.rect.x - camera_x, self.rect.y - camera_y, self.rect.width, self.rect.height))

class EntityManager:
    def __init__(self):
        self.entities = {
            "rocks": [],
            "explosions": [],
            "ore_items": [],
            "particles": [],
            "enemies": [],
            "blaster_shots": []
        }
        logger.info("EntityManager initialized")

    def add(self, entity, category):
        """Add an entity to the specified category."""
        if category not in self.entities:
            logger.error(f"Invalid entity category: {category}")
            return
        self.entities[category].append(entity)
        logger.debug(f"Added {type(entity).__name__} to {category}, total {category}: {len(self.entities[category])}")

    def update(self, dt, game):
        """Update all entities and handle removals."""
        for category in self.entities:
            logger.debug(f"Updating {category}, count before: {len(self.entities[category])}")
            entities_to_remove = set()  # Use set to avoid duplicates
            for entity in self.entities[category][:]:  # Iterate over copy
                if hasattr(entity, "update"):
                    if category == "ore_items":
                        remove, player = entity.update(dt, game)
                        if remove:
                            entities_to_remove.add(entity)
                    elif category == "explosions":
                        if entity.update(dt, game):
                            entities_to_remove.add(entity)
                    else:
                        entity.update(dt, game)
                        if hasattr(entity, "active") and not entity.active:
                            entities_to_remove.add(entity)
                        elif hasattr(entity, "life") and entity.life <= 0:
                            entities_to_remove.add(entity)
            # Remove entities immediately
            for entity in entities_to_remove:
                if entity in self.entities[category]:
                    self.entities[category].remove(entity)
                    logger.debug(f"Removed {type(entity).__name__} (id: {getattr(entity, 'id', 'N/A')}) from {category}")
                else:
                    logger.warning(f"Attempted to remove {type(entity).__name__} (id: {getattr(entity, 'id', 'N/A')}) from {category}, but it was already removed")
            # Log remaining collected OreItems
            if category == "ore_items":
                collected_items = [e.id for e in self.entities[category] if getattr(e, 'collected', False)]
                if collected_items:
                    logger.warning(f"Found {len(collected_items)} OreItems still in list with collected=True: {collected_items}")
            logger.debug(f"Updated {category}, count after: {len(self.entities[category])}")

    def draw(self, screen, camera_x, camera_y):
        """Draw all entities using their respective draw methods."""
        for category in self.entities:
            for entity in self.entities[category]:
                entity.draw(screen, camera_x, camera_y)
        logger.debug("All entities drawn")