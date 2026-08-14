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
        self.chunk_size = chunk_size  # 每个区块 16x16 格
        self.scale = scale
        self.octaves = octaves
        self.world_seed = 42  # 固定种子，保证同一位置地形永远一致
        
        # 存储已生成的区块：key = (chunk_x, chunk_y), value = 地形数组
        self.chunks = {}
        
        # 当前加载的区块范围
        self.loaded_chunks = set()
        
        # 地形颜色
        self.terrain_colors = {
            0: (144, 238, 144),   # 平原
            1: (139, 90, 43),     # 山地
            2: (65, 105, 225),    # 水域
            3: (34, 139, 34),     # 森林
            4: (255, 255, 255),   # 雪山
        }
        
        # 预创建图块缓存（每个地形类型一个 Surface）
        self.tile_cache = {}
        for terrain_id, color in self.terrain_colors.items():
            surf = pygame.Surface((tile_size, tile_size))
            surf.fill(color)
            self.tile_cache[terrain_id] = surf
    
    def get_chunk_key(self, chunk_x, chunk_y):
        """生成区块的唯一键"""
        return f"{chunk_x},{chunk_y}"
    
    def generate_chunk(self, chunk_x, chunk_y):
        """生成一个区块的地形数据"""
        # 使用区块坐标作为种子的一部分，保证同一位置永远一致
        seed = self.world_seed + chunk_x * 10000 + chunk_y * 7
        
        # 生成该区块的噪声图
        noise_map = generate_perlin_noise(
            self.chunk_size, 
            self.chunk_size, 
            scale=self.scale, 
            octaves=self.octaves,
            seed=seed
        )
        
        # 转换为地形类型
        terrain_map = [[0 for _ in range(self.chunk_size)] for _ in range(self.chunk_size)]
        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                h = noise_map[y][x]
                if h < 0.25:
                    terrain_map[y][x] = 2   # 水域
                elif h < 0.35:
                    terrain_map[y][x] = 0   # 平原
                elif h < 0.65:
                    terrain_map[y][x] = 3   # 森林
                elif h < 0.85:
                    terrain_map[y][x] = 1   # 山地
                else:
                    terrain_map[y][x] = 4   # 雪山
        
        return terrain_map
    
    def get_tile(self, world_x, world_y):
        """获取世界坐标 (world_x, world_y) 处的地形类型"""
        # 将世界坐标转换为区块坐标和区块内坐标
        chunk_x = world_x // self.chunk_size
        chunk_y = world_y // self.chunk_size
        local_x = world_x % self.chunk_size
        local_y = world_y % self.chunk_size
        
        key = self.get_chunk_key(chunk_x, chunk_y)
        
        # 如果区块还没生成，先生成
        if key not in self.chunks:
            self.chunks[key] = self.generate_chunk(chunk_x, chunk_y)
        
        return self.chunks[key][local_y][local_x]
    
    def update(self, player_chunk_x, player_chunk_y, load_radius=2):
        """
        更新加载的区块：以玩家所在区块为中心，加载周围 load_radius 个区块
        """
        # 计算需要加载的区块范围
        needed_chunks = set()
        for dx in range(-load_radius, load_radius + 1):
            for dy in range(-load_radius, load_radius + 1):
                cx = player_chunk_x + dx
                cy = player_chunk_y + dy
                needed_chunks.add((cx, cy))
        
        # 生成新的区块
        for cx, cy in needed_chunks:
            key = self.get_chunk_key(cx, cy)
            if key not in self.chunks:
                self.chunks[key] = self.generate_chunk(cx, cy)
        
        # 卸载距离玩家太远的区块（节省内存）
        to_remove = []
        for key in self.chunks:
            cx, cy = map(int, key.split(','))
            if abs(cx - player_chunk_x) > load_radius + 1 or abs(cy - player_chunk_y) > load_radius + 1:
                to_remove.append(key)
        
        for key in to_remove:
            del self.chunks[key]
        
        self.loaded_chunks = needed_chunks
    
    def get_visible_tiles(self, camera_x, camera_y, screen_width, screen_height):
        """
        获取在屏幕可见范围内的所有图块及其绘制位置
        返回：[(screen_x, screen_y, terrain_id), ...]
        """
        visible = []
        
        # 计算可见范围（在世界坐标中）
        start_world_x = camera_x
        start_world_y = camera_y
        end_world_x = camera_x + screen_width + self.tile_size
        end_world_y = camera_y + screen_height + self.tile_size
        
        # 转换为区块范围
        start_chunk_x = start_world_x // (self.chunk_size * self.tile_size)
        start_chunk_y = start_world_y // (self.chunk_size * self.tile_size)
        end_chunk_x = end_world_x // (self.chunk_size * self.tile_size) + 1
        end_chunk_y = end_world_y // (self.chunk_size * self.tile_size) + 1
        
        # 遍历可见范围内的区块
        for chunk_x in range(start_chunk_x, end_chunk_x + 1):
            for chunk_y in range(start_chunk_y, end_chunk_y + 1):
                key = self.get_chunk_key(chunk_x, chunk_y)
                if key not in self.chunks:
                    continue
                
                chunk_data = self.chunks[key]
                
                # 该区块左上角的世界坐标
                chunk_world_x = chunk_x * self.chunk_size * self.tile_size
                chunk_world_y = chunk_y * self.chunk_size * self.tile_size
                
                # 遍历区块内的所有图块
                for local_y in range(self.chunk_size):
                    for local_x in range(self.chunk_size):
                        world_x = chunk_world_x + local_x * self.tile_size
                        world_y = chunk_world_y + local_y * self.tile_size
                        
                        # 检查是否在可见范围内
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


# ============ 3. Pygame 初始化 ============
pygame.init()

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("TAF Studio - 无限地图 + 摄像机跟随")

# ============ 4. 创建无限地图 ============
TILE_SIZE = 32
CHUNK_SIZE = 16
world_map = InfiniteMap(tile_size=TILE_SIZE, chunk_size=CHUNK_SIZE, scale=12.0, octaves=4)

# ============ 5. 玩家设置 ============
PLAYER_SIZE = 30
player_x = 0
player_y = 0

player_surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE))
player_surf.fill((255, 50, 50))


# ============ 6. 摄像机 ============ 
camera_x = 0
camera_y = 0


def update_camera():
    global camera_x, camera_y
    target_camera_x = player_x - WINDOW_WIDTH // 2 + PLAYER_SIZE // 2
    target_camera_y = player_y - WINDOW_HEIGHT // 2 + PLAYER_SIZE // 2
    camera_x = target_camera_x
    camera_y = target_camera_y


# ============ 7. 辅助函数 ============
def is_walkable(tile_type):
    return tile_type != 2


def can_move_to(x, y):
    # 检查玩家的四个角是否能走
    corners = [
        (x, y),
        (x + PLAYER_SIZE, y),
        (x, y + PLAYER_SIZE),
        (x + PLAYER_SIZE, y + PLAYER_SIZE),
    ]
    for cx, cy in corners:
        # 将像素坐标转换为图块坐标
        tile_x = cx // TILE_SIZE
        tile_y = cy // TILE_SIZE
        tile_type = world_map.get_tile(tile_x, tile_y)
        if not is_walkable(tile_type):
            return False
    return True


# ============ 8. 主循环 ============
clock = pygame.time.Clock()
running = True

while running:
    # --- 事件处理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- 键盘控制 ---
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

    if dx != 0:
        new_x = player_x + dx
        if can_move_to(new_x, player_y):
            player_x = new_x
    
    if dy != 0:
        new_y = player_y + dy
        if can_move_to(player_x, new_y):
            player_y = new_y

    # --- 更新无限地图（根据玩家位置加载区块） ---
    player_chunk_x = player_x // (CHUNK_SIZE * TILE_SIZE)
    player_chunk_y = player_y // (CHUNK_SIZE * TILE_SIZE)
    world_map.update(player_chunk_x, player_chunk_y, load_radius=3)

    # --- 更新摄像机 ---
    update_camera()

    # --- 绘制 ---
    screen.fill((0, 0, 0))
    
    # 1. 绘制可见地图
    visible_tiles = world_map.get_visible_tiles(camera_x, camera_y, WINDOW_WIDTH, WINDOW_HEIGHT)
    for screen_x, screen_y, terrain_id in visible_tiles:
        screen.blit(world_map.tile_cache[terrain_id], (screen_x, screen_y))
    
    # 2. 绘制玩家
    screen.blit(player_surf, (player_x - camera_x, player_y - camera_y))

    # 3. 显示调试信息（简洁版）
    font = pygame.font.SysFont('SimHei', 18)
    center_x = player_x + PLAYER_SIZE // 2
    center_y = player_y + PLAYER_SIZE // 2
    tile_x = center_x // TILE_SIZE
    tile_y = center_y // TILE_SIZE
    
    terrain_names = {0: '平原', 1: '山地', 2: '水域', 3: '森林', 4: '雪山'}
    current_tile = world_map.get_tile(tile_x, tile_y)
    info_text = f"坐标: ({tile_x}, {tile_y})  地形: {terrain_names.get(current_tile, '未知')}  区块: ({player_chunk_x}, {player_chunk_y})  已加载: {len(world_map.chunks)}个区块"
    
    text_surf = font.render(info_text, True, (255, 255, 255))
    text_bg = pygame.Surface((text_surf.get_width() + 10, text_surf.get_height() + 6))
    text_bg.fill((0, 0, 0))
    text_bg.set_alpha(180)
    screen.blit(text_bg, (5, 5))
    screen.blit(text_surf, (10, 8))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()