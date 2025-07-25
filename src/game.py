import asyncio
import pygame
import platform
import logging
import random
import math
import time
import json
import settings
from event_handler import EventHandler
from renderer import Renderer
from state_manager import StateManager
from entities import EntityManager, OreScanner, OreItem, BlasterShot, Explosion, Enemy
from utils import load_sound, calculate_distance, trigger_screen_shake, trigger_screen_flash, spawn_ore_item, spawn_particles, aoe_mining
from world import World
from player import Player
from ui import UI
from data import load_ores, load_upgrades
from save_load import load_game, save_game

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing game.py")

class Game:
    class RemotePlayer:
        def __init__(self, player_id, x, y, health):
            self.player_id = player_id
            self.x = x
            self.y = y
            self.health = health
            self.rect = pygame.Rect(x, y, 16, 32)  # Assuming player size

        def update(self, x, y, health):
            self.x = x
            self.y = y
            self.health = health
            self.rect.x = x
            self.rect.y = y

    def __init__(self, upgrades_cfg, ores_cfg):
        """Initialize the game with configurations and core components."""
        logger.info("Initializing Game")
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
        pygame.display.set_caption("Yearn - Ultimate Miner")
        self.event_handler = EventHandler(self)
        self.renderer = Renderer(self.screen, settings)
        self.state_manager = StateManager()
        self.entity_manager = EntityManager()
        self.world = World()
        self.players = [Player(upgrades_cfg, self.world)]
        self.remote_players = {}  # Dictionary to store remote players
        self.ore_scanner = OreScanner(self.players[0], self.world)
        self.ui = UI(pygame.font.SysFont(settings.FONT_NAME, settings.FONT_SIZE))
        self.ores_cfg = ores_cfg
        self.upgrades_cfg = upgrades_cfg
        self.move_speed = settings.MOVE_SPEED
        self.jump_velocity = settings.JUMP_VELOCITY
        self.mining = False
        self.mine_start = 0.0
        self.mine_target = None
        self.mining_progress = 0.0
        self.last_mining_stage = 0
        self.mining_fatigue = 0.0
        self.mining_fatigue_timer = 0.0
        self.camera_x = self.players[0].rect.centerx - settings.WIDTH // 2
        self.camera_y = max(0, self.players[0].rect.centery - settings.HEIGHT // 2)
        self.target_camera_x = self.camera_x
        self.target_camera_y = self.camera_y
        self.camera_smoothing = 0.1
        self.running = True
        self.shake_timer = 0.0
        self.shake_intensity = 0
        self.last_sound_time = time.time()
        self.debug_message = None
        self.debug_message_timer = 0.0
        self.flash_timer = 0.0
        self.flash_color = settings.WHITE
        self.show_debug = False
        self.show_minimap = False
        self.pulse_timer = 0.0
        self.landed = False
        self.day = 1
        self.quota = settings.QUOTA_BASE
        self.cash_earned_today = 0
        self.day_start_time = time.time()
        self.time_left = settings.DAY_DURATION
        self.grace_period = False
        self.bonus_multiplier = 1.0
        self.ores_mined = 0
        self.diamonds_mined = 0
        self.treasure_notification = None
        self.treasure_notification_timer = 0.0
        self.lava_hazard_active = False
        self.lava_damage_timer = 0.0
        self.auto_mined_blocks = []
        self.inventory_full_notification = None
        self.inventory_full_timer = 0.0
        self.ore_collect_notification = None
        self.ore_collect_timer = 0.0
        self.milestones = {
            "depth": {10000 * i: False for i in range(1, 11)},
            "ores_mined": {1000 * i: False for i in range(1, 11)},
            "diamonds_mined": {10 * i: False for i in range(1, 6)}
        }
        self.shop_unlocks = {
            1000: ["ore_magnet"],
            5000: ["auto_miner_drone", "blaster"],
            10000: ["teleporter"],
            20000: ["xray_vision"],
            50000: ["cash_multiplier"],
            75000: ["quantum_pickaxe", "shield_generator"]
        }
        # Multiplayer attributes
        self.websocket = None
        self.player_id = None
        self.lobby_code = None
        self.mode = None  # Initialize as None until selected
        self.message_queue = []
        self.last_position_send_time = time.time()
        self.position_send_interval = 0.1
        # Load background music
        try:
            pygame.mixer.music.load("assets/backgroundmusic.wav")
            pygame.mixer.music.set_volume(settings.SOUND_VOLUME)
            pygame.mixer.music.play(-1)
            logger.info("Background music loaded and started")
        except pygame.error as e:
            logger.error(f"Failed to load background music: {e}")
        # Load sounds
        self.mining_sound = load_sound("mining.wav")
        self.item_sound = load_sound("item_use.wav", "mining.wav")
        self.landing_sound = load_sound("landing.wav", "mining.wav")
        self.drop_sound = load_sound("item_use.wav", "mining.wav")
        self.treasure_sound = load_sound("item_use.wav", "item_use.wav")
        self.bat_sound = load_sound("mining.wav", "mining.wav")
        self.goblin_sound = load_sound("mining.wav", "mining.wav")
        self.iron_sound = load_sound("item_use.wav", "item_use.wav")
        self.rare_ore_sound = load_sound("item_use.wav", "item_use.wav")
        self.diamond_sound = load_sound("item_use.wav", "item_use.wav")
        self.inventory_full_sound = load_sound("item_use.wav", "mining.wav")
        self.ore_collect_sound = load_sound("item_use.wav", "mining.wav")
        self.fatigue_sound = load_sound("item_use.wav", "mining.wav")
        loaded = load_game(self.players[0], self.upgrades_cfg)
        if loaded[0] is not None:
            self.world.block_cols, self.day, self.quota, self.cash_earned_today, self.time_left = loaded
            self.world.load_from_block_cols(self.world.block_cols)
            self.day_start_time = time.time() - (settings.DAY_DURATION + self.players[0].day_extension - self.time_left)
            self.mining = False
            self.mine_target = None
            self.mining_progress = 0.0
            self.last_mining_stage = 0
            logger.info("Game loaded successfully")

    def create_lobby(self):
        """Send request to create a new lobby."""
        if self.websocket and self.mode == "online_coop":
            self.send_message({"action": "create_lobby"})
            logger.info("Requested lobby creation")
        else:
            self.ui.lobby_message = "Cannot create lobby: Not in online mode"
            self.ui.lobby_message_timer = 2.0
            logger.warning("Lobby creation failed: Not in online mode or no websocket")

    def join_lobby(self, lobby_code):
        """Send request to join a lobby with the given code."""
        if self.websocket and self.mode == "online_coop":
            self.send_message({"action": "join_lobby", "lobby_code": lobby_code.upper()})
            logger.info(f"Attempting to join lobby {lobby_code}")
        else:
            self.ui.lobby_message = "Cannot join lobby: Not in online mode"
            self.ui.lobby_message_timer = 2.0
            logger.warning("Lobby join failed: Not in online mode or no websocket")

    def send_message(self, message):
        """Queue a message to be sent to the server."""
        self.message_queue.append(message)

    def update_remote_player(self, player_id, x, y, health):
        """Update local or remote player state."""
        if player_id == self.player_id:
            self.players[0].pos_x = x
            self.players[0].pos_y = y
            self.players[0].rect.x = x
            self.players[0].rect.y = y
            self.players[0].health = health
        else:
            if player_id not in self.remote_players:
                self.remote_players[player_id] = self.RemotePlayer(player_id, x, y, health)
            else:
                self.remote_players[player_id].update(x, y, health)

    def remove_remote_player(self, player_id):
        """Remove a remote player."""
        if player_id in self.remote_players:
            del self.remote_players[player_id]
            logger.info(f"Removed remote player {player_id}")

    def handle_spawn_entity(self, entity_id, entity_data):
        """Handle spawning of entities from server."""
        if entity_data["type"] == "ore":
            ore = OreItem(entity_data["x"], entity_data["y"], entity_data["ore_type"], entity_data["value"], self.ores_cfg, entity_id=entity_id)
            self.entity_manager.add(ore, "ore_items")

    def remove_ore(self, ore_id):
        """Remove an ore item by ID."""
        self.entity_manager.remove_ore(ore_id)

    @property
    def ore_items(self):
        return self.entity_manager.entities["ore_items"]

    def add_ore_to_inventory(self, player, ore_type, count, value_per_unit, ore_pos=None):
        """Add an ore to the player's inventory."""
        if self.mode == "online_coop":
            # In online mode, server handles inventory; client updates via messages
            return False
        base_value = value_per_unit / self.world.get_depth_zone(int(player.rect.centery // settings.TILE_SIZE))["value_scale"]
        for i, slot in enumerate(player.ore_slots):
            if slot is None:
                player.ore_slots[i] = {'type': ore_type, 'count': count, 'value_per_unit': base_value}
                logger.debug(f"Added {count} {ore_type} to slot {i}, value_per_unit=${base_value:.2f}, pos={ore_pos}")
                self.ore_collect_notification = f"Collected {count} {ore_type}"
                self.ore_collect_timer = 2.0
                if self.ore_collect_sound:
                    self.ore_collect_sound.play()
                return True
            elif slot['type'] == ore_type and abs(slot['value_per_unit'] - base_value) < 0.01 and slot['count'] < 64:
                slot['count'] += count
                logger.debug(f"Added {count} {ore_type} to existing slot {i}, new count={slot['count']}, value_per_unit=${base_value:.2f}, pos={ore_pos}")
                self.ore_collect_notification = f"Collected {count} {ore_type}"
                self.ore_collect_timer = 2.0
                if self.ore_collect_sound:
                    self.ore_collect_sound.play()
                return True
        self.inventory_full_notification = "Inventory Full! Drop off ores at surface"
        self.inventory_full_timer = 3.0
        if self.inventory_full_sound:
            self.inventory_full_sound.play()
        logger.debug(f"Failed to add {count} {ore_type}, inventory full, pos={ore_pos}")
        return False

    def save_and_quit(self):
        """Save game state and stop running (singleplayer only)."""
        if self.mode != "online_coop":
            save_game(self.players[0], self.world, self.day, self.quota, self.cash_earned_today, self.upgrades_cfg, self.time_left)
        self.running = False
        logger.info("Game saved and quit")

    def quit(self):
        """Quit the game."""
        pygame.mixer.music.stop()
        pygame.quit()
        raise SystemExit

    def start_game(self):
        """Start the game from the start menu."""
        if self.mode == "online_coop" and not self.lobby_code:
            self.ui.lobby_message = "Cannot start: Not in a lobby"
            self.ui.lobby_message_timer = 2.0
            logger.warning("Cannot start online_coop: No lobby code")
            return
        if self.mode == "local_coop":
            self.players.append(Player(self.upgrades_cfg, self.world))
            self.players[1].pos_x = self.players[0].pos_x + 50
            self.players[1].rect.x = self.players[1].pos_x
            self.players[1].pick_index = self.players[0].pick_index
            self.players[1].pick_speed = self.players[0].pick_speed
            self.players[1].current_upgrades = self.players[0].current_upgrades[:]
            self.players[1].mining_speed_boost = self.players[0].mining_speed_boost
            self.players[1].jump_boost = self.players[0].jump_boost
            self.players[1].aoe_mining = self.players[0].aoe_mining
            self.players[1].rock_damage_reduction = self.players[0].rock_damage_reduction
            self.players[1].lucky_miner = self.players[0].lucky_miner
            self.players[1].ore_magnet = self.players[0].ore_magnet
            self.players[1].ore_pickup_range = self.players[0].ore_pickup_range
            self.players[1].melee_upgrade = self.players[0].melee_upgrade
            self.players[1].blaster = self.players[0].blaster
            self.players[1].quantum_pickaxe = self.players[0].quantum_pickaxe
            self.players[1].shield_generator = self.players[0].shield_generator
            self.players[1].inventory = {'dynamite': 0, 'health_pack': 0, 'earthquake': 0, 'depth_charge': 0, 'bat_wing': 0, 'goblin_tooth': 0}
            self.players[1].ore_slots = [None] * self.players[1].max_ore_slots
            logger.info("Added second player for local co-op")
        self.day_start_time = time.time()
        self.time_left = settings.DAY_DURATION + self.players[0].day_extension
        self.state_manager.set_state("playing", self)
        logger.info(f"Started game in {self.mode} mode")

    def toggle_pause(self):
        """Toggle between playing and paused states."""
        if self.state_manager.current_state == "playing":
            self.time_left = settings.DAY_DURATION + self.players[0].day_extension - (time.time() - self.day_start_time)
            self.state_manager.set_state("paused", self)
            pygame.mixer.music.pause()
            logger.debug("Game paused, music paused")
        else:
            self.day_start_time = time.time() - (settings.DAY_DURATION + self.players[0].day_extension - self.time_left)
            self.state_manager.set_state("playing", self)
            pygame.mixer.music.unpause()
            logger.debug("Game resumed, music unpaused")

    def toggle_upgrade_menu(self):
        """Toggle the upgrade menu visibility."""
        self.ui.show_upgrade_menu = not self.ui.show_upgrade_menu
        if self.ui.show_upgrade_menu:
            self.ui.show_inventory = False
            self.ui.selected_upgrade = 0
            self.ui.menu_mode = "pickaxes"
            self.ui.shop_offset = 0
            logger.info("Opened upgrade menu")
        else:
            logger.info("Closed upgrade menu")

    def toggle_inventory_menu(self):
        """Toggle the inventory menu visibility."""
        self.ui.show_inventory = not self.ui.show_inventory
        if self.ui.show_inventory:
            self.ui.show_upgrade_menu = False
            self.ui.selected_item = 0
            logger.info("Opened inventory menu")
        else:
            logger.info("Closed inventory menu")

    def toggle_second_player(self):
        """Add or remove the second player for local co-op."""
        if self.mode != "local_coop":
            self.ui.lobby_message = "Second player only available in local co-op"
            self.ui.lobby_message_timer = 2.0
            logger.info("Cannot toggle second player: Not in local co-op mode")
            return
        if len(self.players) == 1:
            self.players.append(Player(self.upgrades_cfg, self.world))
            self.players[1].pos_x = self.players[0].pos_x + 50
            self.players[1].rect.x = self.players[1].pos_x
            self.players[1].pick_index = self.players[0].pick_index
            self.players[1].pick_speed = self.players[0].pick_speed
            self.players[1].current_upgrades = self.players[0].current_upgrades[:]
            self.players[1].mining_speed_boost = self.players[0].mining_speed_boost
            self.players[1].jump_boost = self.players[0].jump_boost
            self.players[1].aoe_mining = self.players[0].aoe_mining
            self.players[1].rock_damage_reduction = self.players[0].rock_damage_reduction
            self.players[1].lucky_miner = self.players[0].lucky_miner
            self.players[1].ore_magnet = self.players[0].ore_magnet
            self.players[1].ore_pickup_range = self.players[0].ore_pickup_range
            self.players[1].melee_upgrade = self.players[0].melee_upgrade
            self.players[1].blaster = self.players[0].blaster
            self.players[1].quantum_pickaxe = self.players[0].quantum_pickaxe
            self.players[1].shield_generator = self.players[0].shield_generator
            self.players[1].inventory = {'dynamite': 0, 'health_pack': 0, 'earthquake': 0, 'depth_charge': 0, 'bat_wing': 0, 'goblin_tooth': 0}
            self.players[1].ore_slots = [None] * self.players[1].max_ore_slots
            logger.info("Added second player for local co-op")
        else:
            self.players.pop(1)
            logger.info("Removed second player")

    def use_item(self, item_id):
        """Use an item from the player's inventory with enhanced effects."""
        if self.mode == "online_coop":
            self.send_message({"action": "use_item", "item_id": item_id, "player_id": self.player_id})
            return True
        if self.players[0].use_item(item_id):
            if item_id == "dynamite":
                self.entity_manager.add(Explosion(self.players[0].rect.centerx, self.players[0].rect.centery, 5 * settings.TILE_SIZE), "explosions")
                aoe_mining(self, self.players[0].rect.centerx, self.players[0].rect.centery, 5)
                trigger_screen_flash(self, 0.2, (255, 255, 0))
                self.debug_message = "Used Dynamite"
                self.debug_message_timer = 2.0
                if self.item_sound:
                    self.item_sound.play()
                spawn_particles(self, self.players[0].rect.centerx, self.players[0].rect.centery, 10, sparkle=True)
                logger.info("Used dynamite")
            elif item_id == "health_pack":
                self.players[0].health = min(self.players[0].max_health, self.players[0].health + 50)
                trigger_screen_flash(self, 0.2, (0, 255, 0))
                self.debug_message = "Used Health Pack: +50 HP"
                self.debug_message_timer = 2.0
                if self.item_sound:
                    self.item_sound.play()
                spawn_particles(self, self.players[0].rect.centerx, self.players[0].rect.centery, 5, sparkle=True, color=(0, 255, 0))
                logger.info("Used health pack")
            elif item_id == "earthquake":
                center_x = int(self.players[0].rect.centerx // settings.TILE_SIZE)
                for depth in range(int(self.players[0].rect.centery // settings.TILE_SIZE), settings.MAX_DEPTH):
                    if 0 <= center_x < settings.NUM_COLS and 0 <= depth < settings.MAX_DEPTH:
                        block = self.world.block_at(center_x, depth)
                        if block and block != "empty":
                            self.send_message({
                                "action": "mine_block",
                                "block_x": center_x,
                                "block_y": depth,
                                "player_id": self.player_id
                            })
                self.entity_manager.add(Explosion(self.players[0].rect.centerx, settings.HEIGHT, 3 * settings.TILE_SIZE), "explosions")
                trigger_screen_flash(self, 0.2, (255, 255, 0))
                self.debug_message = "Used Earthquake"
                self.debug_message_timer = 2.0
                if self.item_sound:
                    self.item_sound.play()
                logger.info("Used earthquake")
            elif item_id == "depth_charge":
                mx, my = pygame.mouse.get_pos()
                world_mx = mx + self.camera_x
                world_my = my + self.camera_y
                self.entity_manager.add(Explosion(world_mx, world_my, 3 * settings.TILE_SIZE), "explosions")
                aoe_mining(self, world_mx, world_my, 3)
                trigger_screen_flash(self, 0.2, (255, 255, 0))
                self.debug_message = "Used Depth Charge"
                self.debug_message_timer = 2.0
                if self.item_sound:
                    self.item_sound.play()
                spawn_particles(self, world_mx, world_my, 10, sparkle=True)
                logger.info("Used depth charge")
            elif item_id == "bat_wing":
                self.players[0].active_effects['speed_boost'] = {'active': True, 'end_time': time.time() + 30}
                self.players[0].mining_speed_boost += 0.5
                trigger_screen_flash(self, 0.2, (128, 0, 128))
                self.debug_message = "Used Bat Wing: +0.5x Mining Speed (30s)"
                self.debug_message_timer = 2.0
                if self.item_sound:
                    self.item_sound.play()
                spawn_particles(self, self.players[0].rect.centerx, self.players[0].rect.centery, 5, sparkle=True, color=(128, 0, 128))
                logger.info("Used bat wing: Speed boost")
            elif item_id == "goblin_tooth":
                self.players[0].active_effects['safety_bubble'] = {'active': True, 'end_time': time.time() + 30}
                self.players[0].rock_damage_reduction += 0.2
                trigger_screen_flash(self, 0.2, (0, 128, 128))
                self.debug_message = "Used Goblin Tooth: +20% Damage Resist (30s)"
                self.debug_message_timer = 2.0
                if self.item_sound:
                    self.item_sound.play()
                spawn_particles(self, self.players[0].rect.centerx, self.players[0].rect.centery, 5, sparkle=True, color=(0, 128, 128))
                logger.info("Used goblin tooth: Damage resist")
            return True
        return False

    def use_inventory_item(self):
        """Use the selected item from the inventory."""
        item_list = list(self.players[0].inventory.items())
        if item_list and self.ui.selected_item < len(item_list):
            item_id = item_list[self.ui.selected_item][0]
            self.use_item(item_id)

    def purchase_upgrade(self):
        """Purchase the selected upgrade from the upgrade menu."""
        if self.ui.menu_mode == "pickaxes":
            pickaxes = self.upgrades_cfg.get("pickaxes", [])
            if pickaxes and self.ui.selected_upgrade < len(pickaxes):
                upgrade = pickaxes[self.ui.selected_upgrade]
                if self.players[0].cash >= upgrade["cost"] and not upgrade.get("unlocked", False):
                    for player in self.players:
                        player.cash -= upgrade["cost"]
                        player.pick_index = self.ui.selected_upgrade
                        player.pick_speed = upgrade["speed"]
                    upgrade["unlocked"] = True
                    trigger_screen_flash(self, 0.2, (0, 255, 0))
                    self.debug_message = f"Purchased {upgrade['name']}"
                    self.debug_message_timer = 2.0
                    self.ui.show_upgrade_menu = False
                    if self.item_sound:
                        self.item_sound.play()
                    logger.info(f"Purchased pickaxe: {upgrade['name']}")
                else:
                    self.ui.lobby_message = "Cannot afford or already unlocked"
                    self.ui.lobby_message_timer = 2.0
                    logger.debug(f"Failed to purchase pickaxe: {upgrade['name']}, cash: {self.players[0].cash}, unlocked: {upgrade.get('unlocked', False)}")
        else:
            shop_items = self.upgrades_cfg.get("shop", [])
            if shop_items and self.ui.selected_upgrade < len(shop_items):
                item = shop_items[self.ui.selected_upgrade]
                if item.get("permanent", False) and item.get("unlocked", False):
                    self.ui.lobby_message = "Already purchased"
                    self.ui.lobby_message_timer = 2.0
                    logger.debug(f"Cannot purchase {item['name']}, already unlocked")
                else:
                    prereq_met = True
                    if item["id"] == "quantum_pickaxe" and not self.players[0].aoe_mining >= 2:
                        prereq_met = False
                        self.ui.lobby_message = "Requires AOE Mining II"
                        self.ui.lobby_message_timer = 2.0
                        logger.debug("Quantum Pickaxe purchase failed: AOE Mining II required")
                    elif item["id"] == "shield_generator" and not self.players[0].rock_damage_reduction > 0:
                        prereq_met = False
                        self.ui.lobby_message = "Requires Damage Resistance"
                        self.ui.lobby_message_timer = 2.0
                        logger.debug("Shield Generator purchase failed: Damage Resistance required")
                    elif item["id"] == "ore_pickup_range_2":
                        if not any(i["id"] == "ore_pickup_range" and i.get("unlocked", False) for i in shop_items):
                            prereq_met = False
                            self.ui.lobby_message = "Requires Ore Pickup Range I"
                            self.ui.lobby_message_timer = 2.0
                            logger.debug("Ore Pickup Range II purchase failed: Ore Pickup Range I required")
                        elif self.players[0].ore_pickup_range >= 5.0:
                            prereq_met = False
                            self.ui.lobby_message = "Max Ore Pickup Range Reached"
                            self.ui.lobby_message_timer = 2.0
                            logger.debug("Ore Pickup Range II purchase failed: Max range reached")
                    if prereq_met and self.players[0].cash >= item["cost"]:
                        self.players[0].cash -= item["cost"]
                        self.ui.apply_upgrade(item, self.players[0])
                        trigger_screen_flash(self, 0.2, (255, 255, 0))
                        self.debug_message = f"Purchased {item['name']}"
                        self.debug_message_timer = 2.0
                        self.ui.show_upgrade_menu = False
                        if self.item_sound:
                            self.item_sound.play()
                        logger.info(f"Purchased shop item: {item['name']}")
                    else:
                        self.ui.lobby_message = "Cannot afford or prerequisites not met"
                        self.ui.lobby_message_timer = 2.0
                        logger.debug(f"Failed to purchase shop item: {item['name']}, cash: {self.players[0].cash}")

    def use_melee(self):
        """Perform a melee attack on nearby enemies."""
        for enemy in self.entity_manager.entities["enemies"]:
            if abs(enemy.rect.centerx - self.players[0].rect.centerx) <= 2 * settings.TILE_SIZE and abs(enemy.rect.centery - self.players[0].rect.centery) <= 2 * settings.TILE_SIZE:
                enemy.health -= 10 * (1.5 if self.players[0].melee_upgrade else 1.0)
                trigger_screen_flash(self, 0.2, (255, 0, 0))
                self.debug_message = f"Melee Hit {enemy.type}"
                self.debug_message_timer = 2.0
                if self.goblin_sound and enemy.type == "goblin":
                    self.goblin_sound.play()
                elif self.bat_sound and enemy.type == "bat":
                    self.bat_sound.play()
                elif self.rare_ore_sound and enemy.type == "abyss_wraith":
                    self.rare_ore_sound.play()
                logger.debug(f"Melee hit {enemy.type} at ({enemy.rect.x}, {enemy.rect.y})")

    def handle_mining(self, mouse_pos):
        """Start mining at the specified position."""
        if self.mining_fatigue >= 1.0:
            self.ui.lobby_message = "Mining Fatigue: Rest to recover"
            self.ui.lobby_message_timer = 1.0
            logger.debug("Mining blocked by fatigue")
            if self.fatigue_sound and (time.time() - self.last_sound_time) >= 0.5:
                self.fatigue_sound.set_volume(settings.SOUND_VOLUME * 0.5)
                self.fatigue_sound.play()
                self.last_sound_time = time.time()
            trigger_screen_flash(self, 0.2, (255, 0, 0))
            if self.mining:
                self.stop_mining()
            return
        world_mx = mouse_pos[0] + self.camera_x
        world_my = mouse_pos[1] + self.camera_y
        tx, ty = int(world_mx // settings.TILE_SIZE), int(world_my // settings.TILE_SIZE)
        block_type = self.world.block_at(tx, ty)
        if block_type and block_type not in ["empty", "grass"]:
            player_x, player_y = self.players[0].rect.center
            block_x, block_y = tx * settings.TILE_SIZE + settings.TILE_SIZE // 2, ty * settings.TILE_SIZE + settings.TILE_SIZE // 2
            distance = calculate_distance((player_x, player_y), (block_x, block_y))
            if distance <= self.players[0].mining_range * settings.TILE_SIZE:
                if self.mode == "online_coop":
                    self.send_message({"action": "mine_block", "block_x": tx, "block_y": ty, "player_id": self.player_id})
                    self.mining = False  # Server handles mining
                else:
                    depth_zone = self.world.get_depth_zone(ty)
                    fatigue_increment = 0.03 * depth_zone["value_scale"] / (self.players[0].mining_speed_boost * self.players[0].pick_speed) * (1.0 - self.players[0].fatigue_reduction)
                    self.mining_fatigue = min(self.mining_fatigue + fatigue_increment, 1.0)
                    self.mining = True
                    self.mine_target = (tx, ty)
                    self.mine_start = time.time()
                    self.mining_progress = self.world.get_block_state(tx, ty) / 3.0
                    spawn_particles(self, block_x, block_y, 3, rock_chip=True)
                    if self.mining_sound and (time.time() - self.last_sound_time) >= 0.2:
                        self.mining_sound.set_volume(settings.SOUND_VOLUME * settings.BLOCK_PITCHES.get(block_type, 1.0) * 0.7)
                        self.mining_sound.play()
                        self.last_sound_time = time.time()
                    logger.debug(f"Started mining {block_type} at ({tx}, {ty}), fatigue: {self.mining_fatigue:.2f}")
                if self.players[0].blaster:
                    self.handle_blaster_shot(world_mx, world_my)
                elif self.players[0].quantum_pickaxe:
                    self.handle_quantum_pickaxe(world_mx, world_my)
            else:
                self.mining = False
                self.mine_target = None
                self.mining_progress = 0.0
                self.last_mining_stage = 0
                self.ui.lobby_message = "Block out of range"
                self.ui.lobby_message_timer = 1.0
                logger.debug(f"Block at ({tx}, {ty}) out of mining range")
        else:
            self.mining = False
            self.mine_target = None
            self.mining_progress = 0.0
            self.last_mining_stage = 0
            self.ui.lobby_message = "No valid block to mine"
            self.ui.lobby_message_timer = 1.0
            logger.debug(f"No valid block to mine at ({tx}, {ty})")

    def stop_mining(self):
        """Stop mining and reset state."""
        self.mining = False
        self.mine_target = None
        self.mining_progress = 0.0
        self.last_mining_stage = 0
        logger.debug("Stopped mining")

    def handle_blaster_shot(self, world_mx, world_my):
        """Handle blaster shot."""
        if self.mode == "online_coop":
            tx, ty = int(world_mx // settings.TILE_SIZE), int(world_my // settings.TILE_SIZE)
            self.send_message({"action": "mine_block", "block_x": tx, "block_y": ty, "player_id": self.player_id})
        else:
            tx, ty = int(world_mx // settings.TILE_SIZE), int(world_my // settings.TILE_SIZE)
            self.entity_manager.add(BlasterShot(self.players[0].rect.centerx, self.players[0].rect.centery, 
                                                (world_mx - self.players[0].rect.centerx) * 3, 
                                                (world_my - self.players[0].rect.centery) * 3), "blaster_shots")
            if 0 <= tx < settings.NUM_COLS and 0 <= ty < settings.MAX_DEPTH:
                block = self.world.block_at(tx, ty)
                if block and block not in ["empty", "grass"]:
                    self.send_message({"action": "mine_block", "block_x": tx, "block_y": ty, "player_id": self.player_id})
                    self.debug_message = f"Blaster Shot at ({tx}, {ty})"
                    self.debug_message_timer = 2.0
            for enemy in self.entity_manager.entities["enemies"]:
                if enemy.rect.collidepoint(world_mx, world_my):
                    enemy.health -= 5
                    trigger_screen_flash(self, 0.2, (255, 0, 0))
                    self.debug_message = f"Blaster Hit {enemy.type}"
                    self.debug_message_timer = 2.0
                    if self.goblin_sound and enemy.type == "goblin":
                        self.goblin_sound.play()
                    elif self.bat_sound and enemy.type == "bat":
                        self.bat_sound.play()
                    elif self.rare_ore_sound and enemy.type == "abyss_wraith":
                        self.rare_ore_sound.play()
                    logger.debug(f"Blaster hit {enemy.type} at ({world_mx}, {world_my})")

    def handle_quantum_pickaxe(self, world_mx, world_my):
        """Handle quantum pickaxe."""
        if self.mode == "online_coop":
            tx, ty = int(world_mx // settings.TILE_SIZE), int(world_my // settings.TILE_SIZE)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if 0 <= tx + dx < settings.NUM_COLS and 0 <= ty + dy < settings.MAX_DEPTH:
                        self.send_message({"action": "mine_block", "block_x": tx + dx, "block_y": ty + dy, "player_id": self.player_id})
        else:
            tx, ty = int(world_mx // settings.TILE_SIZE), int(world_my // settings.TILE_SIZE)
            depth_zone = self.world.get_depth_zone(ty)
            self.mining_fatigue += 0.05 * depth_zone["value_scale"] * 9
            aoe_mining(self, world_mx, world_my, 1)
            trigger_screen_flash(self, 0.2, (0, 255, 255))
            self.debug_message = "Quantum Pickaxe Used"
            self.debug_message_timer = 2.0
            if self.mining_sound and (time.time() - self.last_sound_time) >= 0.3:
                self.mining_sound.set_volume(settings.SOUND_VOLUME * 0.9)
                self.mining_sound.play()
                self.last_sound_time = time.time()
            spawn_particles(self, world_mx, world_my, 12, sparkle=True, color=(0, 255, 255))
            logger.debug(f"Quantum Pickaxe used at ({tx}, {ty}), fatigue: {self.mining_fatigue:.2f}")

    def handle_auto_mining(self):
        """Handle auto-mining for players with auto-miner upgrade."""
        for player in self.players:
            if player.active_effects.get("auto_miner", {}).get("active", False) and not self.mining and random.random() < 0.05:
                center_x = int(player.rect.centerx // settings.TILE_SIZE)
                center_y = int(player.rect.centery // settings.TILE_SIZE)
                radius = 5
                for ty in range(center_y - radius, center_y + radius + 1):
                    for tx in range(center_x - radius, center_x + radius + 1):
                        if 0 <= tx < settings.NUM_COLS and 0 <= ty < settings.MAX_DEPTH and (tx, ty) not in self.auto_mined_blocks:
                            block = self.world.block_at(tx, ty)
                            if block in ['dirt', 'stone', 'cave_wall']:
                                self.send_message({
                                    "action": "mine_block",
                                    "block_x": tx,
                                    "block_y": ty,
                                    "player_id": self.player_id
                                })
                                self.auto_mined_blocks.append((tx, ty))
                                self.debug_message = f"Auto-Mining at ({tx}, {ty})"
                                self.debug_message_timer = 2.0

    def check_milestones(self):
        """Check and apply depth, ore, and diamond mining milestones."""
        depth = max(int(player.pos_y // settings.TILE_SIZE) for player in self.players)
        for milestone_depth, achieved in self.milestones["depth"].items():
            if depth >= milestone_depth and not achieved:
                self.milestones["depth"][milestone_depth] = True
                for player in self.players:
                    player.cash += 1000
                    player.inventory['health_pack'] = player.inventory.get('health_pack', 0) + 1
                for item_id in self.shop_unlocks.get(milestone_depth, []):
                    for item in self.upgrades_cfg.get('shop', []):
                        if item['id'] == item_id:
                            item['unlocked'] = True
                trigger_screen_flash(self, 0.2, (0, 255, 0))
                self.debug_message = f"Milestone: Reached Depth {milestone_depth} - +$1000, +1 Health Pack"
                self.debug_message_timer = 2.0
                logger.info(f"Achieved depth milestone: {milestone_depth}")
                if milestone_depth >= 75000:
                    self.lava_hazard_active = True
                    self.debug_message = "Warning: Lava Hazard Activated!"
                    self.debug_message_timer = 2.0
                    logger.info("Lava hazard activated at depth 75000")
        for milestone_ores, achieved in self.milestones["ores_mined"].items():
            if self.ores_mined >= milestone_ores and not achieved:
                self.milestones["ores_mined"][milestone_ores] = True
                for player in self.players:
                    player.cash += 500
                    player.inventory['dynamite'] = player.inventory.get('dynamite', 0) + 1
                trigger_screen_flash(self, 0.2, (0, 255, 0))
                self.debug_message = f"Milestone: Mined {milestone_ores} Ores - +$500, +1 Dynamite"
                self.debug_message_timer = 2.0
                logger.info(f"Achieved ores mined milestone: {milestone_ores}")
        for milestone_diamonds, achieved in self.milestones["diamonds_mined"].items():
            if self.diamonds_mined >= milestone_diamonds and not achieved:
                self.milestones["diamonds_mined"][milestone_diamonds] = True
                for player in self.players:
                    player.cash += 500
                    player.inventory['health_pack'] = player.inventory.get('health_pack', 0) + 1
                trigger_screen_flash(self, 0.3, (185, 242, 255))
                self.debug_message = f"Milestone: Mined {milestone_diamonds} Diamonds - +$500, +1 Health Pack"
                self.debug_message_timer = 2.0
                logger.info(f"Achieved diamonds mined milestone: {milestone_diamonds}")

    def setup(self):
        """Reset game state for a new game."""
        self.world = World()
        self.players = [Player(self.upgrades_cfg, self.world)]
        self.remote_players = {}
        self.ore_scanner = OreScanner(self.players[0], self.world)
        self.entity_manager = EntityManager()
        self.day = 1
        self.quota = settings.QUOTA_BASE
        self.cash_earned_today = 0
        self.day_start_time = time.time()
        self.time_left = settings.DAY_DURATION
        self.grace_period = False
        self.bonus_multiplier = 1.0
        self.ores_mined = 0
        self.diamonds_mined = 0
        self.lava_hazard_active = False
        self.lava_damage_timer = 0.0
        self.auto_mined_blocks = []
        self.mining_fatigue = 0.0
        self.mining_fatigue_timer = 0.0
        self.inventory_full_notification = None
        self.inventory_full_timer = 0.0
        self.ore_collect_notification = None
        self.ore_collect_timer = 0.0
        self.milestones = {
            "depth": {10000 * i: False for i in range(1, 11)},
            "ores_mined": {1000 * i: False for i in range(1, 11)},
            "diamonds_mined": {10 * i: False for i in range(1, 6)}
        }
        self.landed = False
        for pick in self.upgrades_cfg['pickaxes']:
            pick['unlocked'] = False
        self.upgrades_cfg['pickaxes'][0]['unlocked'] = True
        for item in self.upgrades_cfg.get('shop', []):
            item['unlocked'] = False
        self.players[0].inventory = {'dynamite': 0, 'health_pack': 0, 'earthquake': 0, 'depth_charge': 0, 'bat_wing': 0, 'goblin_tooth': 0}
        self.players[0].ore_slots = [None] * self.players[0].max_ore_slots
        trigger_screen_flash(self, 0.2, (0, 255, 0))
        self.debug_message = "Game Restarted"
        self.debug_message_timer = 2.0
        self.state_manager.set_state("start_menu", self)
        self.ui.show_start_menu = True
        self.ui.show_mode_menu = False
        self.ui.show_lobby_menu = False
        logger.info("Game restarted")

    def next_day(self):
        """Advance to the next day, updating quota and resetting state."""
        self.day += 1
        self.time_left = settings.DAY_DURATION + self.players[0].day_extension
        self.quota *= settings.QUOTA_INCREASE
        self.cash_earned_today = max(0, self.cash_earned_today - self.quota)
        self.players[0].cash += self.cash_earned_today
        self.day_start_time = time.time()
        self.grace_period = False
        self.bonus_multiplier = 1.0
        self.mining_fatigue = 0.0
        self.mining_fatigue_timer = 0.0
        self.inventory_full_notification = None
        self.inventory_full_timer = 0.0
        self.ore_collect_notification = None
        self.ore_collect_timer = 0.0
        trigger_screen_flash(self, 0.2, (0, 255, 0))
        self.debug_message = f"Day {self.day} started! New quota: ${self.quota:.2f}"
        self.debug_message_timer = 2.0
        self.state_manager.set_state("playing", self)
        logger.info(f"Starting day {self.day}, new quota: ${self.quota:.2f}")

    def update(self, dt):
        """Update game logic for the playing state."""
        # Skip updates if any menu is active
        if (self.ui.show_start_menu or self.ui.show_mode_menu or self.ui.show_lobby_menu or 
            self.ui.show_pause_menu or self.ui.show_upgrade_menu or self.ui.show_inventory or 
            self.ui.show_post_day_upgrades or self.ui.game_over):
            return

        if self.mode == "online_coop" and self.lobby_code:
            self.time_left = max(0, self.time_left - dt)
        else:
            self.time_left -= dt
        if self.time_left <= 0:
            if self.cash_earned_today >= self.quota:
                self.ui.select_post_day_upgrades(self.upgrades_cfg)
                self.state_manager.set_state("post_day_upgrades", self)
                logger.info("Day ended, quota met, showing post-day upgrades")
            else:
                self.state_manager.set_state("game_over", self)
                trigger_screen_flash(self, 0.2, (255, 0, 0))
                self.debug_message = "Game Over: Quota not met!"
                self.debug_message_timer = 2.0
                logger.info("Game over: Quota not met")
            return

        # Send position updates
        if self.websocket and self.mode == "online_coop":
            current_time = time.time()
            if current_time - self.last_position_send_time >= self.position_send_interval:
                self.send_message({
                    "action": "update_position",
                    "x": self.players[0].pos_x,
                    "y": self.players[0].pos_y,
                    "player_id": self.player_id
                })
                self.last_position_send_time = current_time

        # Update players and world (singleplayer/local co-op)
        if self.mode != "online_coop":
            for player in self.players:
                player.update(dt, self.world, pygame.key.get_pressed(), game=self)
            total_value = self.world.update(dt)
            self.cash_earned_today += total_value
            for player in self.players:
                player.quota_buffer += total_value

        # Update mining fatigue with faster recovery
        if self.mining_fatigue > 0:
            self.mining_fatigue_timer += dt
            if self.mining_fatigue_timer >= 0.5:
                self.mining_fatigue = max(0, self.mining_fatigue - 0.2 * dt)
                self.mining_fatigue_timer = 0.0
                logger.debug(f"Mining fatigue reduced to {self.mining_fatigue:.2f}")

        # Update entities
        for entity_group in self.entity_manager.entities.values():
            for entity in entity_group[:]:
                if entity.__class__.__name__ == "Particle":
                    entity.update(dt)
                else:
                    entity.update(dt, self)

        # Handle mining (client-side for singleplayer/local co-op)
        if self.mining and self.mine_target and self.mode != "online_coop":
            tx, ty = self.mine_target
            block_type = self.world.block_at(tx, ty)
            if block_type and block_type not in ["empty", "grass"]:
                player_x, player_y = self.players[0].rect.center
                block_x, block_y = tx * settings.TILE_SIZE + settings.TILE_SIZE // 2, ty * settings.TILE_SIZE + settings.TILE_SIZE // 2
                distance = calculate_distance((player_x, player_y), (block_x, block_y))
                if distance <= self.players[0].mining_range * settings.TILE_SIZE:
                    depth_zone = self.world.get_depth_zone(ty)
                    mining_time = self.ores_cfg.get(block_type, {"time": 1.0})["time"] / (self.players[0].pick_speed * self.players[0].mining_speed_boost * (1.5 if self.players[0].melee_upgrade else 1.0)) * (1 + self.mining_fatigue)
                    elapsed = time.time() - self.mine_start
                    initial_progress = self.world.get_block_state(tx, ty) / 3.0
                    self.mining_progress = initial_progress + (elapsed / mining_time)
                    stage = min(3, int(self.mining_progress * 3))
                    if stage > self.last_mining_stage:
                        spawn_particles(self, tx * settings.TILE_SIZE, ty * settings.TILE_SIZE, 3, rock_chip=True)
                        self.last_mining_stage = stage
                        self.world.set_block_state(tx, ty, stage)
                        if self.mining_sound and (time.time() - self.last_sound_time) >= 0.2:
                            self.mining_sound.set_volume(settings.SOUND_VOLUME * settings.BLOCK_PITCHES.get(block_type, 1.0) * 0.7)
                            self.mining_sound.play()
                            self.last_sound_time = time.time()
                        logger.debug(f"Mining stage {stage} at ({tx}, {ty})")
                    if self.mining_progress >= 1.0:
                        self.send_message({
                            "action": "mine_block",
                            "block_x": tx,
                            "block_y": ty,
                            "player_id": self.player_id
                        })
                        self.mine_start = time.time()
                        self.mine_target = None
                        self.mining_progress = 0.0
                        self.last_mining_stage = 0
                else:
                    self.stop_mining()

        # Handle lava hazard (client-side for singleplayer/local co-op)
        if self.lava_hazard_active and self.mode != "online_coop":
            self.lava_damage_timer += dt
            if self.lava_damage_timer >= 1.0:
                for player in self.players:
                    if not player.active_effects.get("safety_bubble", {}).get("active", False):
                        player.health -= 5
                        self.ui.lobby_message = "Lava Hazard: -5 HP"
                        self.ui.lobby_message_timer = 1.0
                        logger.debug("Lava hazard dealt 5 damage to player")
                self.lava_damage_timer = 0.0

        # Auto-mining and milestones
        if self.mode != "online_coop":
            self.handle_auto_mining()
        self.check_milestones()

        # Update camera
        self.target_camera_x = self.players[0].rect.centerx - settings.WIDTH // 2
        self.target_camera_y = max(0, self.players[0].rect.centery - settings.HEIGHT // 2)
        self.camera_x += (self.target_camera_x - self.camera_x) * self.camera_smoothing
        self.camera_y += (self.target_camera_y - self.camera_y) * self.camera_smoothing

        # Handle timers
        if self.debug_message_timer > 0:
            self.debug_message_timer -= dt
            if self.debug_message_timer <= 0:
                self.debug_message = None
        if self.treasure_notification_timer > 0:
            self.treasure_notification_timer -= dt
            if self.treasure_notification_timer <= 0:
                self.treasure_notification = None
        if self.inventory_full_timer > 0:
            self.inventory_full_timer -= dt
            if self.inventory_full_timer <= 0:
                self.inventory_full_notification = None
        if self.ore_collect_timer > 0:
            self.ore_collect_timer -= dt
            if self.ore_collect_timer <= 0:
                self.ore_collect_notification = None
        if self.shake_timer > 0:
            self.shake_timer -= dt
        if self.flash_timer > 0:
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.flash_color = settings.WHITE
        self.pulse_timer += dt

    async def run(self):
        """Run the game loop with optimized rendering and multiplayer message sending."""
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(settings.FPS) / 1000.0
            self.event_handler.process_events()
            # Only update game logic if not in menu states
            if not (self.ui.show_start_menu or self.ui.show_mode_menu or self.ui.show_lobby_menu or 
                    self.ui.show_pause_menu or self.ui.show_upgrade_menu or self.ui.show_inventory or 
                    self.ui.show_post_day_upgrades or self.ui.game_over):
                self.state_manager.update(self, dt)
            self.screen.fill((0, 0, 0))
            if not (self.ui.show_start_menu or self.ui.show_mode_menu or self.ui.show_lobby_menu or 
                    self.ui.show_pause_menu or self.ui.show_upgrade_menu or self.ui.show_inventory or 
                    self.ui.show_post_day_upgrades or self.ui.game_over):
                self.renderer.draw_world(self.world, self.camera_x, self.camera_y)
                self.renderer.draw_entities(self.entity_manager.entities.values(), self.camera_x, self.camera_y)
                self.renderer.draw_players(self.players, self.remote_players, self.camera_x, self.camera_y)
                if self.ore_scanner.active:
                    self.renderer.draw_ore_scanner(self.ore_scanner, self.camera_x, self.camera_y)
                if self.inventory_full_notification:
                    notification_surf = self.ui.font.render(self.inventory_full_notification, True, (255, 100, 100))
                    self.screen.blit(notification_surf, (settings.WIDTH // 2 - notification_surf.get_width() // 2, settings.HEIGHT - 150))
                if self.ore_collect_notification:
                    notification_surf = self.ui.font.render(self.ore_collect_notification, True, (0, 255, 0))
                    self.screen.blit(notification_surf, (settings.WIDTH // 2 - notification_surf.get_width() // 2, settings.HEIGHT - 100))
            self.renderer.draw_ui(self.ui, self)
            self.renderer.apply_effects(self.shake_timer, self.shake_intensity, self.flash_timer, self.flash_color)
            pygame.display.flip()
            if self.websocket:
                while self.message_queue:
                    message = self.message_queue.pop(0)
                    try:
                        await self.websocket.send(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")
                        self.ui.lobby_message = "Connection error, please reconnect"
                        self.ui.lobby_message_timer = 5.0
                        self.running = False
            await asyncio.sleep(0)
        pygame.mixer.music.stop()
        pygame.quit()
        logger.info("Game loop ended, music stopped")

if __name__ == "__main__":
    upgrades = load_upgrades()
    ores = load_ores()
    game = Game(upgrades, ores)
    if platform.system() == "Emscripten":
        asyncio.ensure_future(game.run())
    else:
        asyncio.run(game.run())