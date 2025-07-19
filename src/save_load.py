import json
import os
import logging
from settings import BASE_DIR, DAY_DURATION

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing save_load.py")

def save_game(player, world, day, quota, cash_earned_today, upgrades_cfg, time_left):
    if os.environ.get("PYODIDE"):
        logger.warning("Saving not supported in Pyodide environment")
        return
    save_data = {
        "player": {
            "pos_x": player.pos_x,
            "pos_y": player.pos_y,
            "health": player.health,
            "cash": player.cash,
            "inventory": player.inventory,
            "pick_index": player.pick_index,
            "pick_speed": player.pick_speed,
            "current_upgrades": player.current_upgrades,
            "mining_speed_boost": player.mining_speed_boost,
            "jump_boost": player.jump_boost,
            "aoe_mining": player.aoe_mining,
            "rock_damage_reduction": player.rock_damage_reduction,
            "lucky_miner": player.lucky_miner,
            "ore_magnet": player.ore_magnet,
            "melee_upgrade": player.melee_upgrade,
            "blaster": player.blaster,
            "quantum_pickaxe": player.quantum_pickaxe,
            "shield_generator": player.shield_generator,
            "active_effects": {
                effect: {
                    "active": data["active"],
                    "duration": data["duration"],
                    "start_time": data["start_time"]
                } for effect, data in player.active_effects.items()
            },
            "quota_buffer": player.quota_buffer,
            "day_extension": player.day_extension,
            "efficiency_boost": player.efficiency_boost,
            "ore_scanner": player.ore_scanner,
            "cash_multiplier": player.cash_multiplier
        },
        "world": {
            "block_cols": {f"{x},{y}": block_type for (x, y), block_type in world.block_cols.items()}
        },
        "game": {
            "day": day,
            "quota": quota,
            "cash_earned_today": cash_earned_today,
            "time_left": time_left
        },
        "upgrades": {
            "pickaxes": [
                {"name": pick["name"], "cost": pick["cost"], "speed": pick["speed"], "unlocked": pick.get("unlocked", False)}
                for pick in upgrades_cfg["pickaxes"]
            ],
            "shop": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "cost": item["cost"],
                    "unlocked": item.get("unlocked", True),
                    "description": item.get("description", "")
                }
                for item in upgrades_cfg.get("shop", [])
            ]
        }
    }
    save_path = os.path.join(BASE_DIR, "savegame.json")
    try:
        with open(save_path, "w") as f:
            json.dump(save_data, f, indent=4)
        logger.info("Game saved successfully")
    except Exception as e:
        logger.error(f"Failed to save game: {e}")

def load_game(player, upgrades_cfg):
    if os.environ.get("PYODIDE"):
        logger.warning("Loading not supported in Pyodide environment")
        return None, 1, 200, 0, DAY_DURATION
    save_path = os.path.join(BASE_DIR, "savegame.json")
    if not os.path.exists(save_path):
        logger.info("No save file found, starting new game")
        return None, 1, 200, 0, DAY_DURATION

    try:
        with open(save_path, "r") as f:
            data = json.load(f)
        
        # Load player data
        player_data = data.get("player", {})
        player.pos_x = player_data.get("pos_x", 0)
        player.pos_y = player_data.get("pos_y", 0)
        player.rect.x = int(player.pos_x)
        player.rect.y = int(player.pos_y)
        player.health = player_data.get("health", 100)
        player.cash = player_data.get("cash", 0)
        player.inventory = player_data.get("inventory", {})
        player.pick_index = player_data.get("pick_index", 0)
        player.pick_speed = player_data.get("pick_speed", 1.0)
        player.current_upgrades = player_data.get("current_upgrades", [])
        player.mining_speed_boost = player_data.get("mining_speed_boost", 1.0)
        player.jump_boost = player_data.get("jump_boost", 1.0)
        player.aoe_mining = player_data.get("aoe_mining", 0)
        player.rock_damage_reduction = player_data.get("rock_damage_reduction", 0.0)
        player.lucky_miner = player_data.get("lucky_miner", False)
        player.ore_magnet = player_data.get("ore_magnet", False)
        player.melee_upgrade = player_data.get("melee_upgrade", False)
        player.blaster = player_data.get("blaster", False)
        player.quantum_pickaxe = player_data.get("quantum_pickaxe", False)
        player.shield_generator = player_data.get("shield_generator", False)
        player.active_effects = player_data.get("active_effects", {})
        player.quota_buffer = player_data.get("quota_buffer", 0)
        player.day_extension = player_data.get("day_extension", 0)
        player.efficiency_boost = player_data.get("efficiency_boost", 1.0)
        player.ore_scanner = player_data.get("ore_scanner", False)
        player.cash_multiplier = player_data.get("cash_multiplier", 1.0)

        # Load world data
        block_cols = {
            tuple(map(int, k.split(","))): v
            for k, v in data.get("world", {}).get("block_cols", {}).items()
        }

        # Load game data
        game_data = data.get("game", {})
        day = game_data.get("day", 1)
        quota = game_data.get("quota", 200)
        cash_earned_today = game_data.get("cash_earned_today", 0)
        time_left = game_data.get("time_left", DAY_DURATION)

        # Load upgrades
        upgrades_data = data.get("upgrades", {})
        upgrades_cfg["pickaxes"] = [
            {
                "name": pick["name"],
                "cost": pick["cost"],
                "speed": pick["speed"],
                "unlocked": pick.get("unlocked", False)
            }
            for pick in upgrades_data.get("pickaxes", upgrades_cfg["pickaxes"])
        ]
        upgrades_cfg["shop"] = [
            {
                "id": item["id"],
                "name": item["name"],
                "cost": item["cost"],
                "unlocked": item.get("unlocked", True),
                "description": item.get("description", "")
            }
            for item in upgrades_data.get("shop", upgrades_cfg.get("shop", []))
        ]

        logger.info("Game state loaded successfully")
        return block_cols, day, quota, cash_earned_today, time_left

    except json.JSONDecodeError as e:
        logger.error(f"Failed to load save file due to JSON error: {e}")
        logger.info("Starting new game due to corrupted save file")
        return None, 1, 200, 0, DAY_DURATION
    except Exception as e:
        logger.error(f"Unexpected error loading save file: {e}")
        logger.info("Starting new game due to save file error")
        return None, 1, 200, 0, DAY_DURATION