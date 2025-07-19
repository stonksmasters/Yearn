import pygame
import random
import logging
import time
from settings import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]

class Player:
    def __init__(self, upgrades, world):
        self.rect = pygame.Rect(NUM_COLS * TILE_SIZE // 2, 0, 16, 32)
        self.pos_x = self.rect.x
        self.pos_y = self.rect.y
        self.vx = 0.0
        self.vy = 0.0
        self.target_vx = 0.0
        self.on_ground = False
        self.coyote_timer = 0.0
        self.max_health = 100
        self.health = self.max_health
        self.cash = 0
        self.quota_buffer = 0
        self.day_extension = 0
        self.efficiency_boost = 1.0
        self.inventory = {'dynamite': 0, 'health_pack': 0, 'earthquake': 0, 'depth_charge': 0, 'bat_wing': 0, 'goblin_tooth': 0}
        self.max_ore_slots = 9
        self.ore_slots = [None] * self.max_ore_slots  # Each slot: {'type': str, 'value_per_unit': float, 'count': int}
        self.active_effects = {
            "speed_boost": {"active": False, "duration": 0.0},
            "safety_bubble": {"active": False, "duration": 0.0},
            "auto_miner": {"active": False, "duration": 0.0},
            "xray_vision": {"active": False, "duration": 0.0}
        }
        self.mining_range = 2.0
        self.ore_pickup_range = 3.0  # Initial ore pickup range: 3 blocks
        self.cash_multiplier = 1.0
        self.jump_boost = 1.0
        self.ore_scanner = False
        self.lucky_miner = False
        self.ore_magnet = False
        self.rock_damage_reduction = 0.0
        self.mining_speed_boost = 1.0
        self.fatigue_reduction = 0.0
        self.aoe_mining = 0
        self.melee_upgrade = False
        self.blaster = False
        self.quantum_pickaxe = False
        self.shield_generator = False
        self.current_upgrades = []
        self.world = world
        self.pick_index = 0
        self.pick_speed = upgrades['pickaxes'][0]['speed']
        self.last_ore_added = None  # Track last ore added for debugging
        self.last_ore_pos = None  # Track position of last ore added
        logger.debug(f"Player initialized with ore_pickup_range={self.ore_pickup_range}, fatigue_reduction={self.fatigue_reduction}")

    def add_ore(self, ore_type, value_per_unit, count=1, ore_pos=None):
        """Add a specified count of ores to the inventory, return True if successful."""
        if count <= 0:
            logger.warning(f"Invalid count {count} for {ore_type}, skipping add_ore")
            return False
        if value_per_unit > 1000:
            logger.warning(f"Suspiciously high value_per_unit ${value_per_unit} for {ore_type}, possible multiplier error")
        if self.last_ore_added == (ore_type, value_per_unit) and self.last_ore_pos == ore_pos:
            logger.warning(f"Repeated add_ore call for {ore_type} at {ore_pos}, value_per_unit=${value_per_unit:.2f}")
            return False
        self.last_ore_added = (ore_type, value_per_unit)
        self.last_ore_pos = ore_pos
        for slot in self.ore_slots:
            if slot and slot['type'] == ore_type and abs(slot['value_per_unit'] - value_per_unit) < 0.01 and slot['count'] + count <= 64:
                slot['count'] += count
                logger.debug(f"Added {count} {ore_type} to existing slot, count now {slot['count']}, value_per_unit=${value_per_unit:.2f}, pos={ore_pos}")
                return True
        for i in range(self.max_ore_slots):
            if self.ore_slots[i] is None:
                self.ore_slots[i] = {'type': ore_type, 'value_per_unit': value_per_unit, 'count': count}
                logger.debug(f"Added {count} {ore_type} to new slot {i}, value_per_unit=${value_per_unit:.2f}, pos={ore_pos}")
                return True
        logger.debug(f"Failed to add {count} {ore_type}, inventory full, pos={ore_pos}")
        return False

    def get_ore_inventory(self):
        return self.ore_slots

    def clear_ore_inventory(self, game):
        """Clear ore inventory and return total cash value."""
        total_value = 0
        for slot in self.ore_slots:
            if slot:
                depth_zone = game.world.get_depth_zone(int(self.rect.centery // TILE_SIZE))
                slot_value = slot['value_per_unit'] * slot['count'] * depth_zone["value_scale"]
                if slot['type'] == "diamond":
                    slot_value *= 2
                if self.lucky_miner and random.random() < 0.1:
                    slot_value *= 2
                slot_value *= self.cash_multiplier * game.bonus_multiplier
                total_value += slot_value
        self.ore_slots = [None] * self.max_ore_slots
        logger.debug(f"Cleared ore inventory, total value=${total_value:.2f}")
        return total_value

    def apply_effect(self, effect, duration):
        if effect in self.active_effects:
            self.active_effects[effect]["active"] = True
            self.active_effects[effect]["duration"] = duration
            logger.debug(f"Applied effect {effect} for {duration}s")

    def add_to_inventory(self, item_id):
        self.inventory[item_id] = self.inventory.get(item_id, 0) + 1
        logger.debug(f"Added {item_id} to inventory: {self.inventory[item_id]}")

    def use_item(self, item_id):
        if item_id in self.inventory and self.inventory[item_id] > 0:
            self.inventory[item_id] -= 1
            logger.debug(f"Used {item_id}, remaining: {self.inventory[item_id]}")
            return True
        return False

    def drop_inventory(self):
        dropped = []
        available_items = [(k, v) for k, v in self.inventory.items() if v > 0]
        if available_items:
            for _ in range(random.randint(1, 2)):
                if not available_items:
                    break
                item_type, count = random.choice(available_items)
                self.inventory[item_type] = max(0, self.inventory[item_type] - 1)
                dropped.append((item_type, 1))
                available_items = [(k, v) for k, v in self.inventory.items() if v > 0]
        return dropped

    def throw_item(self, game, ore_items):
        item_list = [(k, v) for k, v in self.inventory.items() if v > 0]
        if item_list:
            item_type, _ = random.choice(item_list)
            if self.use_item(item_type):
                value = game.ores_cfg.get(item_type, {"value": 0})["value"]
                ore_items.append(OreItem(self.rect.centerx, self.rect.centery, item_type, value, game.ores_cfg))
                logger.debug(f"Threw {item_type} at ({self.rect.centerx}, {self.rect.centery})")

    def update(self, dt, world, keys, game=None):
        """Update player state, movement, and ore collection."""
        # Update active effects
        for effect_name, effect in self.active_effects.items():
            if effect["active"]:
                effect["duration"] -= dt
                if effect["duration"] <= 0:
                    effect["active"] = False
                    if effect_name == "speed_boost":
                        self.mining_speed_boost = max(1.0, self.mining_speed_boost - 0.5)
                    elif effect_name == "safety_bubble":
                        self.rock_damage_reduction = max(0.0, self.rock_damage_reduction - 0.2)
                    logger.debug(f"Effect {effect_name} expired")

        # Handle movement input
        self.target_vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.target_vx = -MOVE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.target_vx = MOVE_SPEED
        if (keys[pygame.K_SPACE] or keys[pygame.K_w]) and (self.on_ground or self.coyote_timer > 0):
            self.vy = -JUMP_VELOCITY * self.jump_boost
            self.on_ground = False
            self.coyote_timer = 0
            logger.debug(f"Player jumped, vy={self.vy}")

        # Update velocity and position
        self.vx += (self.target_vx - self.vx) * 0.3
        if self.active_effects["speed_boost"]["active"]:
            self.vx *= 1.5
        self.pos_x += self.vx * dt
        self.vy += GRAVITY * dt
        self.pos_y += self.vy * dt
        self.rect.x = int(self.pos_x)
        self.rect.y = int(self.pos_y)

        # Handle collisions with world blocks
        self.on_ground = False
        for block in world.get_surrounding_blocks(self.rect):
            if self.vy > 0 and self.rect.bottom <= block.top + 8 and self.rect.bottom > block.top - 8 and self.rect.left < block.right and self.rect.right > block.left:
                self.rect.bottom = block.top
                self.pos_y = self.rect.y
                self.vy = 0
                self.on_ground = True
                self.coyote_timer = 0.1
            elif self.vy < 0 and self.rect.top >= block.bottom - 8 and self.rect.top < block.bottom + 8 and self.rect.left < block.right and self.rect.right > block.left:
                self.rect.top = block.bottom
                self.pos_y = self.rect.y
                self.vy = 0
            elif self.vx > 0 and self.rect.right <= block.left + 8 and self.rect.right > block.left - 8 and self.rect.top < block.bottom and self.rect.bottom > block.top:
                self.rect.right = block.left
                self.pos_x = self.rect.x
                self.vx = 0
            elif self.vx < 0 and self.rect.left >= block.right - 8 and self.rect.left < block.right + 8 and self.rect.top < block.bottom and self.rect.bottom > block.top:
                self.rect.left = block.right
                self.pos_x = self.rect.x
                self.vx = 0

        # Handle ore collection
        if game and "ore_items" in game.entity_manager.entities:
            pickup_range = self.ore_pickup_range * TILE_SIZE
            if self.ore_magnet:
                pickup_range *= 2  # Double pickup range with ore_magnet
            for ore_item in game.entity_manager.entities["ore_items"][:]:
                if ore_item.collected or ore_item.collecting:
                    continue
                if time.time() - ore_item.creation_time < 0.5:
                    continue
                dx = self.rect.centerx - ore_item.rect.centerx
                dy = self.rect.centery - ore_item.rect.centery
                distance = (dx ** 2 + dy ** 2) ** 0.5
                if distance <= pickup_range:
                    ore_item.collecting = True
                    ore_item.target_player = self
                    ore_item.collect_timer = 0.5  # Reset timer for animation
                    logger.debug(f"Initiated collection animation for {ore_item.ore_type} at distance {distance:.2f}, pos=({ore_item.rect.x}, {ore_item.rect.y})")
                else:
                    logger.debug(f"Ore {ore_item.ore_type} at ({ore_item.rect.x}, {ore_item.rect.y}) outside pickup range {pickup_range:.2f}, distance {distance:.2f}")

        # Update position constraints
        self.pos_x = max(0, min(self.pos_x, NUM_COLS * TILE_SIZE - self.rect.width))
        self.pos_y = max(0, min(self.pos_y, MAX_DEPTH * TILE_SIZE - self.rect.height))
        self.rect.x = int(self.pos_x)
        self.rect.y = int(self.pos_y)

        # Check health
        if self.health <= 0:
            logger.debug("Player health reached zero")