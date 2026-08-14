import pygame
pygame.init()
MAP_DATA = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 2, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1 ,0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,],
    ]
TILE_SIZE = 32
screen = pygame.display.set_mode((640, 640))
pygame.display.set_caption("TAF Studio - BATA1.1")

# 玩家初始位置
player_x = 300
player_y = 300

# 加载并缩放图片
player_img = pygame.image.load("images/蓝2.png")
beijin = pygame.image.load("images/背景草地.png")
player_img = pygame.transform.scale(player_img, (50, 50))  # 缩放到合适大小
beijin = pygame.transform.scale(beijin, (640, 640))  # 草地背景
wall_img = pygame.image.load("images/墙壁.png")  # 32x32像素
grass_img = pygame.image.load("images/草地.png")  # 32x32像素
floor_img = pygame.image.load("images/地板.png") # 32x32像素
wall_img = pygame.transform.scale(wall_img, (TILE_SIZE, TILE_SIZE))  # 缩放到合适大小
grass_img = pygame.transform.scale(grass_img, (TILE_SIZE, TILE_SIZE))  # 缩放到合适大小
floor_img = pygame.transform.scale(floor_img, (TILE_SIZE, TILE_SIZE))  # 缩放到合适大小

clock = pygame.time.Clock()
running = True
player_decation = player_x,player_y

while running:
    # 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 键盘控制
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]: player_y -= 5
    if keys[pygame.K_s]: player_y += 5
    if keys[pygame.K_a]: player_x -= 5
    if keys[pygame.K_d]: player_x += 5

    # 边界限制
    if player_x < 0: player_x = 0
    if player_x > 640 - 50: player_x = 640 - 50
    if player_y < 0: player_y = 0
    if player_y > 640 - 50: player_y = 640 - 50

    # --- 绘制（顺序很重要！） ---

    # 1. 背景
    screen.blit(beijin, (0, 0))

    # 2. 地图（覆盖背景）
    for row_index, row in enumerate(MAP_DATA):
        for col_index, tile_type in enumerate(row):
            x = col_index * TILE_SIZE
            y = row_index * TILE_SIZE
            if tile_type == 1:
                screen.blit(wall_img, (x, y))
            elif tile_type == 2:
                screen.blit(grass_img, (x, y))
            else:
                screen.blit(floor_img, (x, y))

    # 3. 玩家（在地图最上面）
    screen.blit(player_img, (player_x, player_y))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()