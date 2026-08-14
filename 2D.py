import pygame
pygame.init()
MAP_DATA = [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 2, 2, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
]
TILE_SIZE = 32
screen = pygame.display.set_mode((640, 640))
pygame.display.set_caption("TAF Studio - BATA1")

# 玩家初始位置
player_x = 300
player_y = 300

# 加载并缩放图片
player_img = pygame.image.load("images/蓝2.png")
beijin = pygame.image.load("images/背景草地.png")
player_img = pygame.transform.scale(player_img, (50, 50))  # 缩放到合适大小
beijin = pygame.transform.scale(beijin, (640, 640))  # 草地背景

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
    # 边界限制（防止跑出画面）
    if player_x < 0: player_x = 0
    if player_x > 640 - 50: player_x = 640 - 50
    if player_y < 0: player_y = 0
    if player_y > 640 - 50: player_y = 640 - 50

    # 绘制背景和角色
    screen.blit(beijin,(0,0))     # 草地背景
    screen.blit(player_img, (player_x, player_y))  # 绘制图片

    pygame.display.flip()
    clock.tick(60)

pygame.quit()