import pygame
import asyncio
import logging
import os
import platform
from game import Game
from data import load_ores, load_upgrades
from settings import *

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

async def main():
    pygame.init()
    verify_files()
    upgrades = load_upgrades()
    ores = load_ores()
    
    # Ensure pickaxes have unlocked state
    for i, pick in enumerate(upgrades['pickaxes']):
        pick.setdefault('unlocked', i == 0)
    
    game = Game(upgrades, ores)
    logger.info("Starting game loop")
    await game.run()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())