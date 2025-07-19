import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
PLAYERS = {}  # {player_id: websocket}
WORLD_STATE = {}  # {(x, y): block_type}
ENTITIES = {}  # {entity_id: {type, x, y, ...}}
entity_id_counter = 0

async def handler(websocket, path):
    player_id = f"player_{len(PLAYERS)}"
    PLAYERS[player_id] = websocket
    await websocket.send(json.dumps({"type": "player_joined", "id": player_id}))
    logging.info(f"{player_id} connected")

    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "update_position":
                x, y = data["x"], data["y"]
                await broadcast({"type": "player_update", "id": player_id, "x": x, "y": y})
            elif action == "mine_block":
                block_x, block_y = data["block_x"], data["block_y"]
                if is_valid_mining(player_id, block_x, block_y):
                    WORLD_STATE[(block_x, block_y)] = "empty"
                    if random.random() < 0.1:  # Chance to spawn ore
                        spawn_ore(block_x, block_y, "coal")
                    await broadcast({"type": "block_mined", "block_x": block_x, "block_y": block_y})
            elif action == "collect_ore":
                ore_id = data["ore_id"]
                if ore_id in ENTITIES and is_valid_collection(player_id, ore_id):
                    del ENTITIES[ore_id]
                    await broadcast({"type": "ore_collected", "ore_id": ore_id, "player_id": player_id})

    except websockets.ConnectionClosed:
        del PLAYERS[player_id]
        await broadcast({"type": "player_left", "id": player_id})
        logging.info(f"{player_id} disconnected")

async def broadcast(message):
    for ws in PLAYERS.values():
        await ws.send(json.dumps(message))

def spawn_ore(block_x, block_y, ore_type):
    global entity_id_counter
    entity_id = f"entity_{entity_id_counter}"
    entity_id_counter += 1
    entity_data = {"type": "ore", "x": block_x * TILE_SIZE, "y": block_y * TILE_SIZE, "ore_type": ore_type}
    ENTITIES[entity_id] = entity_data
    asyncio.create_task(broadcast({"type": "spawn_entity", "entity_id": entity_id, "entity_data": entity_data}))

def is_valid_mining(player_id, block_x, block_y):
    # Placeholder: Validate mining (e.g., player proximity, block exists)
    return True

def is_valid_collection(player_id, ore_id):
    # Placeholder: Validate ore collection (e.g., player proximity)
    return ore_id in ENTITIES

async def main():
    server = await websockets.serve(handler, "localhost", 8765)
    logging.info("Server running on ws://localhost:8765")
    await server.wait_closed()

asyncio.run(main())