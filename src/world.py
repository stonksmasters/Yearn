import random
import pygame
import logging
import math
from data import load_ores
from settings import *

# Configure logging (Pyodide-compatible)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.handlers = [console_handler]
logger.info("Initializing world.py")

class FallingRock:
    def __init__(self):
        """Initialize a falling rock with default properties."""
        self.x = 0
        self.y = 0
        self.velocity = 0
        self.active = False
        self.ore_type = "stone"

    def activate(self, x, y, velocity, ore_type):
        """Activate the falling rock at the specified position with given velocity and ore type."""
        self.x = x
        self.y = y
        self.velocity = velocity
        self.ore_type = ore_type
        self.active = True
        logger.debug(f"Activated FallingRock at ({x}, {y}) with ore {ore_type}")

    def update(self, dt, world, ores):
        """Update the falling rock's position and check for collisions, returning value if it lands."""
        if not self.active:
            return 0
        self.y += self.velocity * dt
        self.velocity += 0.5  # Gravity effect
        grid_x = int(self.x // TILE_SIZE)
        grid_y = int(self.y // TILE_SIZE)
        if grid_y >= MAX_DEPTH or (0 <= grid_x < NUM_COLS and grid_y < MAX_DEPTH and world.block_at(grid_x, grid_y) != "empty"):
            logger.debug(f"FallingRock at ({grid_x}, {grid_y}) collided")
            self.active = False
            return ores.get(self.ore_type, {"value": 0})["value"] if self.ore_type != "unstable" else 0
        return 0

class World:
    def __init__(self):
        """Initialize the world with chunks, falling rocks, and depth zones."""
        self.ores = load_ores()
        self.chunk_size = 16
        self.chunks = {}
        self.seed = random.randint(0, 1000000)
        self.falling_rocks = [FallingRock() for _ in range(5)]
        self.block_states = {}  # Track cracking stages (x, y): stage
        self.depth_zones = [
            {"name": "Surface", "depth": 0, "blocks": ["grass", "dirt"], "hazard_chance": 0.0, "color": (135, 206, 235), "cave_chance": 0.0, "cave_size": 0, "value_scale": 1.0},
            {"name": "Shallow", "depth": 1, "blocks": ["dirt", "stone", "coal", "copper", "tin"], "hazard_chance": 0.005, "color": (139, 69, 19), "cave_chance": 0.1, "cave_size": 3, "value_scale": 1.0},
            {"name": "Mid", "depth": 50, "blocks": ["stone", "coal", "iron", "silver"], "hazard_chance": 0.01, "color": (105, 105, 105), "cave_chance": 0.15, "cave_size": 5, "value_scale": 1.5},
            {"name": "Crystal Cavern", "depth": 300, "blocks": ["stone", "ruby", "sapphire", "emerald"], "hazard_chance": 0.015, "color": (72, 61, 139), "cave_chance": 0.2, "cave_size": 7, "value_scale": 2.0},
            {"name": "Deep", "depth": 500, "blocks": ["stone", "iron", "silver", "gold", "sapphire", "ruby", "emerald", "amethyst", "platinum", "mithril"], "hazard_chance": 0.02, "color": (47, 79, 79), "cave_chance": 0.1, "cave_size": 4, "value_scale": 3.0},
            {"name": "Abyss", "depth": 1000, "blocks": ["stone", "gold", "sapphire", "ruby", "emerald", "amethyst", "platinum", "mithril", "diamond"], "hazard_chance": 0.03, "color": (25, 25, 112), "cave_chance": 0.15, "cave_size": 6, "value_scale": 5.0}
        ]
        self.unstable_blocks = {}
        self.block_cols = {}  # Initialize block_cols for saving/loading
        self.ensure_depth(1)
        logger.info("World initialized")

    def load_from_block_cols(self, block_cols):
        """Load world state from block_cols dictionary."""
        self.chunks = {}  # Clear existing chunks
        self.block_cols = block_cols
        for (x, y), block_type in block_cols.items():
            if not (0 <= x < NUM_COLS and 0 <= y < MAX_DEPTH):
                continue
            chunk_x, chunk_y = x // self.chunk_size, y // self.chunk_size
            local_x, local_y = x % self.chunk_size, y % self.chunk_size
            chunk_key = (chunk_x, chunk_y)
            if chunk_key not in self.chunks:
                self.chunks[chunk_key] = [[None for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]
            self.chunks[chunk_key][local_x][local_y] = block_type
        logger.info("Loaded world from block_cols")

    def block_at(self, x, y):
        """Get the block type at the specified coordinates."""
        if not (0 <= x < NUM_COLS and 0 <= y < MAX_DEPTH):
            return None
        chunk_x, chunk_y = x // self.chunk_size, y // self.chunk_size
        local_x, local_y = x % self.chunk_size, y % self.chunk_size
        chunk = self.get_chunk(chunk_x, chunk_y)
        return chunk[local_x][local_y]

    def set_block(self, x, y, block_type):
        """Set the block type at the specified coordinates and update block_cols."""
        if not (0 <= x < NUM_COLS and 0 <= y < MAX_DEPTH):
            return
        chunk_x, chunk_y = x // self.chunk_size, y // self.chunk_size
        local_x, local_y = x % self.chunk_size, y % self.chunk_size
        chunk = self.get_chunk(chunk_x, chunk_y)
        chunk[local_x][local_y] = block_type
        self.block_cols[(x, y)] = block_type
        if block_type == "empty":
            if (x, y) in self.block_states:
                del self.block_states[(x, y)]  # Clean up block state
            self.check_stability(x, y)
        logger.debug(f"Set block at ({x}, {y}): {block_type}")

    def set_block_state(self, x, y, stage):
        """Set the mining progress stage for a block."""
        if 0 <= x < NUM_COLS and 0 <= y < MAX_DEPTH:
            self.block_states[(x, y)] = stage
            logger.debug(f"Set block state at ({x}, {y}) to stage {stage}")

    def get_block_state(self, x, y):
        """Get the mining progress stage for a block."""
        return self.block_states.get((x, y), 0)

    def get_surrounding_blocks(self, rect):
        """Get a list of surrounding non-empty block rectangles for collision detection."""
        blocks = []
        left = int(rect.left // TILE_SIZE) - 1
        right = int(rect.right // TILE_SIZE) + 2
        top = int(rect.top // TILE_SIZE) - 1
        bottom = int(rect.bottom // TILE_SIZE) + 2
        for ty in range(max(0, top), min(bottom, MAX_DEPTH)):
            for tx in range(max(0, left), min(right, NUM_COLS)):
                block_type = self.block_at(tx, ty)
                if block_type and block_type != "empty":
                    blocks.append(pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        return blocks

    def get_chunk(self, chunk_x, chunk_y):
        """Get or generate a chunk at the specified chunk coordinates."""
        chunk_key = (chunk_x, chunk_y)
        if chunk_key not in self.chunks:
            self.generate_chunk(chunk_x, chunk_y)
        return self.chunks[chunk_key]

    def generate_chunk(self, chunk_x, chunk_y):
        """Generate a chunk with blocks, caves, and hazards based on depth zone."""
        chunk = [[None for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]
        start_y = chunk_y * self.chunk_size
        end_y = min((chunk_y + 1) * self.chunk_size, MAX_DEPTH)
        zone = self.get_depth_zone(start_y)

        # Initialize chunk with blocks
        for y in range(max(1, start_y), end_y):
            for x in range(self.chunk_size):
                world_x = chunk_x * self.chunk_size + x
                world_y = y
                if chunk_y == 0 and y == 0:
                    chunk[x][0] = "grass"
                else:
                    chunk[x][y - start_y] = self.generate_ore_vein(world_x, world_y, zone)
                self.block_cols[(world_x, world_y)] = chunk[x][y - start_y]

        # Generate caves if applicable
        if start_y > 10 and random.random() < zone["cave_chance"]:
            self.generate_cave(chunk, chunk_x, chunk_y, zone)

        # Add unstable blocks
        for y in range(max(1, start_y), end_y):
            for x in range(self.chunk_size):
                world_y = y
                hazard_chance = zone["hazard_chance"] * (1 + world_y / 10000)
                if random.random() < hazard_chance and world_y > 50:
                    chunk[x][y - start_y] = "unstable"
                    self.block_cols[(chunk_x * self.chunk_size + x, world_y)] = "unstable"

        self.chunks[(chunk_x, chunk_y)] = chunk
        logger.debug(f"Generated chunk ({chunk_x}, {chunk_y})")

    def generate_cave(self, chunk, chunk_x, chunk_y, zone):
        """Generate a cave in the chunk using cellular automaton, preserving rare ores."""
        temp_grid = [[1 for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]
        start_y = chunk_y * self.chunk_size
        cave_size = zone["cave_size"]
        num_seeds = random.randint(1, 3)
        for _ in range(num_seeds):
            seed_x = random.randint(2, self.chunk_size - 3)
            seed_y = random.randint(2, self.chunk_size - 3)
            temp_grid[seed_x][seed_y] = 0

        # Cellular automaton for cave shape
        for _ in range(4):
            new_grid = [[1 for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]
            for y in range(self.chunk_size):
                for x in range(self.chunk_size):
                    neighbors = sum(
                        1 for dx in range(-1, 2) for dy in range(-1, 2)
                        if 0 <= x + dx < self.chunk_size and 0 <= y + dy < self.chunk_size and temp_grid[x + dx][y + dy] == 1
                    )
                    if temp_grid[x][y] == 1 and neighbors < 4:
                        new_grid[x][y] = 0
                    elif temp_grid[x][y] == 0 and neighbors >= 5:
                        new_grid[x][y] = 1
                    else:
                        new_grid[x][y] = temp_grid[x][y]
            temp_grid = new_grid

        # Apply cave, preserving rare ores
        rare_ores = ["ruby", "sapphire", "emerald", "mithril", "diamond"]
        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                if temp_grid[x][y] == 0 and chunk[x][y] not in rare_ores:
                    chunk[x][y] = "empty"
                    self.block_cols[(chunk_x * self.chunk_size + x, start_y + y)] = "empty"
                elif temp_grid[x][y] == 1 and chunk[x][y] not in rare_ores:
                    neighbors = sum(
                        1 for dx in range(-1, 2) for dy in range(-1, 2)
                        if 0 <= x + dx < self.chunk_size and 0 <= y + dy < self.chunk_size and temp_grid[x + dx][y + dy] == 0
                    )
                    if neighbors > 0 and random.random() < 0.2:
                        chunk[x][y] = "cave_wall" if zone["name"] != "Crystal Cavern" else "crystal_wall"
                        self.block_cols[(chunk_x * self.chunk_size + x, start_y + y)] = chunk[x][y]

        # Add treasure
        if random.random() < 0.1 and zone["name"] in ["Crystal Cavern", "Deep", "Abyss"]:
            treasure_x = random.randint(2, self.chunk_size - 3)
            treasure_y = random.randint(2, self.chunk_size - 3)
            if temp_grid[treasure_x][treasure_y] == 0:
                chunk[treasure_x][treasure_y] = random.choice(rare_ores)
                self.block_cols[(chunk_x * self.chunk_size + treasure_x, start_y + treasure_y)] = chunk[treasure_x][treasure_y]
        logger.debug(f"Generated cave in chunk ({chunk_x}, {chunk_y})")

    def get_depth_zone(self, y):
        """Get the depth zone for a given y-coordinate."""
        current_zone = self.depth_zones[0]
        for zone in self.depth_zones:
            if y >= zone["depth"]:
                current_zone = zone
            else:
                break
        return current_zone

    def get_biome_color(self, depth):
        """Get the biome color for a given depth."""
        zone = self.get_depth_zone(depth)
        return zone["color"]

    def perlin_noise(self, x, y, scale=0.1, threshold=0.5):
        """Generate Perlin noise for ore vein generation."""
        random.seed(self.seed + x * 1000 + y)
        noise = (math.sin(x * scale) + math.sin(y * scale)) / 2
        return noise + 0.5

    def generate_ore_vein(self, x, y, zone):
        """Generate an ore type for a position based on depth zone."""
        total_weight = sum(self.ores.get(ore, {"weight": 0})["weight"] for ore in zone["blocks"])
        noise = self.perlin_noise(x, y, scale=0.05)
        r = (noise + random.random()) / 2 * total_weight
        current_weight = 0
        for ore_name in zone["blocks"]:
            if y * TILE_SIZE >= self.ores.get(ore_name, {"min_depth": 0})["min_depth"]:
                current_weight += self.ores.get(ore_name, {"weight": 0})["weight"]
                if r <= current_weight:
                    return ore_name
        return "stone"

    def ensure_depth(self, depth):
        """Ensure the world is generated up to the specified depth."""
        target = min(int(depth), MAX_DEPTH - 1)
        target_chunk_y = target // self.chunk_size
        for chunk_x in range(NUM_COLS // self.chunk_size):
            for chunk_y in range(target_chunk_y + 1):
                self.get_chunk(chunk_x, chunk_y)
        logger.debug(f"Ensured world depth to {target}")

    def check_stability(self, x, y):
        """Check stability of adjacent unstable blocks."""
        for dx, dy in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < NUM_COLS and 0 <= ny < MAX_DEPTH:
                block = self.block_at(nx, ny)
                if block == "unstable":
                    adjacent_empty = sum(1 for ddx, ddy in [(0, 1), (1, 0), (-1, 0), (0, -1)] if 0 <= nx + ddx < NUM_COLS and 0 <= ny + ddy < MAX_DEPTH and self.block_at(nx + ddx, ny + ddy) == "empty")
                    if adjacent_empty >= 2:
                        self.unstable_blocks[(nx, ny)] = 0.0

    def get_hazard_blocks(self):
        """Get a list of unstable block positions."""
        return list(self.unstable_blocks.keys())

    def spawn_falling_rock(self, x, y, velocity, ore_type):
        """Spawn a falling rock at the specified position."""
        for rock in self.falling_rocks:
            if not rock.active:
                rock.activate(x, y, velocity, ore_type)
                return True
        return False

    def update(self, dt):
        """Update falling rocks and unstable blocks, returning total value collected."""
        total_value = 0
        for rock in self.falling_rocks:
            value = rock.update(dt, self, self.ores)
            total_value += value
        to_remove = []
        for (x, y), timer in self.unstable_blocks.items():
            timer += dt
            if timer >= 2.0:
                block = self.block_at(x, y)
                if self.spawn_falling_rock(x * TILE_SIZE, y * TILE_SIZE, random.randint(200, 400), block):
                    self.set_block(x, y, "empty")
                    to_remove.append((x, y))
            else:
                self.unstable_blocks[(x, y)] = timer
        for pos in to_remove:
            del self.unstable_blocks[pos]
        return total_value

    def get_surface_y(self, x):
        """Get the y-coordinate of the surface (grass) at the specified x."""
        for y in range(MAX_DEPTH):
            block = self.block_at(x, y)
            if block == "grass":
                return y
        return 0