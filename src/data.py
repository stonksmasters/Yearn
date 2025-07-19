import json
import os
from settings import BASE_DIR

def load_ores():
    try:
        with open(os.path.join(BASE_DIR, "data", "ores.json"), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Pyodide fallback or default data if file is missing
        return {
            "dirt": {"color": (139, 69, 19), "value": 1, "time": 0.5},
            "stone": {"color": (128, 128, 128), "value": 2, "time": 1.0},
            "iron": {"color": (192, 192, 192), "value": 5, "time": 1.5},
            "gold": {"color": (255, 215, 0), "value": 10, "time": 2.0},
            "ruby": {"color": (255, 0, 0), "value": 50, "time": 3.0},
            "sapphire": {"color": (0, 0, 255), "value": 50, "time": 3.0},
            "emerald": {"color": (0, 255, 0), "value": 50, "time": 3.0},
            "mithril": {"color": (0, 255, 255), "value": 100, "time": 4.0},
            "cave_wall": {"color": (100, 100, 100), "value": 0, "time": 2.0},
            "crystal_wall": {"color": (200, 200, 255), "value": 0, "time": 2.5}
        }

def load_upgrades():
    try:
        with open(os.path.join(BASE_DIR, "data", "upgrades.json"), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Pyodide fallback or default data if file is missing
        return {
            "pickaxes": [
                {"name": "Basic Pickaxe", "cost": 0, "speed": 1.0, "unlocked": True},
                {"name": "Iron Pickaxe", "cost": 500, "speed": 1.5},
                {"name": "Steel Pickaxe", "cost": 2000, "speed": 2.0},
                {"name": "Diamond Pickaxe", "cost": 5000, "speed": 3.0}
            ],
            "shop": [
                {"id": "dynamite", "name": "Dynamite", "cost": 100, "unlocked": True},
                {"id": "health_pack", "name": "Health Pack", "cost": 50, "unlocked": True},
                {"id": "earthquake", "name": "Earthquake", "cost": 500, "unlocked": True},
                {"id": "depth_charge", "name": "Depth Charge", "cost": 300, "unlocked": True},
                {"id": "speed_boost", "name": "Speed Boost", "cost": 200, "unlocked": True},
                {"id": "safety_bubble", "name": "Safety Bubble", "cost": 200, "unlocked": True},
                {"id": "ore_magnet", "name": "Ore Magnet", "cost": 1000},
                {"id": "storage_upgrade", "name": "Storage Upgrade", "cost": 1000, "unlocked": True},
                {"id": "time_extender", "name": "Time Extender", "cost": 500, "unlocked": True},
                {"id": "efficiency_module", "name": "Efficiency Module", "cost": 750, "unlocked": True},
                {"id": "ore_scanner", "name": "Ore Scanner", "cost": 1500},
                {"id": "reinforced_boots", "name": "Reinforced Boots", "cost": 1000, "unlocked": True},
                {"id": "lucky_charm", "name": "Lucky Charm", "cost": 2000},
                {"id": "xray_vision", "name": "X-Ray Vision", "cost": 3000},
                {"id": "teleporter", "name": "Teleporter", "cost": 5000},
                {"id": "auto_miner_drone", "name": "Auto-Miner Drone", "cost": 4000},
                {"id": "health_boost", "name": "Health Boost", "cost": 1000, "unlocked": True},
                {"id": "cash_multiplier", "name": "Cash Multiplier", "cost": 10000},
                {"id": "blaster", "name": "Blaster", "cost": 3000},
                {"id": "melee_upgrade", "name": "Melee Upgrade", "cost": 2000},
                {"id": "quantum_pickaxe", "name": "Quantum Pickaxe", "cost": 10000},
                {"id": "shield_generator", "name": "Shield Generator", "cost": 7500}
            ]
        }