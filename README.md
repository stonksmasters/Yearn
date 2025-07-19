Yearn – Ultimate Miner

Yearn – Ultimate Miner is a 2D mining roguelike game developed using Pygame, designed to run seamlessly both locally with CPython and in web browsers via Pyodide. Players dive into procedurally generated underground layers, mining ores, managing resources, upgrading equipment, and surviving daily quotas amidst environmental hazards and enemies. The game now supports local co-op and is being extended to include online multiplayer functionality, making it a collaborative mining adventure.
This README provides an in-depth guide to the game’s features, project structure, installation, controls, and a detailed section on setting up online multiplayer using WebSockets for real-time player interaction.

🚀 Features

Procedural World Generation:Infinite vertical layers with depth-based ore distribution (e.g., coal at shallow depths, diamonds deeper) and environmental hazards like cave-ins and gas pockets.

Mining Mechanics:  

Click-to-mine blocks with upgradeable pickaxes (e.g., steel, diamond, quantum).  
Area-of-effect (AOE) mining with dynamite or blasters.  
Special tools like quantum pickaxes for instant block destruction.


Resource Management:  

Earn cash by dropping off ores at the surface.  
Meet increasing daily quotas (e.g., Day 1: $1000, Day 2: $1200).  
Unlock milestone rewards for hitting depth or cash goals.


Upgrade System:  

Shop items: dynamite, teleporters, ore magnets, health packs.  
Pickaxe upgrades: speed, power, range.  
Persistent upgrades saved across sessions.


Entity System:  

Particles: Visual effects for mining, explosions, and treasure sparkles.  
Falling Rocks: Dynamic hazards that damage players.  
Enemies: Bats, goblins, abyss wraiths with unique drops (e.g., bat wings, goblin teeth).  
OreItems: Collectible resources with immediate removal on pickup.


Ore Pickup Range:  

Automatically collect ores within a configurable radius (default: 50 pixels).  
Upgrades increase range (e.g., Ore Magnet: +25 pixels per level).


Animated Ore Collection:  

Ores within pickup range animate smoothly toward the player with a lerp-based movement (speed: 200 pixels/second).  
Added to inventory once they reach the player’s position.


Ore Drop-Off:  

Press 'O' at the surface to cash in ores.  
On-screen notifications display earnings (e.g., “+500 cash”).


Persistent Save/Load:  

Save progress to local files (CPython) or browser storage (Pyodide).  
Multiple save slots for flexibility.


User Interface:  

HUD: Cash, quota progress, day timer, depth meter.  
Menus: Start, pause, upgrade shop, inventory, post-day upgrade selector.  
Debug Overlays: FPS, entity count, player coords.  
Minimap: Shows explored areas and player position.


Multiplayer:  

Local co-op: Two players on the same screen with split controls.  
Online multiplayer (in progress): Real-time collaboration via WebSockets.


Recent Updates:  

Fixed NameError in player.py by adding missing import.  
Enhanced logging for ore collection and animation debugging.  
Improved Pyodide compatibility with async event handling.




📁 Project Structure
The project follows a modular design to separate concerns, making it easy to maintain and extend, especially for adding online multiplayer features.
Roguelike/
├── src/
│   ├── main.py            # Entry point; initializes game and runs async loop
│   ├── game.py            # Core game loop, state coordination, and multiplayer sync
│   ├── data.py            # Loads JSON data for ores and upgrades
│   ├── settings.py        # Constants: screen size, quotas, key bindings
│   ├── event_handler.py   # Processes inputs and routes multiplayer actions
│   ├── renderer.py        # Renders world, entities, UI, and multiplayer visuals
│   ├── state_manager.py   # Manages game states (e.g., playing, paused)
│   ├── world.py           # Procedural world generation and block management
│   ├── entities.py        # Entity definitions and management (ores, enemies)
│   ├── player.py          # Player logic, including ore pickup and animation
│   ├── ui.py              # HUD, menus, and multiplayer status display
│   ├── save_load.py       # Save/load progress for single and multiplayer
│   ├── utils.py           # Helpers: sound, effects, distance calculations
│   └── server.py          # WebSocket server for online multiplayer
├── data/
│   ├── ores.json          # Ore properties (value, color, mining time)
│   └── upgrades.json      # Upgrade definitions (cost, effects)
├── assets/
│   └── backgroundmusic.wav # Placeholder for audio (to be implemented)
└── index.html             # Browser entry point for Pyodide deployment

Detailed Module Breakdown

main.pyInitializes Pygame, logging, and game data. Runs the async game loop, with WebSocket integration for multiplayer clients.

game.pyCoordinates the game loop: updates state, processes inputs, renders frames, and syncs multiplayer data (e.g., player positions, mined blocks).

data.pyLoads ores.json (e.g., {"coal": {"value": 10, "color": "black"}}) and upgrades.json with Pyodide-compatible fallbacks.

settings.pyDefines constants:  

Screen: WIDTH=1280, HEIGHT=720, TILE_SIZE=32  
Game: FPS=60, DAY_DURATION=300.0, QUOTA_BASE=1000  
Player: MOVE_SPEED=200, JUMP_VELOCITY=-400  
Multiplayer: PLAYER_ID_PREFIX="player_"  
Key bindings: KEYS={"move_left": "LEFT", "drop_ore": "O"}


event_handler.pyHandles inputs and routes multiplayer actions (e.g., broadcasting mining events to other players).

renderer.pyDraws the world, entities, UI, and multiplayer elements (e.g., other players’ avatars).

state_manager.pyManages states: PlayingState now includes multiplayer synchronization logic.

world.pyGenerates chunks and tracks block states, with multiplayer-aware updates (e.g., syncing broken blocks).

entities.pyManages entities like OreItem (with animation) and Enemy, with multiplayer collision handling.

player.pyImplements player physics, inventory, and ore pickup logic. Fixed NameError by importing settings.

ui.pyDisplays HUD and menus, with multiplayer extensions (e.g., player list, ping).

save_load.pySaves single-player progress; multiplayer saves planned for server-side storage.

utils.pyProvides helpers: spawn_ore_item(), trigger_screen_shake(), and multiplayer utilities like serialize_position().

server.pyWebSocket server for online multiplayer (detailed below).



🛠️ Installation & Running
Local (CPython)

Clone the repository:  git clone https://github.com/yourusername/coal-llc.git
cd coal-llc


Install dependencies:  pip install pygame websockets


Run the game:  cd src
python main.py



Browser (Pyodide)

Serve the project directory:  python -m http.server 8000


Open http://localhost:8000/index.html in a browser.  
Ensure index.html includes Pyodide and points to main.py.


🎮 Controls

Player 1:  

Move: Left/Right Arrows  
Jump: Up Arrow  
Mine: Left Mouse Button  
Drop Ore: O  
Use Item: D (dynamite), H (health)  
Pause: P


Player 2 (Local Only):  

Move: A/D  
Jump: W  
Mine: Right Mouse Button  
Drop Ore: L  
Use Item: G (dynamite), J (health)


General:  

Upgrade Menu: U  
Inventory: I  
Minimap: M  
Debug Overlay: F1




🌐 Online Multiplayer Setup
The game is transitioning from local co-op to online multiplayer using WebSockets for real-time communication. Below is a step-by-step guide to set up and run the online multiplayer feature.
Prerequisites

Python 3.8+ with websockets (pip install websockets).  
A static HTTP server for browser deployment (e.g., python -m http.server).  
Basic understanding of networking concepts (e.g., client-server model, latency).

Step 1: Set Up the WebSocket Server

Create server.py in src/:
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
PLAYERS = {}
WORLD_STATE = {}

async def handler(websocket, path):
    player_id = f"player_{len(PLAYERS)}"
    PLAYERS[player_id] = websocket
    logging.info(f"{player_id} connected")

    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "update_position":
                PLAYERS[player_id] = {"x": data["x"], "y": data["y"]}
                await broadcast({"type": "player_update", "id": player_id, "x": data["x"], "y": data["y"]})
            elif action == "mine_block":
                block_x, block_y = data["block_x"], data["block_y"]
                WORLD_STATE[(block_x, block_y)] = "air"
                await broadcast({"type": "block_mined", "block_x": block_x, "block_y": block_y})
            elif action == "collect_ore":
                ore_id = data["ore_id"]
                await broadcast({"type": "ore_collected", "ore_id": ore_id, "player_id": player_id})

    except websockets.ConnectionClosed:
        del PLAYERS[player_id]
        logging.info(f"{player_id} disconnected")
        await broadcast({"type": "player_left", "id": player_id})

async def broadcast(message):
    for player_id, ws in PLAYERS.items():
        try:
            await ws.send(json.dumps(message))
        except websockets.ConnectionClosed:
            pass

async def main():
    server = await websockets.serve(handler, "localhost", 8765)
    logging.info("Server running on ws://localhost:8765")
    await server.wait_closed()

asyncio.run(main())


Run the server:  
cd src
python server.py



Step 2: Update Client Code

Modify main.py to connect to the server:
import asyncio
import pygame
import websockets
import json
from game import Game

async def websocket_client(game):
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        game.websocket = websocket
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                if data["type"] == "player_update":
                    game.update_remote_player(data["stipulate"], data["x"], data["y"])
                elif data["type"] == "block_mined":
                    game.world.set_block(data["block_x"], data["block_y"], "air")
                elif data["type"] == "ore_collected":
                    game.entities.remove_ore(data["ore_id"])
            except websockets.ConnectionClosed:
                break

async def main():
    pygame.init()
    game = Game()
    asyncio.ensure_future(websocket_client(game))
    await game.run()

if __name__ == "__main__":
    asyncio.run(main())


Update game.py to handle multiplayer:
class Game:
    def __init__(self):
        self.websocket = None
        self.remote_players = {}
        self.world = World()
        self.player = Player()
        self.entities = EntityManager()

    async def run(self):
        clock = pygame.time.Clock()
        while True:
            self.update()
            self.renderer.draw(self)
            pygame.display.flip()
            clock.tick(60)
            await asyncio.sleep(0)

    def update(self):
        self.player.update()
        if self.websocket:
            self.send_position()

    def send_position(self):
        asyncio.ensure_future(self.websocket.send(json.dumps({
            "action": "update_position",
            "x": self.player.pos_x,
            "y": self.player.pos_y
        })))

    def update_remote_player(self, player_id, x, y):
        self.remote_players[player_id] = (x, y)



Step 3: Run the Game

Start the server:  python server.py


Run clients:  
Local: python main.py (multiple instances).  
Browser: Serve files and open index.html in multiple tabs.



Multiplayer Features

Player Sync: Positions updated in real-time.  
World Sync: Mined blocks reflected across clients.  
Ore Collection: Prevents duplicate pickups.


🤝 Contributing

Fork and submit PRs to main.  
Follow module boundaries and add tests.  
Focus on multiplayer stability and latency handling.

📄 License
MIT © Coal LLC