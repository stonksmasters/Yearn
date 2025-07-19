import pygame
import logging
from settings import TILE_SIZE, KEYS
from utils import spawn_particles, trigger_screen_shake, trigger_screen_flash, aoe_mining

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing event_handler.py")

class EventHandler:
    def __init__(self, game):
        self.game = game
        logger.info("EventHandler initialized")

    def process_events(self):
        """Process all Pygame events and delegate to appropriate game methods."""
        for event in pygame.event.get():
            logger.debug(f"Processing event: type={event.type}, key={getattr(event, 'key', 'N/A')}, unicode={getattr(event, 'unicode', 'N/A')}")
            if event.type == pygame.QUIT:
                self.game.save_and_quit()
                logger.info("Quit event triggered")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not any([self.game.ui.show_start_menu, self.game.ui.show_mode_menu,
                            self.game.ui.show_lobby_menu, self.game.ui.show_pause_menu,
                            self.game.ui.show_upgrade_menu, self.game.ui.game_over,
                            self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]):
                    self.game.handle_mining(event.pos)
                    logger.debug(f"Mouse button down at {event.pos}")
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.game.stop_mining()
                logger.debug("Mouse button up, stopped mining")
            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event)
            elif event.type == pygame.KEYUP:
                self.handle_keyup(event)

    def handle_keydown(self, event):
        """Handle key press events based on game state and key bindings."""
        if self.game.ui.show_start_menu:
            action = self.game.ui.handle_start_input(event)
            if action == "start":
                self.game.state_manager.set_state("mode_menu", self.game)
                logger.info("Transitioned to mode selection menu")
            elif action == "quit":
                self.game.save_and_quit()
                logger.info("Game quit from start menu")
            return
        if self.game.ui.show_mode_menu:
            action = self.game.ui.handle_mode_input(event, self.game)
            if action == "start":
                if self.game.mode != "online_coop":
                    self.game.state_manager.set_state("playing", self.game)
                    logger.info(f"Started game in {self.game.mode} mode")
            return
        if self.game.ui.show_lobby_menu:
            self.game.ui.handle_lobby_input(event, self.game)
            return
        if self.game.ui.show_pause_menu:
            action = self.game.ui.handle_pause_input(event)
            if action == "resume":
                self.game.toggle_pause()
                logger.debug("Resumed game from pause menu")
            elif action == "restart":
                self.game.setup()
                logger.info("Game restarted from pause menu")
            elif action == "quit":
                self.game.save_and_quit()
                logger.info("Game quit from pause menu")
            return
        if self.game.ui.game_over:
            if event.key == pygame.K_r:
                self.game.setup()
                logger.info("Game restarted from game over")
            return
        if self.game.ui.show_post_day_upgrades:
            if self.game.ui.handle_post_day_input(event, self.game.players[0]):
                self.game.next_day()
                logger.info("Proceeded to next day from post-day upgrades")
            return
        if self.game.ui.show_upgrade_menu:
            if event.key == pygame.K_ESCAPE:
                self.game.ui.show_upgrade_menu = False
                logger.debug("Closed upgrade menu")
            elif event.key == pygame.K_TAB:
                self.game.ui.menu_mode = "shop" if self.game.ui.menu_mode == "pickaxes" else "pickaxes"
                self.game.ui.selected_upgrade = 0
                self.game.ui.shop_offset = 0
                logger.info(f"Switched to {self.game.ui.menu_mode} menu")
            elif event.key == pygame.K_UP:
                if self.game.ui.menu_mode == "pickaxes":
                    if self.game.upgrades_cfg.get("pickaxes", []):
                        self.game.ui.selected_upgrade = max(0, self.game.ui.selected_upgrade - 1)
                        logger.debug(f"Selected pickaxe index: {self.game.ui.selected_upgrade}")
                else:
                    shop_items = self.game.upgrades_cfg.get("shop", [])
                    if shop_items:
                        self.game.ui.selected_upgrade = max(0, self.game.ui.selected_upgrade - 1)
                        if self.game.ui.selected_upgrade < self.game.ui.shop_offset:
                            self.game.ui.shop_offset = max(0, self.game.ui.shop_offset - 1)
                        logger.debug(f"Selected shop item index: {self.game.ui.selected_upgrade}, offset: {self.game.ui.shop_offset}")
            elif event.key == pygame.K_DOWN:
                if self.game.ui.menu_mode == "pickaxes":
                    if self.game.upgrades_cfg.get("pickaxes", []):
                        self.game.ui.selected_upgrade = min(len(self.game.upgrades_cfg["pickaxes"]) - 1, self.game.ui.selected_upgrade + 1)
                        logger.debug(f"Selected pickaxe index: {self.game.ui.selected_upgrade}")
                else:
                    shop_items = self.game.upgrades_cfg.get("shop", [])
                    if shop_items:
                        self.game.ui.selected_upgrade = min(len(shop_items) - 1, self.game.ui.selected_upgrade + 1)
                        if self.game.ui.selected_upgrade >= self.game.ui.shop_offset + 8:
                            self.game.ui.shop_offset = min(len(shop_items) - 8, self.game.ui.shop_offset + 1)
                        logger.debug(f"Selected shop item index: {self.game.ui.selected_upgrade}, offset: {self.game.ui.shop_offset}")
            elif event.key == pygame.K_RETURN:
                self.game.purchase_upgrade()
                logger.debug("Attempted to purchase upgrade")
            return
        if self.game.ui.show_inventory:
            if event.key == pygame.K_ESCAPE:
                self.game.ui.show_inventory = False
                logger.debug("Closed inventory menu")
            elif event.key == pygame.K_UP:
                item_list = list(self.game.players[0].inventory.items())
                self.game.ui.selected_item = max(0, self.game.ui.selected_item - 1)
                logger.debug(f"Selected inventory item index: {self.game.ui.selected_item}")
            elif event.key == pygame.K_DOWN:
                item_list = list(self.game.players[0].inventory.items())
                self.game.ui.selected_item = min(len(item_list) - 1, self.game.ui.selected_item + 1) if item_list else 0
                logger.debug(f"Selected inventory item index: {self.game.ui.selected_item}")
            elif event.key == pygame.K_RETURN:
                self.game.use_inventory_item()
                logger.debug("Used selected inventory item")
            return

        # Gameplay controls
        if event.key == KEYS.get("PAUSE", pygame.K_p) or event.key == pygame.K_ESCAPE:
            self.game.toggle_pause()
            logger.debug("Toggled pause menu")
        elif event.key == KEYS.get("UPGRADE", pygame.K_u) and not any([self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]):
            self.game.toggle_upgrade_menu()
            logger.info(f"{'Opened' if self.game.ui.show_upgrade_menu else 'Closed'} upgrade menu")
        elif event.key == KEYS.get("INVENTORY", pygame.K_i) and not any([self.game.ui.show_post_day_upgrades, self.game.ui.show_upgrade_menu]):
            self.game.toggle_inventory_menu()
            logger.info(f"{'Opened' if self.game.ui.show_inventory else 'Closed'} inventory menu")
        elif event.key == KEYS.get("DEBUG", pygame.K_F1):
            self.game.show_debug = not self.game.show_debug
            logger.info(f"Debug overlay {'enabled' if self.game.show_debug else 'disabled'}")
        elif event.key == KEYS.get("MINIMAP", pygame.K_m):
            self.game.show_minimap = not self.game.show_minimap
            logger.info(f"Minimap {'shown' if self.game.show_minimap else 'hidden'}")
        elif event.key == KEYS.get("SECOND_PLAYER", pygame.K_2):
            self.game.toggle_second_player()
            logger.info(f"{'Added' if len(self.game.players) > 1 else 'Removed'} second player")
        elif event.key == KEYS.get("LEFT", pygame.K_LEFT):
            self.game.players[0].target_vx = -self.game.move_speed
            logger.debug("Player 1 moving left")
        elif event.key == KEYS.get("RIGHT", pygame.K_RIGHT):
            self.game.players[0].target_vx = self.game.move_speed
            logger.debug("Player 1 moving right")
        elif event.key == KEYS.get("JUMP", pygame.K_UP) and (self.game.players[0].on_ground or self.game.players[0].coyote_timer > 0):
            self.game.players[0].vy = self.game.jump_velocity * self.game.players[0].jump_boost
            self.game.players[0].on_ground = False
            self.game.players[0].coyote_timer = 0.0
            logger.debug("Player 1 jumped")
        elif event.key == KEYS.get("THROW", pygame.K_t):
            self.game.players[0].throw_item(self.game, self.game.ore_items)
            if self.game.drop_sound:
                self.game.drop_sound.play()
            logger.info("Player 1 threw item")
        elif event.key == KEYS.get("P2_LEFT", pygame.K_a) and len(self.game.players) > 1:
            self.game.players[1].target_vx = -self.game.move_speed
            logger.debug("Player 2 moving left")
        elif event.key == KEYS.get("P2_RIGHT", pygame.K_d) and len(self.game.players) > 1:
            self.game.players[1].target_vx = self.game.move_speed
            logger.debug("Player 2 moving right")
        elif event.key == KEYS.get("P2_JUMP", pygame.K_w) and len(self.game.players) > 1 and (self.game.players[1].on_ground or self.game.players[1].coyote_timer > 0):
            self.game.players[1].vy = self.game.jump_velocity * self.game.players[1].jump_boost
            self.game.players[1].on_ground = False
            self.game.players[1].coyote_timer = 0.0
            logger.debug("Player 2 jumped")
        elif event.key == KEYS.get("P2_THROW", pygame.K_g) and len(self.game.players) > 1:
            self.game.players[1].throw_item(self.game, self.game.ore_items)
            if self.game.drop_sound:
                self.game.drop_sound.play()
            logger.info("Player 2 threw item")
        elif event.key == KEYS.get("DYNAMITE", pygame.K_d) and not any([self.game.ui.show_upgrade_menu, self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]):
            self.game.use_item("dynamite")
            logger.info("Used dynamite")
        elif event.key == KEYS.get("HEALTH_PACK", pygame.K_h) and not any([self.game.ui.show_upgrade_menu, self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]):
            self.game.use_item("health_pack")
            logger.info("Used health pack")
        elif event.key == KEYS.get("EARTHQUAKE", pygame.K_e) and not any([self.game.ui.show_upgrade_menu, self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]):
            self.game.use_item("earthquake")
            logger.info("Used earthquake")
        elif event.key == KEYS.get("DEPTH_CHARGE", pygame.K_f) and not any([self.game.ui.show_upgrade_menu, self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]):
            self.game.use_item("depth_charge")
            logger.info("Used depth charge")
        elif event.key == KEYS.get("DROP_ORE", pygame.K_o) and not any([self.game.ui.show_upgrade_menu, self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]):
            for player in self.game.players:
                if player.rect.y < TILE_SIZE:
                    total_value = player.clear_ore_inventory(self.game)
                    if total_value > 0:
                        player.cash += total_value
                        self.game.cash_earned_today += total_value
                        self.game.ore_collect_notification = f"Dropped off ore: ${total_value:.2f}"
                        self.game.notification_timer = 2.0
                        logger.info(f"Player dropped off ores for ${total_value:.2f}")
        elif event.key == KEYS.get("MELEE", pygame.K_SPACE) and not any([self.game.ui.show_upgrade_menu, self.game.ui.show_post_day_upgrades, self.game.ui.show_inventory]) and self.game.players[0].melee_upgrade:
            self.game.use_melee()
            logger.debug("Player 1 used melee attack")

    def handle_keyup(self, event):
        """Handle key release events for movement."""
        if event.key in (KEYS.get("LEFT", pygame.K_LEFT), KEYS.get("RIGHT", pygame.K_RIGHT)):
            self.game.players[0].target_vx = 0.0
            logger.debug("Player 1 stopped moving horizontally")
        elif event.key in (KEYS.get("P2_LEFT", pygame.K_a), KEYS.get("P2_RIGHT", pygame.K_d)) and len(self.game.players) > 1:
            self.game.players[1].target_vx = 0.0
            logger.debug("Player 2 stopped moving horizontally")