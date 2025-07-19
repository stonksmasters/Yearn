import asyncio
import websockets
import json
import logging
import random
import string
import time
from datetime import datetime
from settings import TILE_SIZE, NUM_COLS, MAX_DEPTH, QUOTA_BASE, QUOTA_INCREASE, DAY_DURATION

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Game state
LOBBIES = {}  # {lobby_code: {players: {player_id: {...}}, world_state: {}, entities: {}, seed: int, day: int, quota: float, cash_earned_today: float, day_start_time: float, time_left: float, ores_mined: int, diamonds_mined: int, milestones: dict}}
PLAYERS = {}  # {player_id: {websocket, lobby_code, x, y, health, inventory, ore_slots, cash, upgrades, pick_index, pick_speed, active_effects, mining_speed_boost, jump_boost, aoe_mining, rock_damage_reduction, lucky_miner, ore_magnet, ore_pickup_range, melee_upgrade, blaster, quantum_pickaxe, shield_generator, max_ore_slots, day_extension, quota_buffer}}
entity_id_counter = 0

def generate_lobby_code():
    """Generate a unique 4-character lobby code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

async def handler(websocket, path=None):
    """Handle WebSocket connections for each player."""
    player_id = f"player_{len(PLAYERS)}"
    PLAYERS[player_id] = {
        "websocket": websocket,
        "lobby_code": None,
        "x": NUM_COLS * TILE_SIZE // 2,
        "y": 0,
        "health": 100,
        "inventory": {"dynamite": 0, "health_pack": 0, "earthquake": 0, "depth_charge": 0, "bat_wing": 0, "goblin_tooth": 0},
        "ore_slots": [None] * 9,
        "cash": 0.0,
        "upgrades": [],
        "pick_index": 0,
        "pick_speed": 1.0,
        "active_effects": {},
        "mining_speed_boost": 1.0,
        "jump_boost": 0.0,
        "aoe_mining": 0,
        "rock_damage_reduction": 0.0,
        "lucky_miner": False,
        "ore_magnet": False,
        "ore_pickup_range": 1.0,
        "melee_upgrade": False,
        "blaster": False,
        "quantum_pickaxe": False,
        "shield_generator": False,
        "max_ore_slots": 9,
        "day_extension": 0.0,
        "quota_buffer": 0.0,
        "last_update": time.time()
    }
    logger.info(f"{player_id} connected at {datetime.now()}")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                action = data.get("action")
                logger.debug(f"Received action from {player_id}: {action}")

                if action == "create_lobby":
                    lobby_code = generate_lobby_code()
                    while lobby_code in LOBBIES:
                        lobby_code = generate_lobby_code()
                    LOBBIES[lobby_code] = {
                        "players": {player_id: PLAYERS[player_id]},
                        "world_state": {},
                        "entities": {},
                        "seed": random.randint(0, 1000000),
                        "day": 1,
                        "quota": QUOTA_BASE,
                        "cash_earned_today": 0.0,
                        "day_start_time": time.time(),
                        "time_left": DAY_DURATION,
                        "ores_mined": 0,
                        "diamonds_mined": 0,
                        "milestones": {
                            "depth": {10000 * i: False for i in range(1, 11)},
                            "ores_mined": {1000 * i: False for i in range(1, 11)},
                            "diamonds_mined": {10 * i: False for i in range(1, 6)}
                        }
                    }
                    PLAYERS[player_id]["lobby_code"] = lobby_code
                    await websocket.send(json.dumps({
                        "type": "lobby_created",
                        "lobby_code": lobby_code,
                        "player_id": player_id,
                        "world_seed": LOBBIES[lobby_code]["seed"],
                        "world_state": LOBBIES[lobby_code]["world_state"],
                        "players": {},
                        "entities": LOBBIES[lobby_code]["entities"],
                        "day": LOBBIES[lobby_code]["day"],
                        "quota": LOBBIES[lobby_code]["quota"],
                        "time_left": LOBBIES[lobby_code]["time_left"]
                    }))
                    logger.info(f"{player_id} created lobby {lobby_code}")

                elif action == "join_lobby":
                    lobby_code = data.get("lobby_code").upper()
                    if lobby_code in LOBBIES:
                        LOBBIES[lobby_code]["players"][player_id] = PLAYERS[player_id]
                        PLAYERS[player_id]["lobby_code"] = lobby_code
                        await websocket.send(json.dumps({
                            "type": "lobby_joined",
                            "lobby_code": lobby_code,
                            "player_id": player_id,
                            "world_seed": LOBBIES[lobby_code]["seed"],
                            "world_state": LOBBIES[lobby_code]["world_state"],
                            "players": {pid: {"x": p["x"], "y": p["y"], "health": p["health"]} for pid, p in LOBBIES[lobby_code]["players"].items() if pid != player_id},
                            "entities": LOBBIES[lobby_code]["entities"],
                            "day": LOBBIES[lobby_code]["day"],
                            "quota": LOBBIES[lobby_code]["quota"],
                            "time_left": LOBBIES[lobby_code]["time_left"]
                        }))
                        await broadcast_to_lobby(lobby_code, {
                            "type": "player_joined",
                            "id": player_id,
                            "x": PLAYERS[player_id]["x"],
                            "y": PLAYERS[player_id]["y"],
                            "health": PLAYERS[player_id]["health"]
                        }, exclude=player_id)
                        logger.info(f"{player_id} joined lobby {lobby_code}")
                    else:
                        await websocket.send(json.dumps({"type": "error", "message": "Invalid lobby code"}))
                        logger.warning(f"{player_id} attempted to join invalid lobby {lobby_code}")

                elif action == "update_position":
                    lobby_code = PLAYERS[player_id]["lobby_code"]
                    if lobby_code and is_valid_position(data.get("x"), data.get("y")):
                        PLAYERS[player_id]["x"] = data["x"]
                        PLAYERS[player_id]["y"] = data["y"]
                        PLAYERS[player_id]["last_update"] = time.time()
                        await broadcast_to_lobby(lobby_code, {
                            "type": "player_update",
                            "id": player_id,
                            "x": data["x"],
                            "y": data["y"],
                            "health": PLAYERS[player_id]["health"]
                        }, exclude=player_id)
                        await check_milestones(lobby_code, player_id)

                elif action == "mine_block":
                    lobby_code = PLAYERS[player_id]["lobby_code"]
                    if lobby_code and is_valid_mining(player_id, data["block_x"], data["block_y"]):
                        block_x, block_y = data["block_x"], data["block_y"]
                        block_type = LOBBIES[lobby_code]["world_state"].get((block_x, block_y), get_block_type(block_y))
                        LOBBIES[lobby_code]["world_state"][(block_x, block_y)] = "empty"
                        if block_type not in ["empty", "grass"]:
                            spawn_ore(lobby_code, block_x, block_y, block_type)
                            LOBBIES[lobby_code]["ores_mined"] += 1
                            if block_type == "diamond":
                                LOBBIES[lobby_code]["diamonds_mined"] += 1
                        await broadcast_to_lobby(lobby_code, {
                            "type": "block_mined",
                            "block_x": block_x,
                            "block_y": block_y
                        })
                        await check_milestones(lobby_code, player_id)
                        logger.info(f"{player_id} mined block {block_type} at ({block_x}, {block_y}) in lobby {lobby_code}")

                elif action == "collect_ore":
                    lobby_code = PLAYERS[player_id]["lobby_code"]
                    ore_id = data["ore_id"]
                    if lobby_code and is_valid_collection(player_id, ore_id, lobby_code):
                        ore_data = LOBBIES[lobby_code]["entities"].get(ore_id)
                        if ore_data and add_ore_to_inventory(player_id, ore_data["ore_type"], ore_data["value"]):
                            total_value = ore_data["value"] * (2 if ore_data["ore_type"] == "diamond" else 1)
                            LOBBIES[lobby_code]["cash_earned_today"] += total_value
                            PLAYERS[player_id]["cash"] += total_value
                            PLAYERS[player_id]["quota_buffer"] += total_value
                            del LOBBIES[lobby_code]["entities"][ore_id]
                            await broadcast_to_lobby(lobby_code, {
                                "type": "ore_collected",
                                "ore_id": ore_id,
                                "player_id": player_id,
                                "cash_earned": total_value
                            })
                            logger.info(f"{player_id} collected ore {ore_id} worth ${total_value:.2f} in lobby {lobby_code}")

                elif action == "use_item":
                    lobby_code = PLAYERS[player_id]["lobby_code"]
                    item_id = data["item_id"]
                    if lobby_code and is_valid_item_use(player_id, item_id):
                        player = PLAYERS[player_id]
                        if item_id == "dynamite":
                            for dx in range(-5, 6):
                                for dy in range(-5, 6):
                                    bx = int(player["x"] // TILE_SIZE + dx)
                                    by = int(player["y"] // TILE_SIZE + dy)
                                    if 0 <= bx < NUM_COLS and 0 <= by < MAX_DEPTH:
                                        block_type = LOBBIES[lobby_code]["world_state"].get((bx, by), get_block_type(by))
                                        if block_type not in ["empty", "grass"]:
                                            LOBBIES[lobby_code]["world_state"][(bx, by)] = "empty"
                                            spawn_ore(lobby_code, bx, by, block_type)
                                            LOBBIES[lobby_code]["ores_mined"] += 1
                                            if block_type == "diamond":
                                                LOBBIES[lobby_code]["diamonds_mined"] += 1
                                            await broadcast_to_lobby(lobby_code, {
                                                "type": "block_mined",
                                                "block_x": bx,
                                                "block_y": by
                                            })
                        elif item_id == "health_pack":
                            player["health"] = min(100, player["health"] + 50)
                            await broadcast_to_lobby(lobby_code, {
                                "type": "player_update",
                                "id": player_id,
                                "x": player["x"],
                                "y": player["y"],
                                "health": player["health"]
                            })
                        elif item_id == "earthquake":
                            center_x = int(player["x"] // TILE_SIZE)
                            for depth in range(int(player["y"] // TILE_SIZE), MAX_DEPTH):
                                if 0 <= center_x < NUM_COLS:
                                    block_type = LOBBIES[lobby_code]["world_state"].get((center_x, depth), get_block_type(depth))
                                    if block_type and block_type != "empty":
                                        LOBBIES[lobby_code]["world_state"][(center_x, depth)] = "empty"
                                        spawn_ore(lobby_code, center_x, depth, block_type)
                                        LOBBIES[lobby_code]["ores_mined"] += 1
                                        if block_type == "diamond":
                                            LOBBIES[lobby_code]["diamonds_mined"] += 1
                                        await broadcast_to_lobby(lobby_code, {
                                            "type": "block_mined",
                                            "block_x": center_x,
                                            "block_y": depth
                                        })
                        elif item_id == "depth_charge":
                            bx = int(data.get("x", player["x"]) // TILE_SIZE)
                            by = int(data.get("y", player["y"]) // TILE_SIZE)
                            for dx in range(-3, 4):
                                for dy in range(-3, 4):
                                    if 0 <= bx + dx < NUM_COLS and 0 <= by + dy < MAX_DEPTH:
                                        block_type = LOBBIES[lobby_code]["world_state"].get((bx + dx, by + dy), get_block_type(by + dy))
                                        if block_type not in ["empty", "grass"]:
                                            LOBBIES[lobby_code]["world_state"][(bx + dx, by + dy)] = "empty"
                                            spawn_ore(lobby_code, bx + dx, by + dy, block_type)
                                            LOBBIES[lobby_code]["ores_mined"] += 1
                                            if block_type == "diamond":
                                                LOBBIES[lobby_code]["diamonds_mined"] += 1
                                            await broadcast_to_lobby(lobby_code, {
                                                "type": "block_mined",
                                                "block_x": bx + dx,
                                                "block_y": by + dy
                                            })
                        elif item_id == "bat_wing":
                            player["active_effects"]["speed_boost"] = {"active": True, "end_time": time.time() + 30}
                            player["mining_speed_boost"] += 0.5
                        elif item_id == "goblin_tooth":
                            player["active_effects"]["safety_bubble"] = {"active": True, "end_time": time.time() + 30}
                            player["rock_damage_reduction"] += 0.2
                        await broadcast_to_lobby(lobby_code, {
                            "type": "item_used",
                            "player_id": player_id,
                            "item_id": item_id
                        })
                        await check_milestones(lobby_code, player_id)
                        logger.info(f"{player_id} used item {item_id} in lobby {lobby_code}")

                elif action == "drop_ore":
                    lobby_code = PLAYERS[player_id]["lobby_code"]
                    if lobby_code and PLAYERS[player_id]["y"] < TILE_SIZE:
                        total_value = 0
                        for slot in PLAYERS[player_id]["ore_slots"]:
                            if slot:
                                total_value += slot["value"] * slot["count"]
                                slot["count"] = 0
                                slot = None
                        PLAYERS[player_id]["cash"] += total_value
                        PLAYERS[player_id]["quota_buffer"] += total_value
                        LOBBIES[lobby_code]["cash_earned_today"] += total_value
                        await broadcast_to_lobby(lobby_code, {
                            "type": "ore_dropped",
                            "player_id": player_id,
                            "cash_earned": total_value
                        })
                        logger.info(f"{player_id} dropped off ores for ${total_value:.2f} in lobby {lobby_code}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {player_id}: {message}")
            except KeyError as e:
                logger.error(f"Missing key in message from {player_id}: {e}")

    except websockets.ConnectionClosed:
        lobby_code = PLAYERS[player_id]["lobby_code"]
        if lobby_code and player_id in LOBBIES[lobby_code]["players"]:
            del LOBBIES[lobby_code]["players"][player_id]
            if not LOBBIES[lobby_code]["players"]:
                del LOBBIES[lobby_code]
                logger.info(f"Lobby {lobby_code} closed (no players)")
            else:
                await broadcast_to_lobby(lobby_code, {"type": "player_left", "id": player_id}, exclude=player_id)
        del PLAYERS[player_id]
        logger.info(f"{player_id} disconnected at {datetime.now()}")

async def broadcast_to_lobby(lobby_code, message, exclude=None):
    """Broadcast a message to all players in a lobby, optionally excluding one."""
    if lobby_code in LOBBIES:
        message_str = json.dumps(message)
        for player_id, player in list(LOBBIES[lobby_code]["players"].items()):
            if player_id != exclude:
                try:
                    await player["websocket"].send(message_str)
                except websockets.ConnectionClosed:
                    del LOBBIES[lobby_code]["players"][player_id]
                    del PLAYERS[player_id]
                    await broadcast_to_lobby(lobby_code, {"type": "player_left", "id": player_id}, exclude=player_id)
                    logger.info(f"{player_id} disconnected during broadcast")

def spawn_ore(lobby_code, block_x, block_y, ore_type):
    """Spawn an ore item in the specified lobby."""
    global entity_id_counter
    entity_id = f"entity_{entity_id_counter}"
    entity_id_counter += 1
    value = get_ore_value(ore_type, block_y)
    LOBBIES[lobby_code]["entities"][entity_id] = {
        "type": "ore",
        "x": block_x * TILE_SIZE + TILE_SIZE // 2,
        "y": block_y * TILE_SIZE + TILE_SIZE // 2,
        "ore_type": ore_type,
        "value": value,
        "creation_time": time.time()
    }
    asyncio.create_task(broadcast_to_lobby(lobby_code, {
        "type": "spawn_entity",
        "entity_id": entity_id,
        "entity_data": LOBBIES[lobby_code]["entities"][entity_id]
    }))
    logger.debug(f"Spawned ore {entity_id} ({ore_type}) at ({block_x}, {block_y}) in lobby {lobby_code}")

def get_block_type(block_y):
    """Determine block type based on depth (simplified for server)."""
    depth = block_y * TILE_SIZE
    if depth < 1:
        return "grass"
    elif depth < 50:
        return random.choice(["dirt", "stone"])
    elif depth < 300:
        return random.choice(["stone", "iron", "coal"])
    elif depth < 500:
        return random.choice(["iron", "gold", "ruby"])
    elif depth < 1000:
        return random.choice(["ruby", "sapphire", "emerald"])
    else:
        return random.choice(["mithril", "diamond"])

def is_valid_position(x, y):
    """Validate player position within world bounds."""
    return 0 <= x <= NUM_COLS * TILE_SIZE and 0 <= y <= MAX_DEPTH * TILE_SIZE

def is_valid_mining(player_id, block_x, block_y):
    """Validate mining action based on player proximity and block validity."""
    if not (0 <= block_x < NUM_COLS and 0 <= block_y < MAX_DEPTH):
        return False
    player = PLAYERS.get(player_id)
    if not player:
        return False
    player_x, player_y = player["x"], player["y"]
    distance = ((player_x - (block_x * TILE_SIZE + TILE_SIZE // 2)) ** 2 + (player_y - (block_y * TILE_SIZE + TILE_SIZE // 2)) ** 2) ** 0.5
    mining_range = 2 * TILE_SIZE * player["ore_pickup_range"]
    return distance <= mining_range

def is_valid_collection(player_id, ore_id, lobby_code):
    """Validate ore collection based on proximity."""
    player = PLAYERS.get(player_id)
    ore = LOBBIES[lobby_code]["entities"].get(ore_id)
    if not player or not ore or ore["type"] != "ore":
        return False
    distance = ((player["x"] - ore["x"]) ** 2 + (player["y"] - ore["y"]) ** 2) ** 0.5
    pickup_range = 3 * TILE_SIZE * player["ore_pickup_range"]
    return distance <= pickup_range

def is_valid_item_use(player_id, item_id):
    """Validate item use based on inventory."""
    player = PLAYERS.get(player_id)
    if not player or item_id not in player["inventory"]:
        return False
    if player["inventory"][item_id] > 0:
        player["inventory"][item_id] -= 1
        return True
    return False

def add_ore_to_inventory(player_id, ore_type, value):
    """Add ore to player's inventory, respecting stack limits."""
    player = PLAYERS.get(player_id)
    if not player:
        return False
    for slot in player["ore_slots"]:
        if slot and slot["type"] == ore_type and slot["count"] < 64:
            slot["count"] += 1
            return True
    for i in range(len(player["ore_slots"])):
        if player["ore_slots"][i] is None:
            player["ore_slots"][i] = {"type": ore_type, "value": value, "count": 1}
            return True
    return False

def get_ore_value(ore_type, block_y):
    """Calculate ore value based on depth zone."""
    depth_zones = [
        {"depth": 0, "value_scale": 1.0},
        {"depth": 1, "value_scale": 1.0},
        {"depth": 50, "value_scale": 1.5},
        {"depth": 300, "value_scale": 2.0},
        {"depth": 500, "value_scale": 3.0},
        {"depth": 1000, "value_scale": 5.0}
    ]
    base_values = {
        "dirt": 1, "stone": 2, "coal": 3, "iron": 5, "gold": 10, "ruby": 50, "sapphire": 50,
        "emerald": 50, "mithril": 100, "diamond": 200
    }
    zone = depth_zones[0]
    for z in depth_zones:
        if block_y * TILE_SIZE >= z["depth"]:
            zone = z
        else:
            break
    return base_values.get(ore_type, 0) * zone["value_scale"]

async def check_milestones(lobby_code, player_id):
    """Check and apply milestones for the lobby."""
    if lobby_code not in LOBBIES:
        return
    lobby = LOBBIES[lobby_code]
    max_depth = max(p["y"] // TILE_SIZE for p in lobby["players"].values())
    shop_unlocks = {
        1000: ["ore_magnet"],
        5000: ["auto_miner_drone", "blaster"],
        10000: ["teleporter"],
        20000: ["xray_vision"],
        50000: ["cash_multiplier"],
        75000: ["quantum_pickaxe", "shield_generator"]
    }
    for milestone_depth, achieved in lobby["milestones"]["depth"].items():
        if max_depth >= milestone_depth and not achieved:
            lobby["milestones"]["depth"][milestone_depth] = True
            for pid in lobby["players"]:
                PLAYERS[pid]["cash"] += 1000
                PLAYERS[pid]["inventory"]["health_pack"] = PLAYERS[pid]["inventory"].get("health_pack", 0) + 1
            for item_id in shop_unlocks.get(milestone_depth, []):
                for pid in lobby["players"]:
                    PLAYERS[pid]["upgrades"].append(item_id)
                    if item_id == "ore_magnet":
                        PLAYERS[pid]["ore_magnet"] = True
                    elif item_id == "auto_miner_drone":
                        PLAYERS[pid]["active_effects"]["auto_miner"] = {"active": True, "end_time": float('inf')}
                    elif item_id == "blaster":
                        PLAYERS[pid]["blaster"] = True
                    elif item_id == "teleporter":
                        PLAYERS[pid]["jump_boost"] += 1.0
                    elif item_id == "xray_vision":
                        PLAYERS[pid]["lucky_miner"] = True
                    elif item_id == "cash_multiplier":
                        PLAYERS[pid]["mining_speed_boost"] += 0.5
                    elif item_id == "quantum_pickaxe":
                        PLAYERS[pid]["quantum_pickaxe"] = True
                        PLAYERS[pid]["aoe_mining"] = max(2, PLAYERS[pid]["aoe_mining"])
                    elif item_id == "shield_generator":
                        PLAYERS[pid]["shield_generator"] = True
                        PLAYERS[pid]["rock_damage_reduction"] += 0.5
            await broadcast_to_lobby(lobby_code, {
                "type": "milestone_achieved",
                "milestone_type": "depth",
                "value": milestone_depth,
                "reward": {"cash": 1000, "health_pack": 1}
            })
            logger.info(f"Depth milestone {milestone_depth} achieved in lobby {lobby_code}")
            if milestone_depth >= 75000:
                await broadcast_to_lobby(lobby_code, {
                    "type": "lava_hazard_activated"
                })
                logger.info(f"Lava hazard activated in lobby {lobby_code}")
    for milestone_ores, achieved in lobby["milestones"]["ores_mined"].items():
        if lobby["ores_mined"] >= milestone_ores and not achieved:
            lobby["milestones"]["ores_mined"][milestone_ores] = True
            for pid in lobby["players"]:
                PLAYERS[pid]["cash"] += 500
                PLAYERS[pid]["inventory"]["dynamite"] = PLAYERS[pid]["inventory"].get("dynamite", 0) + 1
            await broadcast_to_lobby(lobby_code, {
                "type": "milestone_achieved",
                "milestone_type": "ores_mined",
                "value": milestone_ores,
                "reward": {"cash": 500, "dynamite": 1}
            })
            logger.info(f"Ores mined milestone {milestone_ores} achieved in lobby {lobby_code}")
    for milestone_diamonds, achieved in lobby["milestones"]["diamonds_mined"].items():
        if lobby["diamonds_mined"] >= milestone_diamonds and not achieved:
            lobby["milestones"]["diamonds_mined"][milestone_diamonds] = True
            for pid in lobby["players"]:
                PLAYERS[pid]["cash"] += 500
                PLAYERS[pid]["inventory"]["health_pack"] = PLAYERS[pid]["inventory"].get("health_pack", 0) + 1
            await broadcast_to_lobby(lobby_code, {
                "type": "milestone_achieved",
                "milestone_type": "diamonds_mined",
                "value": milestone_diamonds,
                "reward": {"cash": 500, "health_pack": 1}
            })
            logger.info(f"Diamonds mined milestone {milestone_diamonds} achieved in lobby {lobby_code}")

async def handle_player_death(player_id):
    """Handle player death: respawn and drop items."""
    player = PLAYERS.get(player_id)
    if not player:
        return
    lobby_code = player["lobby_code"]
    if not lobby_code:
        return
    player["x"] = NUM_COLS * TILE_SIZE // 2
    player["y"] = 0
    player["health"] = 100
    for item_id, count in list(player["inventory"].items()):
        if count > 0 and random.random() < 0.5:
            player["inventory"][item_id] -= 1
            spawn_ore(lobby_code, player["x"] // TILE_SIZE, player["y"] // TILE_SIZE, item_id)
    await broadcast_to_lobby(lobby_code, {
        "type": "player_update",
        "id": player_id,
        "x": player["x"],
        "y": player["y"],
        "health": player["health"]
    })
    logger.info(f"{player_id} died and respawned in lobby {lobby_code}")

async def update_lobbies():
    """Update lobby states, including day progression and lava hazards."""
    while True:
        for lobby_code, lobby in list(LOBBIES.items()):
            lobby["time_left"] = max(0, lobby["time_left"] - 0.1)
            if lobby["time_left"] <= 0:
                if lobby["cash_earned_today"] >= lobby["quota"]:
                    lobby["day"] += 1
                    lobby["time_left"] = DAY_DURATION
                    lobby["quota"] *= QUOTA_INCREASE
                    lobby["cash_earned_today"] = max(0, lobby["cash_earned_today"] - lobby["quota"])
                    for pid in lobby["players"]:
                        PLAYERS[pid]["cash"] += lobby["cash_earned_today"]
                    await broadcast_to_lobby(lobby_code, {
                        "type": "next_day",
                        "day": lobby["day"],
                        "quota": lobby["quota"],
                        "time_left": lobby["time_left"]
                    })
                    logger.info(f"Lobby {lobby_code} advanced to day {lobby['day']}, new quota ${lobby['quota']:.2f}")
                else:
                    await broadcast_to_lobby(lobby_code, {
                        "type": "game_over",
                        "reason": "Quota not met"
                    })
                    del LOBBIES[lobby_code]
                    for pid in list(lobby["players"].keys()):
                        PLAYERS[pid]["lobby_code"] = None
                    logger.info(f"Lobby {lobby_code} closed: Quota not met")
            if any(lobby["milestones"]["depth"].get(75000, False) for _ in lobby["players"]):
                for pid, player in list(lobby["players"].items()):
                    if not player["active_effects"].get("safety_bubble", {}).get("active", False):
                        player["health"] = max(0, player["health"] - 5)
                        if player["health"] <= 0:
                            await handle_player_death(pid)
                        await broadcast_to_lobby(lobby_code, {
                            "type": "player_update",
                            "id": pid,
                            "x": player["x"],
                            "y": player["y"],
                            "health": player["health"]
                        })
        await asyncio.sleep(0.1)

async def main():
    """Start the WebSocket server and background tasks."""
    server = await websockets.serve(handler, "localhost", 8765)
    logger.info("Server running on ws://localhost:8765")
    asyncio.create_task(update_lobbies())
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())