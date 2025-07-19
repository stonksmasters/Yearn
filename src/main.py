import pygame
import asyncio
import logging
import os
import platform
import websockets
import json
from game import Game
from data import load_ores, load_upgrades
from settings import WIDTH, HEIGHT, FPS

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing main.py")

def verify_files():
    """Log presence of critical files, with actual checks for local runs."""
    files = [
        'src/main.py',
        'src/game.py',
        'src/player.py',
        'src/world.py',
        'src/entities.py',
        'src/ui.py',
        'src/data.py',
        'src/save_load.py',
        'data/upgrades.json',
        'data/ores.json',
        'assets/mining.wav',
        'assets/item_use.wav',
        'assets/landing.wav'
    ]
    if platform.system() != "Emscripten":
        for path in files:
            if os.path.exists(path):
                logger.info(f"Found: {path}")
            else:
                logger.warning(f"Missing: {path}")
    else:
        for path in files:
            logger.info(f"Assumed present: {path} (file system checks disabled for Pyodide)")

async def websocket_client(game):
    """Handle WebSocket communication with the server."""
    uri = os.getenv("WEBSOCKET_URL", "ws://localhost:8765")  # Use environment variable for production
    try:
        async with websockets.connect(uri) as websocket:
            game.websocket = websocket
            logger.info(f"Connected to WebSocket server at {uri}")
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        logger.debug(f"Received message: {data['type']}")
                        if data["type"] == "lobby_created":
                            game.player_id = data["player_id"]
                            game.lobby_code = data["lobby_code"]
                            game.world.seed = data["world_seed"]
                            game.mode = "online_coop"
                            for pos, block_type in data["world_state"].items():
                                x, y = map(int, pos.strip('()').split(','))
                                game.world.set_block(x, y, block_type)
                            for entity_id, entity_data in data["entities"].items():
                                game.handle_spawn_entity(entity_id, entity_data)
                            game.day = data["day"]
                            game.quota = data["quota"]
                            game.time_left = data["time_left"]
                            game.ui.lobby_message = f"Lobby Created: {data['lobby_code']}"
                            game.ui.lobby_message_timer = 5.0
                            game.ui.show_lobby_menu = False
                            game.state_manager.set_state("playing", game)
                        elif data["type"] == "lobby_joined":
                            game.player_id = data["player_id"]
                            game.lobby_code = data["lobby_code"]
                            game.world.seed = data["world_seed"]
                            game.mode = "online_coop"
                            for pos, block_type in data["world_state"].items():
                                x, y = map(int, pos.strip('()').split(','))
                                game.world.set_block(x, y, block_type)
                            for entity_id, entity_data in data["entities"].items():
                                game.handle_spawn_entity(entity_id, entity_data)
                            for pid, p_data in data["players"].items():
                                game.update_remote_player(pid, p_data["x"], p_data["y"], p_data["health"])
                            game.day = data["day"]
                            game.quota = data["quota"]
                            game.time_left = data["time_left"]
                            game.ui.lobby_message = f"Joined Lobby: {data['lobby_code']}"
                            game.ui.lobby_message_timer = 5.0
                            game.ui.show_lobby_menu = False
                            game.state_manager.set_state("playing", game)
                        elif data["type"] == "error":
                            game.ui.lobby_message = data["message"]
                            game.ui.lobby_message_timer = 5.0
                        elif data["type"] == "player_joined":
                            game.update_remote_player(data["id"], data["x"], data["y"], data["health"])
                            game.ui.lobby_message = f"Player {data['id']} joined"
                            game.ui.lobby_message_timer = 3.0
                        elif data["type"] == "player_update":
                            game.update_remote_player(data["id"], data["x"], data["y"], data["health"])
                        elif data["type"] == "player_left":
                            game.remove_remote_player(data["id"])
                            game.ui.lobby_message = f"Player {data['id']} left"
                            game.ui.lobby_message_timer = 3.0
                        elif data["type"] == "block_mined":
                            game.world.set_block(data["block_x"], data["block_y"], "empty")
                        elif data["type"] == "spawn_entity":
                            game.handle_spawn_entity(data["entity_id"], data["entity_data"])
                        elif data["type"] == "ore_collected":
                            game.remove_ore(data["ore_id"])
                            if data["player_id"] == game.player_id:
                                game.cash_earned_today += data["cash_earned"]
                                game.players[0].cash += data["cash_earned"]
                                game.players[0].quota_buffer += data["cash_earned"]
                        elif data["type"] == "item_used":
                            if data["player_id"] == game.player_id:
                                game.players[0].inventory[data["item_id"]] = max(0, game.players[0].inventory[data["item_id"]] - 1)
                                if data["item_id"] == "health_pack":
                                    game.players[0].health = min(game.players[0].max_health, game.players[0].health + 50)
                                elif data["item_id"] == "bat_wing":
                                    game.players[0].active_effects["speed_boost"] = {"active": True, "end_time": time.time() + 30}
                                    game.players[0].mining_speed_boost += 0.5
                                elif data["item_id"] == "goblin_tooth":
                                    game.players[0].active_effects["safety_bubble"] = {"active": True, "end_time": time.time() + 30}
                                    game.players[0].rock_damage_reduction += 0.2
                        elif data["type"] == "ore_dropped":
                            if data["player_id"] == game.player_id:
                                game.cash_earned_today += data["cash_earned"]
                                game.players[0].cash += data["cash_earned"]
                                game.players[0].quota_buffer += data["cash_earned"]
                                for slot in game.players[0].ore_slots:
                                    if slot:
                                        slot["count"] = 0
                                        slot = None
                        elif data["type"] == "milestone_achieved":
                            if data["milestone_type"] == "depth":
                                game.milestones["depth"][data["value"]] = True
                                game.players[0].cash += data["reward"]["cash"]
                                game.players[0].inventory["health_pack"] = game.players[0].inventory.get("health_pack", 0) + data["reward"]["health_pack"]
                                game.debug_message = f"Milestone: Reached Depth {data['value']} - +${data['reward']['cash']}, +{data['reward']['health_pack']} Health Pack"
                                game.debug_message_timer = 2.0
                            elif data["milestone_type"] == "ores_mined":
                                game.milestones["ores_mined"][data["value"]] = True
                                game.players[0].cash += data["reward"]["cash"]
                                game.players[0].inventory["dynamite"] = game.players[0].inventory.get("dynamite", 0) + data["reward"]["dynamite"]
                                game.debug_message = f"Milestone: Mined {data['value']} Ores - +${data['reward']['cash']}, +{data['reward']['dynamite']} Dynamite"
                                game.debug_message_timer = 2.0
                            elif data["milestone_type"] == "diamonds_mined":
                                game.milestones["diamonds_mined"][data["value"]] = True
                                game.players[0].cash += data["reward"]["cash"]
                                game.players[0].inventory["health_pack"] = game.players[0].inventory.get("health_pack", 0) + data["reward"]["health_pack"]
                                game.debug_message = f"Milestone: Mined {data['value']} Diamonds - +${data['reward']['cash']}, +{data['reward']['health_pack']} Health Pack"
                                game.debug_message_timer = 2.0
                        elif data["type"] == "next_day":
                            game.day = data["day"]
                            game.quota = data["quota"]
                            game.time_left = data["time_left"]
                            game.cash_earned_today = max(0, game.cash_earned_today - game.quota)
                            game.players[0].cash += game.cash_earned_today
                            game.debug_message = f"Day {game.day} started! New quota: ${game.quota:.2f}"
                            game.debug_message_timer = 2.0
                            game.state_manager.set_state("playing", game)
                        elif data["type"] == "game_over":
                            game.state_manager.set_state("game_over", game)
                            game.debug_message = f"Game Over: {data['reason']}"
                            game.debug_message_timer = 2.0
                        elif data["type"] == "lava_hazard_activated":
                            game.lava_hazard_active = True
                            game.debug_message = "Warning: Lava Hazard Activated!"
                            game.debug_message_timer = 2.0
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON received: {message}")
                    except KeyError as e:
                        logger.error(f"Missing key in message: {e}")
            except websockets.ConnectionClosed:
                logger.error("WebSocket connection closed")
                game.ui.lobby_message = "Disconnected from server"
                game.ui.lobby_message_timer = 5.0
    except Exception as e:
        logger.error(f"WebSocket connection failed: {e}")
        game.ui.lobby_message = "Failed to connect to server"
        game.ui.lobby_message_timer = 5.0

async def main():
    """Initialize and run the game with WebSocket integration."""
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Coal LLC - Ultimate Miner")
    clock = pygame.time.Clock()

    verify_files()
    upgrades = load_upgrades()
    ores = load_ores()
    
    # Ensure pickaxes have unlocked state
    for i, pick in enumerate(upgrades['pickaxes']):
        pick.setdefault('unlocked', i == 0)
    
    game = Game(upgrades, ores)
    game.setup()  # Initialize game state, UI, and players
    logger.info("Starting game loop")
    
    # Start WebSocket client as a background task
    asyncio.create_task(websocket_client(game))
    
    while game.running:
        game.event_handler.process_events()
        
        if not any([
            game.ui.show_start_menu,
            game.ui.show_mode_menu,
            game.ui.show_lobby_menu,
            game.ui.show_pause_menu,
            game.ui.show_upgrade_menu,
            game.ui.show_post_day_upgrades,
            game.ui.show_inventory,
            game.ui.game_over
        ]):
            dt = clock.tick(FPS) / 1000.0
            game.run(dt)
        else:
            game.ui.draw(screen, game)
            pygame.display.flip()
        
        await asyncio.sleep(1.0 / FPS)  # Yield control for browser compatibility
    
    if game.websocket:
        await game.websocket.close()
        logger.info("WebSocket connection closed")
    pygame.quit()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Game terminated by user")
            pygame.quit()