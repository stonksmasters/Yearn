Yearn – Ultimate Miner
Yearn – Ultimate Miner is a 2D mining roguelike game developed using Pygame, designed to run seamlessly both locally with CPython and in web browsers via Pyodide. Players dive into procedurally generated underground layers, mining ores, managing resources, upgrading equipment, and surviving daily quotas amidst environmental hazards and enemies. The game supports singleplayer, local co-op, and is being extended to include online multiplayer with a lobby system for collaborative play. This README provides an in-depth guide to the game’s features, project structure, installation, controls, and setup for online multiplayer using WebSockets.
🚀 Features
Procedural World Generation

Infinite vertical layers with depth-based ore distribution (e.g., coal at shallow depths, diamonds deeper).
Environmental hazards like cave-ins and gas pockets.

Mining Mechanics

Click-to-mine blocks with upgradeable pickaxes (e.g., steel, diamond, quantum).
Area-of-effect (AOE) mining with dynamite or blasters.
Special tools like quantum pickaxes for instant block destruction.

Resource Management

Earn cash by dropping off ores at the surface.
Meet increasing daily quotas (e.g., Day 1: $1000, Day 2: $1200).
Unlock milestone rewards for hitting depth or cash goals.

Upgrade System

Shop items: dynamite, teleporters, ore magnets, health packs.
Pickaxe upgrades: speed, power, range.
Persistent upgrades saved across sessions.

Entity System

Particles: Visual effects for mining, explosions, and treasure sparkles.
Falling Rocks: Dynamic hazards that damage players.
Enemies: Bats, goblins, abyss wraiths with unique drops (e.g., bat wings, goblin teeth).
OreItems: Collectible resources with immediate removal on pickup.

Ore Pickup Range

Automatically collect ores within a configurable radius (default: 50 pixels).
Upgrades increase range (e.g., Ore Magnet: +25 pixels per level).

Animated Ore Collection

Ores within pickup range animate smoothly toward the player with lerp-based movement (speed: 200 pixels/second).
Added to inventory once they reach the player’s position.

Ore Drop-Off

Press 'O' at the surface to cash in ores.
On-screen notifications display earnings (e.g., “+500 cash”).

Persistent Save/Load

Save progress to local files (CPython) or browser storage (Pyodide).
Multiple save slots for flexibility.

User Interface

HUD: Cash, quota progress, day timer, depth meter.
Menus: Start, pause, upgrade shop, inventory, post-day upgrade selector.
Debug Overlays: FPS, entity count, player coords.
Minimap: Shows explored areas and player position.

Game Modes

Singleplayer: Play alone with the full mining experience, including procedural world generation, upgrades, and daily quotas.
Local Co-op: Two players on the same device with split controls, supporting keyboard and PlayStation controllers (planned).
Online Co-op: Collaborate with friends via WebSockets, with a lobby system for joining games (in progress).

Multiplayer

Local Co-op: Two players on the same screen with split controls.
Online Multiplayer: Real-time collaboration via WebSockets with a lobby system.
Create a lobby with a 4-character code (random mix of digits and letters, e.g., "A7B4").
Join a friend’s lobby by entering their code in the UI.


Player synchronization: Real-time position updates and shared world state.
World synchronization: Mined blocks and ore collection reflected across all clients.

Recent Updates

Fixed NameError in player.py by adding missing import.
Enhanced logging for ore collection and animation debugging.
Improved Pyodide compatibility with async event handling.
Added WebSocket server for online multiplayer (server.py).
Updated renderer.py to support rendering remote players in online mode.

📁 Project Structure
The project follows a modular design to separate concerns, making it easy to maintain and extend, especially for adding online multiplayer and lobby features.
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
│   └── backgroundmusic.wav # Placeholder for audio
└── index.html             # Browser entry point for Pyodide deployment

Detailed Module Breakdown

main.py: Initializes Pygame, logging, and game data. Runs the async game loop with WebSocket integration for multiplayer clients.
game.py: Coordinates the game loop: updates state, processes inputs, renders frames, and syncs multiplayer data (e.g., player positions, mined blocks).
data.py: Loads ores.json (e.g., {"coal": {"value": 10, "color": "black"}}) and upgrades.json with Pyodide-compatible fallbacks.
settings.py: Defines constants:
Screen: WIDTH=1280, HEIGHT=720, TILE_SIZE=32
Game: FPS=60, DAY_DURATION=300.0, QUOTA_BASE=1000
Player: MOVE_SPEED=200, JUMP_VELOCITY=-400
Multiplayer: PLAYER_ID_PREFIX="player_"
Key bindings: KEYS={"move_left": "LEFT", "drop_ore": "O"}


event_handler.py: Handles inputs and routes multiplayer actions (e.g., broadcasting mining events).
renderer.py: Draws the world, entities, UI, and multiplayer elements (e.g., local and remote players).
state_manager.py: Manages states; PlayingState includes multiplayer synchronization logic.
world.py: Generates chunks and tracks block states, with multiplayer-aware updates (e.g., syncing broken blocks).
entities.py: Manages entities like OreItem (with animation) and Enemy, with multiplayer collision handling.
player.py: Implements player physics, inventory, and ore pickup logic. Fixed NameError by importing settings.
ui.py: Displays HUD and menus, with multiplayer extensions (e.g., player list, ping, lobby interface planned).
save_load.py: Saves singleplayer progress; multiplayer saves planned for server-side storage.
utils.py: Provides helpers: spawn_ore_item(), trigger_screen_shake(), and multiplayer utilities like serialize_position().
server.py: WebSocket server for online multiplayer with lobby system (in progress).

🛠️ Installation & Running
Local (CPython)

Clone the repository:git clone https://github.com/yourusername/coal-llc.git
cd coal-llc


Install dependencies:pip install pygame websockets


Run the game:cd src
python main.py



Browser (Pyodide)

Clone the repository (if not already done):git clone https://github.com/yourusername/coal-llc.git
cd coal-llc


Serve the project directory:python -m http.server 8000


Open http://localhost:8000/index.html in a browser.
Ensure index.html includes Pyodide and points to main.py.
Friends can access the game by visiting the same URL (if hosted publicly) or running their own local server for playtesting.



Notes

For browser playtesting, ensure the server (server.py) is running to support online multiplayer.
The game is designed to be accessible via a web browser, allowing friends to playtest without installing Python or dependencies locally.

🎮 Controls
Singleplayer & Player 1 (Local Co-op)

Move: Left/Right Arrows
Jump: Up Arrow
Mine: Left Mouse Button
Drop Ore: O
Use Item: D (dynamite), H (health)
Pause: P
Upgrade Menu: U
Inventory: I
Minimap: M
Debug Overlay: F1

Player 2 (Local Co-op)

Move: A/D
Jump: W
Mine: Right Mouse Button
Drop Ore: L
Use Item: G (dynamite), J (health)

PlayStation Controller (Local Co-op, Planned)

Move: Left Analog Stick
Jump: X Button
Mine: Square Button
Drop Ore: Circle Button
Use Item: Triangle (dynamite), R1 (health)
Pause: Options Button
Upgrade Menu: L1
Inventory: R2

Online Co-op

Controls mirror singleplayer/Player 1, with additional UI for lobby creation/joining.

🌐 Online Multiplayer Setup
The game supports online multiplayer using WebSockets for real-time communication, with a planned lobby system to facilitate joining friends’ games.
Prerequisites

Python 3.8+ with websockets (pip install websockets).
A static HTTP server for browser deployment (python -m http.server).
Basic understanding of networking concepts (e.g., client-server model, latency).

Step 1: Set Up the WebSocket Server

Ensure server.py is in src/ (see below for updated server code with lobby support).
Run the server:cd src
python server.py



Updated server.py (with Lobby System Placeholder)
import asyncio
import websockets
import json
import logging
import random
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOBBIES = {}  # {lobby_code: {players: {}, world_state: {}}}
PLAYERS = {}  # {player_id: {websocket, lobby_code, x, y, ...}}

def generate_lobby_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

async def handler(websocket, path=None):
    player_id = f"player_{len(PLAYERS)}"
    PLAYERS[player_id] = {"websocket": websocket, "lobby_code": None, "x": 1600, "y": 0}
    logger.info(f"{player_id} connected")

    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")
            if action == "create_lobby":
                lobby_code = generate_lobby_code()
                while lobby_code in LOBBIES:
                    lobby_code = generate_lobby_code()
                LOBBIES[lobby_code] = {"players": {player_id: PLAYERS[player_id]}, "world_state": {}}
                PLAYERS[player_id]["lobby_code"] = lobby_code
                await websocket.send(json.dumps({"type": "lobby_created", "lobby_code": lobby_code}))
            elif action == "join_lobby":
                lobby_code = data.get("lobby_code")
                if lobby_code in LOBBIES:
                    LOBBIES[lobby_code]["players"][player_id] = PLAYERS[player_id]
                    PLAYERS[player_id]["lobby_code"] = lobby_code
                    await websocket.send(json.dumps({"type": "lobby_joined", "lobby_code": lobby_code}))
                    await broadcast_to_lobby(lobby_code, {"type": "player_joined", "id": player_id, "x": 1600, "y": 0})
                else:
                    await websocket.send(json.dumps({"type": "error", "message": "Invalid lobby code"}))
            elif action == "update_position":
                lobby_code = PLAYERS[player_id]["lobby_code"]
                if lobby_code and data.get("x") is not None and data.get("y") is not None:
                    PLAYERS[player_id]["x"] = data["x"]
                    PLAYERS[player_id]["y"] = data["y"]
                    await broadcast_to_lobby(lobby_code, {"type": "player_update", "id": player_id, "x": data["x"], "y": data["y"]})
            elif action == "mine_block":
                lobby_code = PLAYERS[player_id]["lobby_code"]
                if lobby_code:
                    block_x, block_y = data["block_x"], data["block_y"]
                    LOBBIES[lobby_code]["world_state"][(block_x, block_y)] = "air"
                    await broadcast_to_lobby(lobby_code, {"type": "block_mined", "block_x": block_x, "block_y": block_y})
    except websockets.ConnectionClosed:
        lobby_code = PLAYERS[player_id]["lobby_code"]
        if lobby_code and player_id in LOBBIES[lobby_code]["players"]:
            del LOBBIES[lobby_code]["players"][player_id]
            await broadcast_to_lobby(lobby_code, {"type": "player_left", "id": player_id})
        del PLAYERS[player_id]
        logger.info(f"{player_id} disconnected")

async def broadcast_to_lobby(lobby_code, message):
    if lobby_code in LOBBIES:
        for player_id, player in LOBBIES[lobby_code]["players"].items():
            try:
                await player["websocket"].send(json.dumps(message))
            except websockets.ConnectionClosed:
                pass

async def main():
    server = await websockets.serve(handler, "localhost", 8765)
    logger.info("Server running on ws://localhost:8765")
    await server.wait_closed()

asyncio.run(main())

Step 2: Update Client Code

Update main.py to include lobby selection UI and WebSocket handling (planned for ui.py integration).
Add lobby creation/joining to game.py:class Game:
    def __init__(self):
        self.websocket = None
        self.lobby_code = None
        self.mode = "singleplayer"  # Options: singleplayer, local_coop, online_coop
        self.remote_players = {}

    def create_lobby(self):
        if self.websocket:
            asyncio.ensure_future(self.websocket.send(json.dumps({"action": "create_lobby"})))

    def join_lobby(self, lobby_code):
        if self.websocket:
            asyncio.ensure_future(self.websocket.send(json.dumps({"action": "join_lobby", "lobby_code": lobby_code})))



Step 3: Run the Game

Start the server:python server.py


Run clients:
Local: python main.py (select singleplayer, local co-op, or online co-op).
Browser: Serve files and open index.html in multiple tabs, selecting game mode and lobby options.



Multiplayer Features

Lobby System: Create or join lobbies with a 4-character code (e.g., "A7B4").
Player Sync: Real-time position updates within the same lobby.
World Sync: Mined blocks and ore collection synchronized across clients in the same lobby.
Game Modes: Choose singleplayer, local co-op, or online co-op from the start menu.

📅 Roadmap
The following features are planned to enhance the game, particularly for multiplayer and accessibility:

Lobby System Implementation:
UI for creating lobbies (generates a 4-character code, e.g., "A7B4").
UI for entering a lobby code to join friends’ games.
Server-side lobby management to group players and isolate world states per lobby.


PlayStation Controller Support:
Add support for PlayStation controllers in local co-op mode using Pygame’s joystick API.
Map controls to analog sticks and buttons (e.g., Left Stick for movement, X for jump).


Game Mode Selection:
Implement a start menu option to choose between singleplayer, local co-op, and online co-op.
Ensure singleplayer uses the existing game loop without WebSocket connections.
Local co-op supports two players on one device (keyboard or controllers).
Online co-op requires lobby creation or joining via WebSocket.


Multiplayer Enhancements:
Synchronize enemies and hazards across clients in the same lobby.
Implement server-side item usage (e.g., dynamite, health packs) for consistent effects.
Add client-side prediction for smoother player movement.


Browser Optimization:
Optimize Pyodide performance for smoother browser gameplay.
Ensure cross-browser compatibility (Chrome, Firefox, Edge).


Public Hosting:
Provide instructions for hosting the game on a public server for friends to join via a URL.
Implement NAT traversal or relay servers for reliable online play.



🤝 Contributing

Fork and submit PRs to the main branch.
Follow module boundaries and add tests for new features.
Focus on multiplayer stability, latency handling, and lobby system implementation.
Test browser compatibility with Pyodide for playtesting.

📄 License
MIT © Coal LLC