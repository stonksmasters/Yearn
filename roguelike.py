import pygame
import random
import time

# Initialize Pygame
pygame.init()
width, height = 384, 384  # 24x24 tiles at 16x16 pixels
tile_size = 16
grid_width, grid_height = 24, 24
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Coal LLC Roguelike")
font = pygame.font.SysFont("consolas", 12)  # Smaller retro font

# 8-bit NES-like colors
DARK_GRAY = (40, 40, 40)  # Background
LIGHT_GRAY = (90, 90, 90)  # Stone
DIRT_BROWN = (60, 30, 0)  # Dirt
COAL_BLACK = (20, 20, 20)  # Coal
IRON_GRAY = (120, 120, 120)  # Iron
SILVER = (180, 180, 180)  # Silver
GOLD_YELLOW = (140, 90, 0)  # Gold
PLAYER_GRAY = (70, 70, 70)  # Player
WHITE = (160, 160, 160)  # Text/accents

# Ore types with mining times (seconds) and values
ores = {
    "dirt": {"color": DIRT_BROWN, "time": 0.5, "value": 1},
    "coal": {"color": COAL_BLACK, "time": 1.0, "value": 5},
    "stone": {"color": LIGHT_GRAY, "time": 1.5, "value": 2},
    "iron": {"color": IRON_GRAY, "time": 2.0, "value": 10},
    "silver": {"color": SILVER, "time": 3.0, "value": 20},
    "gold": {"color": GOLD_YELLOW, "time": 4.0, "value": 50}
}

# Game objects
player = {"x": 11, "y": 11, "hp": 10, "coal": 0, "pickaxe": 1, "gun": 0}  # Gun 0 = none
grid = [[random.choice(list(ores.keys())) for _ in range(grid_width)] for _ in range(grid_height)]
grid[player["y"]][player["x"]] = None  # Start position is empty
day = 1
quota = 20
time_limit = 30  # Seconds per day
start_time = time.time()
mining = None  # Current block being mined
mining_start = 0
dropped_ores = []  # List of dropped ore items

# Upgrades (cost in coal)
upgrades = {
    "pickaxe": [{"cost": 10, "level": 2}, {"cost": 20, "level": 3}, {"cost": 30, "level": 4}],
    "gun": [
        {"cost": 15, "name": "Iron Pistol", "speed": 0.5},
        {"cost": 25, "name": "Iron Shotgun", "speed": 0.75},
        {"cost": 40, "name": "Silver Pistol", "speed": 1.0}
    ]
}

# Background texture (8-bit dirt pattern)
background = pygame.Surface((width, height))
background.fill(DARK_GRAY)
for y in range(0, height, 4):
    for x in range(0, width, 4):
        if random.random() < 0.2:
            pygame.draw.rect(background, DIRT_BROWN, (x, y, 2, 2))

def generate_map():
    grid = [[random.choice(list(ores.keys())) for _ in range(grid_width)] for _ in range(grid_height)]
    grid[player["y"]][player["x"]] = None  # Ensure player start is empty
    return grid

def draw_grid():
    screen.blit(background, (0, 0))
    for y in range(grid_height):
        for x in range(grid_width):
            rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
            ore_type = grid[y][x]
            if ore_type:
                # Draw block with 8-bit texture (crosshatch)
                pygame.draw.rect(screen, ores[ore_type]["color"], (x * tile_size + 2, y * tile_size + 2, tile_size - 4, tile_size - 4))
                pygame.draw.line(screen, WHITE, (x * tile_size + 4, y * tile_size + 4), (x * tile_size + tile_size - 4, y * tile_size + tile_size - 4), 1)
                pygame.draw.line(screen, WHITE, (x * tile_size + 4, y * tile_size + tile_size - 4), (x * tile_size + tile_size - 4, y * tile_size + 4), 1)
            # Draw dropped ores
            for drop in dropped_ores:
                if drop["x"] == x and drop["y"] == y:
                    pygame.draw.rect(screen, ores[drop["type"]]["color"], (x * tile_size + 5, y * tile_size + 5, tile_size - 10, tile_size - 10))
            # Draw player
            if x == player["x"] and y == player["y"]:
                pygame.draw.rect(screen, PLAYER_GRAY, (x * tile_size + 3, y * tile_size + 3, tile_size - 6, tile_size - 6))
                pygame.draw.rect(screen, WHITE, (x * tile_size + 3, y * tile_size + 3, tile_size - 6, tile_size - 6), 1)
            # Draw mining progress bar
            if mining and mining["x"] == x and mining["y"] == y:
                progress = (time.time() - mining_start) / (ores[ore_type]["time"] / (player["pickaxe"] + player["gun"]))
                pygame.draw.rect(screen, WHITE, (x * tile_size + 2, y * tile_size + tile_size - 4, (tile_size - 4) * progress, 2))
    # Draw stats
    gun_name = "None" if player["gun"] == 0 else upgrades["gun"][player["gun"] - 1]["name"]
    stats = font.render(f"HP: {player['hp']} Coal: {player['coal']} Pick: {player['pickaxe']} Gun: {gun_name} Day: {day} Quota: {quota}", True, WHITE)
    screen.blit(stats, (10, height - 20))
    time_left = max(0, time_limit - (time.time() - start_time))
    timer = font.render(f"Time: {int(time_left)}s", True, WHITE)
    screen.blit(timer, (width - 60, height - 20))
    if time_left <= 0 or player["hp"] <= 0:
        end_text = font.render("Game Over! Failed Quota" if time_left <= 0 else "Game Over! Died", True, WHITE)
        screen.blit(end_text, (width // 2 - 60, height // 2))
    pygame.display.flip()

def move_player(dx, dy):
    new_x = player["x"] + dx
    new_y = player["y"] + dy
    if 0 <= new_x < grid_width and 0 <= new_y < grid_height and grid[new_y][new_x] is None:
        player["x"] = new_x
        player["y"] = new_y

def mine_block(x, y):
    global mining, mining_start
    if not mining and grid[y][x] is not None:
        mining = {"x": x, "y": y}
        mining_start = time.time()

def check_mining():
    global mining, mining_start
    if mining:
        ore_type = grid[mining["y"]][mining["x"]]
        mining_time = ores[ore_type]["time"] / (player["pickaxe"] + player["gun"])
        if time.time() - mining_start >= mining_time:
            player["hp"] -= 1  # Mining costs HP
            dropped_ores.append({"x": mining["x"], "y": mining["y"], "type": ore_type})
            grid[mining["y"]][mining["x"]] = None
            mining = None

def collect_ores():
    global dropped_ores
    for drop in dropped_ores[:]:
        if drop["x"] == player["x"] and drop["y"] == player["y"]:
            player["coal"] += ores[drop["type"]]["value"]
            dropped_ores.remove(drop)

def upgrade_menu():
    global player, day, quota, start_time
    if player["coal"] >= quota:
        player["coal"] -= quota
        day += 1
        quota += 10
        start_time = time.time()
        grid[:] = generate_map()
        dropped_ores.clear()
        # Offer upgrades
        available_upgrades = []
        if player["pickaxe"] < len(upgrades["pickaxe"]) + 1:
            next_pickaxe = upgrades["pickaxe"][player["pickaxe"] - 1]
            if player["coal"] >= next_pickaxe["cost"]:
                available_upgrades.append(("pickaxe", next_pickaxe))
        if player["gun"] < len(upgrades["gun"]):
            next_gun = upgrades["gun"][player["gun"]]
            if player["coal"] >= next_gun["cost"]:
                available_upgrades.append(("gun", next_gun))
        if available_upgrades:
            for i, (upgrade_type, upgrade) in enumerate(available_upgrades):
                print(f"{i+1}. {upgrade_type.capitalize()} ({upgrade['cost']} coal): {'Level ' + str(upgrade['level']) if upgrade_type == 'pickaxe' else upgrade['name']}")
            choice = input("Choose upgrade (number) or press Enter to continue: ")
            if choice.isdigit() and 1 <= int(choice) <= len(available_upgrades):
                upgrade_type, upgrade = available_upgrades[int(choice) - 1]
                player["coal"] -= upgrade["cost"]
                if upgrade_type == "pickaxe":
                    player["pickaxe"] = upgrade["level"]
                else:
                    player["gun"] = upgrades["gun"].index(upgrade) + 1
        return True
    return False

def main():
    global start_time, mining
    clock = pygame.time.Clock()
    running = True
    while running and player["hp"] > 0:
        time_left = time_limit - (time.time() - start_time)
        if time_left <= 0:
            if not upgrade_menu():
                break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_w:
                    move_player(0, -1)
                    mining = None
                elif event.key == pygame.K_s:
                    move_player(0, 1)
                    mining = None
                elif event.key == pygame.K_a:
                    move_player(-1, 0)
                    mining = None
                elif event.key == pygame.K_d:
                    move_player(1, 0)
                    mining = None
                elif event.key == pygame.K_SPACE:
                    # Mine adjacent blocks
                    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        new_x, new_y = player["x"] + dx, player["y"] + dy
                        if 0 <= new_x < grid_width and 0 <= new_y < grid_height:
                            mine_block(new_x, new_y)
                elif event.key == pygame.K_q:
                    running = False
        check_mining()
        collect_ores()
        draw_grid()
        clock.tick(30)
    pygame.quit()
    print("Game Over! Final Coal:", player["coal"], "Days Survived:", day - 1)

if __name__ == "__main__":
    main()