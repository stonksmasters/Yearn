import pygame
import random
import logging
import time
from settings import WIDTH, HEIGHT, FONT_SIZE, PLAYER_COLOR, WHITE, DAY_DURATION, TILE_SIZE

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing ui.py")

class UI:
    def __init__(self, font):
        """Initialize the UI with font and menu states."""
        self.font = font
        self.show_start_menu = True
        self.show_pause_menu = False
        self.show_upgrade_menu = False
        self.show_post_day_upgrades = False
        self.show_inventory = False
        self.game_over = False
        self.selected_start_option = 0
        self.selected_pause_option = 0
        self.selected_upgrade = 0
        self.selected_post_day_upgrade = 0
        self.selected_item = 0
        self.menu_mode = "pickaxes"
        self.shop_offset = 0
        self.post_day_upgrades = []
        # Cache static text surfaces
        self.start_menu_title = self.font.render("COAL LLC - ULTIMATE MINER", True, PLAYER_COLOR)
        self.pause_menu_title = self.font.render("PAUSED", True, PLAYER_COLOR)
        self.inventory_title = self.font.render("INVENTORY", True, PLAYER_COLOR)
        self.upgrade_menu_title = self.font.render("CHOOSE A BONUS UPGRADE", True, PLAYER_COLOR)
        logger.debug("Initialized UI")

    def draw(self, screen, game):
        """Draw the UI elements based on the game state."""
        if self.show_start_menu:
            self.draw_start_menu(screen)
            return
        if self.show_pause_menu:
            self.draw_pause_menu(screen)
            return

        # Extract data from game object
        player = game.players[0]
        day = getattr(game, 'day', 1)
        quota = getattr(game, 'quota', 1000)
        cash_earned_today = getattr(game, 'cash_earned_today', 0)
        day_start_time = getattr(game, 'day_start_time', time.time())
        debug_message = getattr(game, 'debug_message', None)
        show_debug = getattr(game, 'show_debug', False)
        mining_fatigue = getattr(game, 'mining_fatigue', 0.0)
        upgrades_cfg = getattr(game, 'upgrades_cfg', {'pickaxes': [], 'shop': []})

        # Draw HUD
        time_left = max(0, DAY_DURATION + player.day_extension - (time.time() - day_start_time))
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        health_percent = player.health / player.max_health
        quota_percent = min(cash_earned_today / quota, 1.0) if quota > 0 else 0.0

        # Health bar
        pygame.draw.rect(screen, (200, 0, 0), (10, HEIGHT - 50, 100, 20))
        pygame.draw.rect(screen, (0, 200, 0), (10, HEIGHT - 50, 100 * health_percent, 20))
        pygame.draw.rect(screen, WHITE, (10, HEIGHT - 50, 100, 20), 2)

        # Quota progress bar
        pygame.draw.rect(screen, (50, 50, 50), (10, HEIGHT - 80, 100, 15))
        pygame.draw.rect(screen, (255, 215, 0), (10, HEIGHT - 80, 100 * quota_percent, 15))
        pygame.draw.rect(screen, WHITE, (10, HEIGHT - 80, 100, 15), 2)

        # HUD text
        ui_lines = [
            f"Cash: ${player.cash:.2f}  Pick: {upgrades_cfg['pickaxes'][player.pick_index]['name']}",
            f"Day: {day}  Quota: ${cash_earned_today:.2f}/${quota:.2f}",
            f"Time: {minutes:02d}:{seconds:02d}",
            f"Health: {int(player.health)}/{player.max_health}",
            f"Inventory: D:{player.inventory.get('dynamite', 0)} H:{player.inventory.get('health_pack', 0)} "
            f"E:{player.inventory.get('earthquake', 0)} F:{player.inventory.get('depth_charge', 0)} "
            f"B:{player.inventory.get('bat_wing', 0)} G:{player.inventory.get('goblin_tooth', 0)}"
        ]

        for i, line in enumerate(ui_lines):
            screen.blit(self.font.render(line, True, WHITE), (10, 10 + i * (FONT_SIZE + 2)))

        # Status text with fatigue and ore pickup range
        status_lines = [
            f"Mining Speed: {player.mining_speed_boost:.1f}x",
            f"Mining Range: {player.mining_range:.1f}",
            f"AOE: {'None' if player.aoe_mining == 0 else '3x3' if player.aoe_mining == 1 else '5x5'}",
            f"Damage Resist: {player.rock_damage_reduction*100:.0f}%",
            f"Lucky Miner: {'Yes' if player.lucky_miner else 'No'}",
            f"Cash Multiplier: {player.cash_multiplier:.1f}x",
            f"Auto-Miner: {'Yes' if player.active_effects.get('auto_miner', {}).get('active', False) else 'No'}",
            f"Fatigue: {mining_fatigue*100:.0f}%",
            f"Fatigue Reduction: {player.fatigue_reduction*100:.0f}%",
            f"Ore Pickup Range: {player.ore_pickup_range:.1f} blocks"
        ]

        for i, line in enumerate(status_lines):
            screen.blit(self.font.render(line, True, (200, 200, 100)), (WIDTH - 200, 10 + i * (FONT_SIZE + 2)))

        # Active effects
        effect_y = HEIGHT - 50
        for effect_name, effect_data in player.active_effects.items():
            if effect_data.get('active', False):
                effect_time_left = effect_data.get('end_time', time.time()) - time.time()
                if effect_time_left > 0:
                    text = f"{effect_name.capitalize()}: {int(effect_time_left)}s"
                    screen.blit(self.font.render(text, True, (0, 255, 255)), (WIDTH - 200, effect_y))
                    effect_y -= 20

        # Draw inventory
        if self.show_inventory:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            screen.blit(self.inventory_title, (WIDTH // 2 - self.inventory_title.get_width() // 2, 50))
            y_offset = 100
            item_list = list(player.inventory.items())
            for i, (item_id, count) in enumerate(item_list):
                item_info = next((item for item in upgrades_cfg.get('shop', []) if item['id'] == item_id), 
                                 {'name': item_id.replace('_', ' ').title(), 'description': 'No description'})
                text = f"{item_info['name']}: {count} - {item_info['description']}"
                text_surf = self.font.render(text, True, WHITE)
                screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, y_offset))
                if i == self.selected_item:
                    pygame.draw.rect(screen, PLAYER_COLOR, (WIDTH // 2 - 180, y_offset - 5, 360, 30), 2)
                y_offset += 40
            y_offset += 20
            screen.blit(self.font.render("Ores:", True, WHITE), (WIDTH // 2 - 50, y_offset))
            y_offset += 30
            for slot in player.get_ore_inventory():
                if slot:
                    text = f"{slot['type']}: {slot['count']}"
                    text_surf = self.font.render(text, True, WHITE)
                    screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, y_offset))
                    y_offset += 30
            instructions = ["↑/↓: Navigate  ENTER: Use  ESC: Close"]
            for j, line in enumerate(instructions):
                inst_surf = self.font.render(line, True, (200, 200, 100))
                screen.blit(inst_surf, (WIDTH // 2 - inst_surf.get_width() // 2, HEIGHT - 100 + j * 30))

        # Draw upgrade menu
        if self.show_upgrade_menu:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            pick_color = PLAYER_COLOR if self.menu_mode == "pickaxes" else (150, 150, 150)
            shop_color = PLAYER_COLOR if self.menu_mode == "shop" else (150, 150, 150)
            pick_tab = self.font.render("PICKAXES", True, pick_color)
            shop_tab = self.font.render("SHOP", True, shop_color)
            screen.blit(pick_tab, (WIDTH // 4 - pick_tab.get_width() // 2, 30))
            screen.blit(shop_tab, (3 * WIDTH // 4 - shop_tab.get_width() // 2, 30))
            pygame.draw.line(screen, PLAYER_COLOR, (0, 60), (WIDTH, 60), 2)
            y_offset = 80
            if self.menu_mode == "pickaxes":
                for i, upgrade in enumerate(upgrades_cfg.get('pickaxes', [])):
                    color = (100, 255, 100) if upgrade.get('unlocked', False) else WHITE if player.cash >= upgrade['cost'] else (150, 150, 150)
                    status = "[OWNED]" if upgrade.get('unlocked', False) else f"[BUY ${upgrade['cost']}]" if player.cash >= upgrade['cost'] else f"${upgrade['cost']}"
                    text = f"{upgrade['name']} - Speed: {upgrade['speed']}x {status}"
                    text_surf = self.font.render(text, True, color)
                    screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, y_offset))
                    if i == self.selected_upgrade:
                        pygame.draw.rect(screen, PLAYER_COLOR, (WIDTH // 2 - 180, y_offset - 5, 360, 30), 2)
                    y_offset += 40
            else:
                shop_items = upgrades_cfg.get('shop', [])
                visible_items = shop_items[self.shop_offset:self.shop_offset + 8]
                for i, item in enumerate(visible_items):
                    color = (100, 255, 100) if item.get('unlocked', False) and item.get('permanent', False) else WHITE if player.cash >= item['cost'] and not (item.get('unlocked', False) and item.get('permanent', False)) else (150, 150, 150)
                    status = "[OWNED]" if item.get('unlocked', False) and item.get('permanent', False) else f"[BUY ${item['cost']}]" if player.cash >= item['cost'] else f"${item['cost']}"
                    text = f"{item['name']} {status}"
                    text_surf = self.font.render(text, True, color)
                    screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, y_offset))
                    if i + self.shop_offset == self.selected_upgrade:
                        pygame.draw.rect(screen, PLAYER_COLOR, (WIDTH // 2 - 180, y_offset - 5, 360, 30), 2)
                    y_offset += 40
                if self.shop_offset > 0:
                    pygame.draw.polygon(screen, WHITE, [(WIDTH // 2, 70), (WIDTH // 2 - 10, 80), (WIDTH // 2 + 10, 80)])
                if self.shop_offset + 8 < len(shop_items):
                    pygame.draw.polygon(screen, WHITE, [(WIDTH // 2, HEIGHT - 50), (WIDTH // 2 - 10, HEIGHT - 60), (WIDTH // 2 + 10, HEIGHT - 60)])
            instructions = [
                "TAB: Switch Tabs  ↑/↓: Navigate  ENTER: Purchase",
                "ESC: Close Menu"
            ]
            for j, line in enumerate(instructions):
                inst_surf = self.font.render(line, True, (200, 200, 100))
                screen.blit(inst_surf, (WIDTH // 2 - inst_surf.get_width() // 2, HEIGHT - 100 + j * 30))

        # Draw post-day upgrades
        if self.show_post_day_upgrades:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            screen.blit(self.upgrade_menu_title, (WIDTH // 2 - self.upgrade_menu_title.get_width() // 2, 50))
            y_offset = 100
            for i, upgrade in enumerate(self.post_day_upgrades):
                color = PLAYER_COLOR if i == self.selected_post_day_upgrade else WHITE
                text = f"{upgrade['name']}: {upgrade['description']}"
                text_surf = self.font.render(text, True, color)
                screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, y_offset))
                if i == self.selected_post_day_upgrade:
                    pygame.draw.rect(screen, PLAYER_COLOR, (WIDTH // 2 - 180, y_offset - 5, 360, 30), 2)
                y_offset += 40
            instructions = ["↑/↓: Navigate  ENTER: Select  ESC: Skip"]
            for j, line in enumerate(instructions):
                inst_surf = self.font.render(line, True, (200, 200, 100))
                screen.blit(inst_surf, (WIDTH // 2 - inst_surf.get_width() // 2, HEIGHT - 100 + j * 30))

        # Draw game over
        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            screen.blit(overlay, (0, 0))
            reason = "YOU DIED!" if player.health <= 0 else "FAILED TO MEET QUOTA!"
            title = self.font.render(f"GAME OVER - {reason}", True, (255, 50, 50))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 80))
            stats = [
                f"Day Reached: {day}",
                f"Final Cash: ${player.cash:.2f}",
                f"Quota: ${cash_earned_today:.2f}/${quota:.2f}"
            ]
            for i, line in enumerate(stats):
                stat_surf = self.font.render(line, True, WHITE)
                screen.blit(stat_surf, (WIDTH // 2 - stat_surf.get_width() // 2, HEIGHT // 2 - 30 + i * 30))
            restart = self.font.render("Press R to Restart", True, (100, 255, 100))
            screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT - 100))

        # Draw drop-off prompt
        if player.rect.y < TILE_SIZE:
            drop_off_surf = self.font.render("Press O to drop off ores", True, (255, 255, 0))
            screen.blit(drop_off_surf, (WIDTH // 2 - drop_off_surf.get_width() // 2, HEIGHT - 100))

        # Draw debug message
        if debug_message and show_debug:
            debug_surf = self.font.render(debug_message, True, WHITE)
            screen.blit(debug_surf, (WIDTH // 2 - debug_surf.get_width() // 2, HEIGHT - 50))

        logger.debug("Rendered UI elements")

    def draw_start_menu(self, screen):
        """Draw the start menu."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        screen.blit(self.start_menu_title, (WIDTH // 2 - self.start_menu_title.get_width() // 2, HEIGHT // 4))
        options = ["Start Game", "Quit"]
        for i, option in enumerate(options):
            color = PLAYER_COLOR if i == self.selected_start_option else WHITE
            text_surf = self.font.render(option, True, color)
            screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, HEIGHT // 2 + i * 40))
            if i == self.selected_start_option:
                pygame.draw.rect(screen, PLAYER_COLOR, (WIDTH // 2 - 100, HEIGHT // 2 + i * 40 - 5, 200, 30), 2)
        instructions = ["↑/↓: Navigate  ENTER: Select"]
        for j, line in enumerate(instructions):
            inst_surf = self.font.render(line, True, (200, 200, 100))
            screen.blit(inst_surf, (WIDTH // 2 - inst_surf.get_width() // 2, HEIGHT - 100 + j * 30))

    def draw_pause_menu(self, screen):
        """Draw the pause menu."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        screen.blit(self.pause_menu_title, (WIDTH // 2 - self.pause_menu_title.get_width() // 2, HEIGHT // 4))
        options = ["Resume", "Restart", "Quit"]
        for i, option in enumerate(options):
            color = PLAYER_COLOR if i == self.selected_pause_option else WHITE
            text_surf = self.font.render(option, True, color)
            screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, HEIGHT // 2 + i * 40))
            if i == self.selected_pause_option:
                pygame.draw.rect(screen, PLAYER_COLOR, (WIDTH // 2 - 100, HEIGHT // 2 + i * 40 - 5, 200, 30), 2)
        instructions = ["↑/↓: Navigate  ENTER: Select  ESC/P: Resume"]
        for j, line in enumerate(instructions):
            inst_surf = self.font.render(line, True, (200, 200, 100))
            screen.blit(inst_surf, (WIDTH // 2 - inst_surf.get_width() // 2, HEIGHT - 100 + j * 30))

    def handle_start_input(self, event):
        """Handle input for the start menu."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_start_option = (self.selected_start_option - 1) % 2
                logger.debug(f"Selected start option: {self.selected_start_option}")
            elif event.key == pygame.K_DOWN:
                self.selected_start_option = (self.selected_start_option + 1) % 2
                logger.debug(f"Selected start option: {self.selected_start_option}")
            elif event.key == pygame.K_RETURN:
                if self.selected_start_option == 0:
                    self.show_start_menu = False
                    logger.info("Started game from start menu")
                    return "start"
                elif self.selected_start_option == 1:
                    logger.info("Quit game from start menu")
                    return "quit"
        return None

    def handle_pause_input(self, event):
        """Handle input for the pause menu."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.show_pause_menu = False
                logger.debug("Resumed game from pause menu")
                return "resume"
            elif event.key == pygame.K_UP:
                self.selected_pause_option = (self.selected_pause_option - 1) % 3
                logger.debug(f"Selected pause option: {self.selected_pause_option}")
            elif event.key == pygame.K_DOWN:
                self.selected_pause_option = (self.selected_pause_option + 1) % 3
                logger.debug(f"Selected pause option: {self.selected_pause_option}")
            elif event.key == pygame.K_RETURN:
                if self.selected_pause_option == 0:
                    self.show_pause_menu = False
                    logger.debug("Resumed game from pause menu")
                    return "resume"
                elif self.selected_pause_option == 1:
                    self.show_pause_menu = False
                    logger.info("Restarted game from pause menu")
                    return "restart"
                elif self.selected_pause_option == 2:
                    logger.info("Quit game from pause menu")
                    return "quit"
        return None

    def handle_post_day_input(self, event, player):
        """Handle input for post-day upgrade selection."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.show_post_day_upgrades = False
                logger.debug("Skipped post-day upgrade selection")
                return True
            elif event.key == pygame.K_UP:
                self.selected_post_day_upgrade = (self.selected_post_day_upgrade - 1) % len(self.post_day_upgrades)
                logger.debug(f"Selected post-day upgrade: {self.selected_post_day_upgrade}")
            elif event.key == pygame.K_DOWN:
                self.selected_post_day_upgrade = (self.selected_post_day_upgrade + 1) % len(self.post_day_upgrades)
                logger.debug(f"Selected post-day upgrade: {self.selected_post_day_upgrade}")
            elif event.key == pygame.K_RETURN:
                selected_upgrade = self.post_day_upgrades[self.selected_post_day_upgrade]
                self.apply_upgrade(selected_upgrade, player)
                self.show_post_day_upgrades = False
                logger.info(f"Selected post-day upgrade: {selected_upgrade['name']}")
                return True
        return False

    def select_post_day_upgrades(self, upgrades_cfg):
        """Select up to three random shop upgrades for post-day selection."""
        shop_upgrades = [item for item in upgrades_cfg.get("shop", []) if not (item.get('unlocked', False) and item.get('permanent', False))]
        if len(shop_upgrades) >= 3:
            self.post_day_upgrades = random.sample(shop_upgrades, 3)
        else:
            self.post_day_upgrades = shop_upgrades[:]
        self.selected_post_day_upgrade = 0
        logger.debug(f"Selected {len(self.post_day_upgrades)} post-day upgrades")

    def apply_upgrade(self, upgrade, player):
        """Apply a selected upgrade to the player and mark permanent upgrades as unlocked."""
        effect = upgrade.get("effect", {})
        if effect.get("type") == "permanent":
            if effect["attribute"] == "mining_speed":
                player.mining_speed_boost += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: mining_speed += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "health":
                player.max_health += effect["value"]
                player.health += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: health += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "cash_multiplier":
                player.cash_multiplier += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: cash_multiplier += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "lucky_miner":
                player.lucky_miner = True
                upgrade["unlocked"] = True
                logger.debug("Applied permanent upgrade: lucky_miner = True, marked as unlocked")
            elif effect["attribute"] == "aoe_mining":
                player.aoe_mining += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: aoe_mining += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "rock_damage_reduction":
                player.rock_damage_reduction += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: rock_damage_reduction += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "mining_range":
                player.mining_range += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: mining_range += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "fatigue_reduction":
                player.fatigue_reduction += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: fatigue_reduction += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "quota_buffer":
                player.quota_buffer += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: quota_buffer += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "day_extension":
                player.day_extension += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: day_extension += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "jump_boost":
                player.jump_boost += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: jump_boost += {effect['value']}, marked as unlocked")
            elif effect["attribute"] == "ore_pickup_range":
                player.ore_pickup_range += effect["value"]
                upgrade["unlocked"] = True
                logger.debug(f"Applied permanent upgrade: ore_pickup_range += {effect['value']}, marked as unlocked")
        elif effect.get("type") == "item":
            player.inventory[effect["item"]] = player.inventory.get(effect["item"], 0) + effect.get("count", 1)
            logger.debug(f"Added item to inventory: {effect['item']}")
        elif effect.get("type") == "effect":
            player.active_effects[effect["attribute"]] = {
                "active": True,
                "end_time": time.time() + effect["duration"]
            }
            logger.debug(f"Applied effect: {effect['attribute']} for {effect['duration']} seconds")