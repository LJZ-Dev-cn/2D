import pygame
import random
import math

# ============ 1. 纯 Python 实现的 Perlin 噪声 ============
def generate_perlin_noise(width, height, scale=10.0, octaves=4, seed=0):
    """纯 Python 实现的 Perlin 噪声（支持种子）"""
    random.seed(seed)
    
    gradients = {}
    def get_gradient(x, y):
        if (x, y) not in gradients:
            angle = random.random() * 2 * math.pi
            gradients[(x, y)] = (math.cos(angle), math.sin(angle))
        return gradients[(x, y)]
    
    def dot_product(x, y, gx, gy):
        dx, dy = x - gx, y - gy
        gx_vec, gy_vec = get_gradient(gx, gy)
        return dx * gx_vec + dy * gy_vec
    
    def smoothstep(t):
        return t * t * (3 - 2 * t)
    
    def lerp(a, b, t):
        return a + t * (b - a)
    
    def perlin_value(x, y):
        x0 = math.floor(x)
        x1 = x0 + 1
        y0 = math.floor(y)
        y1 = y0 + 1
        
        sx = smoothstep(x - x0)
        sy = smoothstep(y - y0)
        
        n0 = dot_product(x, y, x0, y0)
        n1 = dot_product(x, y, x1, y0)
        ix0 = lerp(n0, n1, sx)
        
        n0 = dot_product(x, y, x0, y1)
        n1 = dot_product(x, y, x1, y1)
        ix1 = lerp(n0, n1, sx)
        
        return lerp(ix0, ix1, sy)
    
    noise_map = [[0 for _ in range(width)] for _ in range(height)]
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0
    
    for _ in range(octaves):
        for y in range(height):
            for x in range(width):
                nx = x / scale * frequency
                ny = y / scale * frequency
                noise_map[y][x] += amplitude * perlin_value(nx, ny)
        max_value += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    
    for y in range(height):
        for x in range(width):
            noise_map[y][x] = (noise_map[y][x] / max_value + 1) / 2
    
    return noise_map


# ============ 2. 无限地图系统 ============
class InfiniteMap:
    """无限地图生成器：只加载玩家周围的区块"""
    
    def __init__(self, tile_size=32, chunk_size=16, scale=12.0, octaves=4):
        self.tile_size = tile_size
        self.chunk_size = chunk_size
        self.scale = scale
        self.octaves = octaves
        self.world_seed = 42
        
        self.chunks = {}
        self.loaded_chunks = set()
        
        self.terrain_colors = {
            0: (144, 238, 144),   # 平原
            1: (139, 90, 43),     # 山地
            2: (65, 105, 225),    # 水域
            3: (34, 139, 34),     # 森林
            4: (255, 255, 255),   # 雪山
        }
        
        self.tile_cache = {}
        for terrain_id, color in self.terrain_colors.items():
            surf = pygame.Surface((tile_size, tile_size))
            surf.fill(color)
            self.tile_cache[terrain_id] = surf
    
    def get_chunk_key(self, chunk_x, chunk_y):
        return f"{chunk_x},{chunk_y}"
    
    def generate_chunk(self, chunk_x, chunk_y):
        seed = self.world_seed + chunk_x * 10000 + chunk_y * 7
        noise_map = generate_perlin_noise(
            self.chunk_size, self.chunk_size,
            scale=self.scale, octaves=self.octaves, seed=seed
        )
        
        terrain_map = [[0 for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]
        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                h = noise_map[y][x]
                if h < 0.25:
                    terrain_map[y][x] = 2
                elif h < 0.35:
                    terrain_map[y][x] = 0
                elif h < 0.65:
                    terrain_map[y][x] = 3
                elif h < 0.85:
                    terrain_map[y][x] = 1
                else:
                    terrain_map[y][x] = 4
        return terrain_map
    
    def get_tile(self, world_x, world_y):
        chunk_x = world_x // self.chunk_size
        chunk_y = world_y // self.chunk_size
        local_x = world_x % self.chunk_size
        local_y = world_y % self.chunk_size
        
        key = self.get_chunk_key(chunk_x, chunk_y)
        if key not in self.chunks:
            self.chunks[key] = self.generate_chunk(chunk_x, chunk_y)
        return self.chunks[key][local_y][local_x]
    
    def update(self, player_chunk_x, player_chunk_y, load_radius=3):
        needed_chunks = set()
        for dx in range(-load_radius, load_radius + 1):
            for dy in range(-load_radius, load_radius + 1):
                cx = player_chunk_x + dx
                cy = player_chunk_y + dy
                needed_chunks.add((cx, cy))
        
        for cx, cy in needed_chunks:
            key = self.get_chunk_key(cx, cy)
            if key not in self.chunks:
                self.chunks[key] = self.generate_chunk(cx, cy)
        
        to_remove = []
        for key in self.chunks:
            cx, cy = map(int, key.split(','))
            if abs(cx - player_chunk_x) > load_radius + 1 or abs(cy - player_chunk_y) > load_radius + 1:
                to_remove.append(key)
        for key in to_remove:
            del self.chunks[key]
        
        self.loaded_chunks = needed_chunks
    
    def get_visible_tiles(self, camera_x, camera_y, screen_width, screen_height):
        visible = []
        start_world_x = camera_x
        start_world_y = camera_y
        end_world_x = camera_x + screen_width + self.tile_size
        end_world_y = camera_y + screen_height + self.tile_size
        
        start_chunk_x = start_world_x // (self.chunk_size * self.tile_size)
        start_chunk_y = start_world_y // (self.chunk_size * self.tile_size)
        end_chunk_x = end_world_x // (self.chunk_size * self.tile_size) + 1
        end_chunk_y = end_world_y // (self.chunk_size * self.tile_size) + 1
        
        for chunk_x in range(start_chunk_x, end_chunk_x + 1):
            for chunk_y in range(start_chunk_y, end_chunk_y + 1):
                key = self.get_chunk_key(chunk_x, chunk_y)
                if key not in self.chunks:
                    continue
                chunk_data = self.chunks[key]
                chunk_world_x = chunk_x * self.chunk_size * self.tile_size
                chunk_world_y = chunk_y * self.chunk_size * self.tile_size
                
                for local_y in range(self.chunk_size):
                    for local_x in range(self.chunk_size):
                        world_x = chunk_world_x + local_x * self.tile_size
                        world_y = chunk_world_y + local_y * self.tile_size
                        if (world_x + self.tile_size < camera_x or 
                            world_x > camera_x + screen_width or
                            world_y + self.tile_size < camera_y or 
                            world_y > camera_y + screen_height):
                            continue
                        terrain_id = chunk_data[local_y][local_x]
                        screen_x = world_x - camera_x
                        screen_y = world_y - camera_y
                        visible.append((screen_x, screen_y, terrain_id))
        return visible


# ============ 3. 有限地图系统（100x100） ============
class FiniteMap:
    """有限地图：100×100 格，预先用 Perlin 噪声生成"""
    
    def __init__(self, width=100, height=100, tile_size=32, scale=8.0, octaves=4):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        
        # 使用 Perlin 噪声生成 100x100 地图
        noise_map = generate_perlin_noise(width, height, scale=scale, octaves=octaves, seed=999)
        
        self.map_data = [[0 for _ in range(width)] for _ in range(height)]
        for y in range(height):
            for x in range(width):
                h = noise_map[y][x]
                if h < 0.20:
                    self.map_data[y][x] = 2   # 水域
                elif h < 0.30:
                    self.map_data[y][x] = 0   # 平原
                elif h < 0.60:
                    self.map_data[y][x] = 3   # 森林
                elif h < 0.80:
                    self.map_data[y][x] = 1   # 山地
                else:
                    self.map_data[y][x] = 4   # 雪山
        
        # 确保边缘是陆地（防止玩家初始生成在水里）
        for x in range(width):
            self.map_data[0][x] = 0
            self.map_data[height-1][x] = 0
        for y in range(height):
            self.map_data[y][0] = 0
            self.map_data[y][width-1] = 0
        
        # 颜色配置
        self.terrain_colors = {
            0: (144, 238, 144),
            1: (139, 90, 43),
            2: (65, 105, 225),
            3: (34, 139, 34),
            4: (255, 255, 255),
        }
        
        self.tile_cache = {}
        for terrain_id, color in self.terrain_colors.items():
            surf = pygame.Surface((tile_size, tile_size))
            surf.fill(color)
            self.tile_cache[terrain_id] = surf
    
    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map_data[y][x]
        return 0
    
    def is_walkable(self, x, y):
        tile = self.get_tile(x, y)
        return tile != 2
    
    def draw(self, screen, camera_x, camera_y, screen_width, screen_height):
        """绘制地图（带摄像机）"""
        start_x = max(0, camera_x // self.tile_size)
        start_y = max(0, camera_y // self.tile_size)
        end_x = min(self.width, (camera_x + screen_width) // self.tile_size + 1)
        end_y = min(self.height, (camera_y + screen_height) // self.tile_size + 1)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                terrain_id = self.map_data[y][x]
                screen_x = x * self.tile_size - camera_x
                screen_y = y * self.tile_size - camera_y
                screen.blit(self.tile_cache[terrain_id], (screen_x, screen_y))


# ============ 4. Pygame 初始化 ============
pygame.init()

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
TILE_SIZE = 32

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("TAF Studio - 双角色切换·剧情触发")

clock = pygame.time.Clock()
font = pygame.font.SysFont('SimHei', 20)


# ============ 5. 游戏状态 ============
# 游戏阶段: 'a_world' = 小红在无限世界, 'b_world' = 小绿在有限世界
game_stage = 'a_world'

# --- 角色A（小红）---
player_a_x = 0
player_a_y = 0
PLAYER_SIZE = 30
player_a_surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
player_a_surf.fill((255, 50, 50))  # 红色

# --- 角色B（小绿）---
player_b_x = 50 * TILE_SIZE  # 出现在有限地图的中央位置
player_b_y = 50 * TILE_SIZE
player_b_surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
player_b_surf.fill((50, 255, 50))  # 绿色

# --- 当前激活的角色指针 ---
current_player_x = player_a_x
current_player_y = player_a_y
current_player_surf = player_a_surf

# --- 地图系统 ---
infinite_map = InfiniteMap(tile_size=TILE_SIZE, chunk_size=16, scale=12.0, octaves=4)
finite_map = FiniteMap(width=100, height=100, tile_size=TILE_SIZE, scale=8.0, octaves=4)

# --- 摄像机 ---
camera_x = 0
camera_y = 0

# --- 切换动画 ---
is_transitioning = False
transition_progress = 0
transition_duration = 60  # 1秒 (60帧)


# ============ 6. 核心函数 ============
def update_camera():
    global camera_x, camera_y
    if game_stage == 'a_world':
        target_x = current_player_x - WINDOW_WIDTH // 2 + PLAYER_SIZE // 2
        target_y = current_player_y - WINDOW_HEIGHT // 2 + PLAYER_SIZE // 2
    else:
        # 有限世界：限制摄像机不能超出地图边界
        target_x = current_player_x - WINDOW_WIDTH // 2 + PLAYER_SIZE // 2
        target_y = current_player_y - WINDOW_HEIGHT // 2 + PLAYER_SIZE // 2
        max_x = finite_map.width * TILE_SIZE - WINDOW_WIDTH
        max_y = finite_map.height * TILE_SIZE - WINDOW_HEIGHT
        target_x = max(0, min(target_x, max_x))
        target_y = max(0, min(target_y, max_y))
    
    camera_x = target_x
    camera_y = target_y


def check_trigger():
    """检查小红是否到达 (120, 120) 坐标"""
    global game_stage, is_transitioning, transition_progress
    global current_player_x, current_player_y, current_player_surf
    global player_a_x, player_a_y, player_b_x, player_b_y
    
    if game_stage == 'a_world' and not is_transitioning:
        # 检查小红的坐标是否在 (120, 120) 附近（允许误差）
        target_world_x = 120 * TILE_SIZE
        target_world_y = 120 * TILE_SIZE
        dist = math.sqrt((player_a_x - target_world_x)**2 + (player_a_y - target_world_y)**2)
        if dist < 20:  # 到达触发区域
            # 开始切换动画
            is_transitioning = True
            transition_progress = 0


def trigger_switch():
    """执行角色切换"""
    global game_stage, current_player_x, current_player_y, current_player_surf
    global player_a_x, player_a_y, player_b_x, player_b_y
    
    # 切换到小绿的坐标（放在有限地图中央）
    player_b_x = (finite_map.width // 2) * TILE_SIZE
    player_b_y = (finite_map.height // 2) * TILE_SIZE
    
    game_stage = 'b_world'
    current_player_x = player_b_x
    current_player_y = player_b_y
    current_player_surf = player_b_surf


def can_move_to_a(x, y):
    """小红的移动碰撞检测（无限地图）"""
    corners = [
        (x, y), (x + PLAYER_SIZE, y),
        (x, y + PLAYER_SIZE), (x + PLAYER_SIZE, y + PLAYER_SIZE)
    ]
    for cx, cy in corners:
        tile_x = cx // TILE_SIZE
        tile_y = cy // TILE_SIZE
        tile_type = infinite_map.get_tile(tile_x, tile_y)
        if tile_type == 2:  # 水域不可通行
            return False
    return True


def can_move_to_b(x, y):
    """小绿的移动碰撞检测（有限地图）"""
    corners = [
        (x, y), (x + PLAYER_SIZE, y),
        (x, y + PLAYER_SIZE), (x + PLAYER_SIZE, y + PLAYER_SIZE)
    ]
    for cx, cy in corners:
        tile_x = cx // TILE_SIZE
        tile_y = cy // TILE_SIZE
        if not finite_map.is_walkable(tile_x, tile_y):
            return False
    return True


# ============ 7. 主循环 ============
running = True

while running:
    # --- 事件处理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- 更新逻辑 ---
    if is_transitioning:
        # 切换动画进行中
        transition_progress += 1
        if transition_progress >= transition_duration:
            is_transitioning = False
            trigger_switch()
            transition_progress = 0
    else:
        # --- 键盘控制（根据当前阶段控制不同角色） ---
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        speed = 4
        
        if keys[pygame.K_w]:
            dy = -speed
        if keys[pygame.K_s]:
            dy = speed
        if keys[pygame.K_a]:
            dx = -speed
        if keys[pygame.K_d]:
            dx = speed
        
        if game_stage == 'a_world':
            # 控制小红
            if dx != 0:
                new_x = player_a_x + dx
                if can_move_to_a(new_x, player_a_y):
                    player_a_x = new_x
            if dy != 0:
                new_y = player_a_y + dy
                if can_move_to_a(player_a_x, new_y):
                    player_a_y = new_y
            current_player_x = player_a_x
            current_player_y = player_a_y
            current_player_surf = player_a_surf
            
            # 检查是否触发切换
            check_trigger()
            
            # 更新无限地图
            player_chunk_x = player_a_x // (infinite_map.chunk_size * TILE_SIZE)
            player_chunk_y = player_a_y // (infinite_map.chunk_size * TILE_SIZE)
            infinite_map.update(player_chunk_x, player_chunk_y, load_radius=3)
        
        else:
            # 控制小绿
            if dx != 0:
                new_x = player_b_x + dx
                if can_move_to_b(new_x, player_b_y):
                    player_b_x = new_x
            if dy != 0:
                new_y = player_b_y + dy
                if can_move_to_b(player_b_x, new_y):
                    player_b_y = new_y
            current_player_x = player_b_x
            current_player_y = player_b_y
            current_player_surf = player_b_surf

    # --- 更新摄像机 ---
    update_camera()

    # --- 绘制 ---
    screen.fill((0, 0, 0))
    
    if game_stage == 'a_world':
        # 绘制无限地图
        visible_tiles = infinite_map.get_visible_tiles(camera_x, camera_y, WINDOW_WIDTH, WINDOW_HEIGHT)
        for screen_x, screen_y, terrain_id in visible_tiles:
            screen.blit(infinite_map.tile_cache[terrain_id], (screen_x, screen_y))
    else:
        # 绘制有限地图
        finite_map.draw(screen, camera_x, camera_y, WINDOW_WIDTH, WINDOW_HEIGHT)
    
    # 绘制当前玩家
    screen.blit(current_player_surf, (current_player_x - camera_x, current_player_y - camera_y))
    
    # --- 绘制切换动画（黑屏淡入淡出） ---
    if is_transitioning:
        # 半透明黑色遮罩，逐渐变黑再变亮
        alpha = 255
        if transition_progress < transition_duration // 2:
            # 前半段：逐渐变黑
            alpha = int(255 * (transition_progress / (transition_duration // 2)))
        else:
            # 后半段：逐渐变亮
            progress_in_second_half = transition_progress - transition_duration // 2
            alpha = 255 - int(255 * (progress_in_second_half / (transition_duration // 2)))
        
        # 绘制遮罩
        mask = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        mask.fill((0, 0, 0))
        mask.set_alpha(alpha)
        screen.blit(mask, (0, 0))
        
        # 显示切换文字
        switch_text = font.render("=== 世界切换中 ===", True, (255, 255, 255))
        text_rect = switch_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 40))
        screen.blit(switch_text, text_rect)
    
    # --- 显示调试信息 ---
    terrain_names = {0: '平原', 1: '山地', 2: '水域', 3: '森林', 4: '雪山'}
    tile_x = current_player_x // TILE_SIZE
    tile_y = current_player_y // TILE_SIZE
    
    if game_stage == 'a_world':
        current_tile = infinite_map.get_tile(tile_x, tile_y)
        stage_text = "世界A (无限) - 小红"
        trigger_status = f"触发条件: (120,120) 目标距离: {math.sqrt((player_a_x/TILE_SIZE - 120)**2 + (player_a_y/TILE_SIZE - 120)**2):.1f}"
        info_text = f"{stage_text} | 坐标: ({tile_x}, {tile_y}) | 地形: {terrain_names.get(current_tile, '未知')} | {trigger_status}"
    else:
        current_tile = finite_map.get_tile(tile_x, tile_y)
        stage_text = "世界B (100x100) - 小绿"
        info_text = f"{stage_text} | 坐标: ({tile_x}, {tile_y}) | 地形: {terrain_names.get(current_tile, '未知')}"
    
    text_surf = font.render(info_text, True, (255, 255, 255))
    text_bg = pygame.Surface((text_surf.get_width() + 10, text_surf.get_height() + 6))
    text_bg.fill((0, 0, 0))
    text_bg.set_alpha(200)
    screen.blit(text_bg, (5, 5))
    screen.blit(text_surf, (10, 8))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()