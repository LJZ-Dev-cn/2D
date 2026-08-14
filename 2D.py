import pygame
import random
import math
import sys

# ============ Perlin噪声 ============
def generate_perlin_noise(width, height, scale=10.0, octaves=4, seed=0):
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
    def smoothstep(t): return t*t*(3-2*t)
    def lerp(a,b,t): return a + t*(b-a)
    def perlin_value(x,y):
        x0, x1 = math.floor(x), math.floor(x)+1
        y0, y1 = math.floor(y), math.floor(y)+1
        sx, sy = smoothstep(x-x0), smoothstep(y-y0)
        n0 = dot_product(x,y,x0,y0)
        n1 = dot_product(x,y,x1,y0)
        ix0 = lerp(n0,n1,sx)
        n0 = dot_product(x,y,x0,y1)
        n1 = dot_product(x,y,x1,y1)
        ix1 = lerp(n0,n1,sx)
        return lerp(ix0,ix1,sy)
    noise = [[0]*width for _ in range(height)]
    amp, freq, max_amp = 1.0, 1.0, 0.0
    for _ in range(octaves):
        for y in range(height):
            for x in range(width):
                noise[y][x] += amp * perlin_value(x/scale*freq, y/scale*freq)
        max_amp += amp
        amp *= 0.5
        freq *= 2.0
    for y in range(height):
        for x in range(width):
            noise[y][x] = (noise[y][x]/max_amp + 1)/2
    return noise

# ============ 无限地图 ============
class InfiniteMap:
    def __init__(self, tile_size=32, chunk_size=16, scale=12.0, octaves=4):
        self.tile_size = tile_size
        self.chunk_size = chunk_size
        self.scale, self.octaves = scale, octaves
        self.world_seed = 42
        self.chunks = {}
        self.terrain_colors = {
            0:(144,238,144), 1:(139,90,43), 2:(65,105,225),
            3:(34,139,34), 4:(255,255,255)
        }
        self.tile_cache = {tid: self._make_tile(color) for tid, color in self.terrain_colors.items()}
    def _make_tile(self, color):
        s = pygame.Surface((self.tile_size, self.tile_size)); s.fill(color); return s
    def get_chunk_key(self, cx, cy): return f"{cx},{cy}"
    def generate_chunk(self, cx, cy):
        seed = self.world_seed + cx*10000 + cy*7
        noise = generate_perlin_noise(self.chunk_size, self.chunk_size, self.scale, self.octaves, seed)
        terrain = [[0]*self.chunk_size for _ in range(self.chunk_size)]
        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                h = noise[y][x]
                terrain[y][x] = 2 if h<0.25 else 0 if h<0.35 else 3 if h<0.65 else 1 if h<0.85 else 4
        return terrain
    def get_tile(self, wx, wy):
        cx, lx = divmod(wx, self.chunk_size)
        cy, ly = divmod(wy, self.chunk_size)
        key = self.get_chunk_key(cx, cy)
        if key not in self.chunks:
            self.chunks[key] = self.generate_chunk(cx, cy)
        return self.chunks[key][ly][lx]
    def update(self, pcx, pcy, radius=3):
        needed = set()
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                needed.add((pcx+dx, pcy+dy))
        for cx, cy in needed:
            key = self.get_chunk_key(cx, cy)
            if key not in self.chunks:
                self.chunks[key] = self.generate_chunk(cx, cy)
        to_remove = []
        for key in list(self.chunks.keys()):
            cx, cy = map(int, key.split(','))
            if abs(cx-pcx)>radius+1 or abs(cy-pcy)>radius+1:
                to_remove.append(key)
        for key in to_remove:
            del self.chunks[key]
    def draw_visible(self, screen, cam_x, cam_y, sw, sh):
        start_wx, start_wy = cam_x, cam_y
        end_wx, end_wy = cam_x+sw+self.tile_size, cam_y+sh+self.tile_size
        scx0, scy0 = start_wx//(self.chunk_size*self.tile_size), start_wy//(self.chunk_size*self.tile_size)
        scx1, scy1 = end_wx//(self.chunk_size*self.tile_size)+1, end_wy//(self.chunk_size*self.tile_size)+1
        for cx in range(scx0, scx1+1):
            for cy in range(scy0, scy1+1):
                key = self.get_chunk_key(cx, cy)
                if key not in self.chunks: continue
                chunk = self.chunks[key]
                chunk_wx = cx*self.chunk_size*self.tile_size
                chunk_wy = cy*self.chunk_size*self.tile_size
                for ly in range(self.chunk_size):
                    for lx in range(self.chunk_size):
                        wx = chunk_wx + lx*self.tile_size
                        wy = chunk_wy + ly*self.tile_size
                        if wx + self.tile_size < cam_x or wx > cam_x+sw or wy+self.tile_size < cam_y or wy > cam_y+sh:
                            continue
                        tid = chunk[ly][lx]
                        sx, sy = wx - cam_x, wy - cam_y
                        screen.blit(self.tile_cache[tid], (sx, sy))

# ============ 有限地图 ============
class FiniteMap:
    def __init__(self, width=100, height=100, tile_size=32, scale=8.0, octaves=4):
        self.width, self.height = width, height
        self.tile_size = tile_size
        noise = generate_perlin_noise(width, height, scale, octaves, seed=999)
        self.map = [[0]*width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                h = noise[y][x]
                self.map[y][x] = 2 if h<0.20 else 0 if h<0.30 else 3 if h<0.60 else 1 if h<0.80 else 4
        # 边缘安全
        for x in range(width):
            self.map[0][x] = self.map[height-1][x] = 0
        for y in range(height):
            self.map[y][0] = self.map[y][width-1] = 0
        self.terrain_colors = {0:(144,238,144),1:(139,90,43),2:(65,105,225),3:(34,139,34),4:(255,255,255)}
        self.tile_cache = {tid: self._make_tile(color) for tid, color in self.terrain_colors.items()}
    def _make_tile(self, color):
        s = pygame.Surface((self.tile_size, self.tile_size)); s.fill(color); return s
    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map[y][x]
        return 0
    def is_walkable(self, x, y):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        return self.get_tile(x,y) != 2
    def draw(self, screen, cam_x, cam_y, sw, sh):
        sx0 = max(0, cam_x//self.tile_size)
        sy0 = max(0, cam_y//self.tile_size)
        sx1 = min(self.width, (cam_x+sw)//self.tile_size+1)
        sy1 = min(self.height, (cam_y+sh)//self.tile_size+1)
        for y in range(sy0, sy1):
            for x in range(sx0, sx1):
                tid = self.map[y][x]
                screen.blit(self.tile_cache[tid], (x*self.tile_size-cam_x, y*self.tile_size-cam_y))

# ============ 初始化 ============
pygame.init()
W, H = 800, 600
TILE = 32
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("TAF Studio")
clock = pygame.time.Clock()
font = pygame.font.SysFont('SimHei', 20)
warn_font = pygame.font.SysFont('SimHei', 28)

# 游戏状态
PLAYER_SIZE = 30

# ---- 小红（红色）在红世界（无限）----
a_x, a_y = 0, 0
a_surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE)); a_surf.fill((255,50,50))

# ---- 小绿（绿色）----
b_green_x, b_green_y = 50*TILE, 50*TILE  # 在绿世界的位置
b_red_x, b_red_y = None, None            # 在红世界的位置（初始未定义）
b_surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE)); b_surf.fill((50,255,50))

# 地图
inf_map = InfiniteMap(tile_size=TILE, chunk_size=16, scale=12.0, octaves=4)
fin_map = FiniteMap(width=100, height=100, tile_size=TILE, scale=8.0, octaves=4)

# 当前世界和玩家
game_stage = 'a_world'  # 'a_world' 或 'b_world'
cur_x, cur_y = a_x, a_y
cur_surf = a_surf

# 摄像机
camera_x, camera_y = 0, 0

# 切换动画
is_transition = False
trans_progress = 0
trans_duration = 60
_target_stage = None

# 状态标记
has_returned_from_green = False
has_shutdown_warning = False
ai_active = False   # 小红是否由AI控制

# L键计数与崩溃
l_press_count = 0
crashing = False
crash_timer = 60

# ============ 辅助函数 ============
def update_camera():
    global camera_x, camera_y
    target_x = cur_x - W//2 + PLAYER_SIZE//2
    target_y = cur_y - H//2 + PLAYER_SIZE//2
    if game_stage == 'b_world':
        max_x = fin_map.width*TILE - W
        max_y = fin_map.height*TILE - H
        target_x = max(0, min(target_x, max_x))
        target_y = max(0, min(target_y, max_y))
    camera_x, camera_y = target_x, target_y

def start_transition(target):
    global is_transition, trans_progress, _target_stage
    if not is_transition:
        is_transition = True
        trans_progress = 0
        _target_stage = target

def trigger_switch():
    global game_stage, cur_x, cur_y, cur_surf
    global a_x, a_y, b_green_x, b_green_y, b_red_x, b_red_y
    global ai_active, has_returned_from_green, has_shutdown_warning
    target = _target_stage

    if target == 'b_world' or (target is None and game_stage == 'a_world'):
        # 切换到绿世界
        game_stage = 'b_world'
        cur_x, cur_y = b_green_x, b_green_y
        cur_surf = b_surf
        ai_active = False
    else:
        # 切换到红世界
        game_stage = 'a_world'
        if b_red_x is None:
            b_red_x = a_x + 40
            b_red_y = a_y + 40
        cur_x, cur_y = b_red_x, b_red_y
        cur_surf = b_surf
        ai_active = True
        has_returned_from_green = True
        has_shutdown_warning = False

def check_trigger():
    global a_x, a_y
    if game_stage == 'a_world' and not is_transition and not ai_active:
        dx = a_x - 120*TILE
        dy = a_y - 120*TILE
        if math.hypot(dx, dy) < 20:
            start_transition('b_world')

def move_a_ai():
    global a_x, a_y
    speed = 2
    direction = pygame.time.get_ticks() // 500 % 4
    if direction == 0: a_y -= speed
    elif direction == 1: a_y += speed
    elif direction == 2: a_x -= speed
    else: a_x += speed
    # 限制范围防止跑太远
    a_x = max(-500*TILE, min(500*TILE, a_x))
    a_y = max(-500*TILE, min(500*TILE, a_y))

def can_move_b_green(x, y):
    corners = [(x,y),(x+PLAYER_SIZE,y),(x,y+PLAYER_SIZE),(x+PLAYER_SIZE,y+PLAYER_SIZE)]
    for cx, cy in corners:
        tx, ty = cx//TILE, cy//TILE
        if not fin_map.is_walkable(tx, ty):
            return False
    return True

def can_move_a_inf(x, y):
    corners = [(x,y),(x+PLAYER_SIZE,y),(x,y+PLAYER_SIZE),(x+PLAYER_SIZE,y+PLAYER_SIZE)]
    for cx, cy in corners:
        tx, ty = cx//TILE, cy//TILE
        if inf_map.get_tile(tx, ty) == 2:
            return False
    return True

def can_move_b_inf(x, y):
    corners = [(x,y),(x+PLAYER_SIZE,y),(x,y+PLAYER_SIZE),(x+PLAYER_SIZE,y+PLAYER_SIZE)]
    for cx, cy in corners:
        tx, ty = cx//TILE, cy//TILE
        if inf_map.get_tile(tx, ty) == 2:
            return False
    return True

# ============ 主循环 ============
running = True
while running:
    # ---- 事件 ----
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if has_returned_from_green:
                has_shutdown_warning = True
            else:
                running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
            if not is_transition and not crashing:
                # 增加计数
                l_press_count += 1
                # 达到10次触发崩溃
                if l_press_count >= 10:
                    crashing = True
                    crash_timer = 60  # 1秒倒计时
                # 切换逻辑（不阻止切换，崩溃后切换逻辑不再执行）
                if game_stage == 'a_world':
                    if ai_active:
                        b_red_x, b_red_y = cur_x, cur_y
                    start_transition('b_world')
                else:  # 'b_world'
                    b_green_x, b_green_y = cur_x, cur_y
                    start_transition('a_world')

    # ---- 崩溃处理 ----
    if crashing:
        crash_timer -= 1
        if crash_timer <= 0:
            pygame.quit()
            sys.exit()

    # ---- 更新 ----
    if is_transition:
        trans_progress += 1
        if trans_progress >= trans_duration:
            is_transition = False
            trigger_switch()
            trans_progress = 0
    else:
        keys = pygame.key.get_pressed()
        dx = dy = 0
        speed = 4
        if keys[pygame.K_w]: dy = -speed
        if keys[pygame.K_s]: dy = speed
        if keys[pygame.K_a]: dx = -speed
        if keys[pygame.K_d]: dx = speed

        if game_stage == 'a_world':
            if ai_active:
                # AI控制小红
                move_a_ai()
                # 玩家控制小绿
                if dx != 0:
                    nx = cur_x + dx
                    if can_move_b_inf(nx, cur_y):
                        cur_x = nx
                if dy != 0:
                    ny = cur_y + dy
                    if can_move_b_inf(cur_x, ny):
                        cur_y = ny
                # 更新小绿在红世界的坐标
                b_red_x, b_red_y = cur_x, cur_y
            else:
                # 玩家控制小红
                if dx != 0:
                    nx = a_x + dx
                    if can_move_a_inf(nx, a_y):
                        a_x = nx
                if dy != 0:
                    ny = a_y + dy
                    if can_move_a_inf(a_x, ny):
                        a_y = ny
                cur_x, cur_y = a_x, a_y
                cur_surf = a_surf
                check_trigger()
            # 更新无限地图区块
            if ai_active:
                pcx = cur_x // (inf_map.chunk_size * TILE)
                pcy = cur_y // (inf_map.chunk_size * TILE)
            else:
                pcx = a_x // (inf_map.chunk_size * TILE)
                pcy = a_y // (inf_map.chunk_size * TILE)
            inf_map.update(pcx, pcy, radius=3)
        else:
            # 绿世界，玩家控制小绿
            if dx != 0:
                nx = cur_x + dx
                if can_move_b_green(nx, cur_y):
                    cur_x = nx
            if dy != 0:
                ny = cur_y + dy
                if can_move_b_green(cur_x, ny):
                    cur_y = ny
            max_x = fin_map.width * TILE - PLAYER_SIZE
            max_y = fin_map.height * TILE - PLAYER_SIZE
            cur_x = max(0, min(cur_x, max_x))
            cur_y = max(0, min(cur_y, max_y))
            b_green_x, b_green_y = cur_x, cur_y

    # ---- 摄像机 ----
    update_camera()

    # ---- 绘制 ----
    screen.fill((0,0,0))
    if game_stage == 'a_world':
        inf_map.draw_visible(screen, camera_x, camera_y, W, H)
        # 绘制小红（始终在红世界）
        screen.blit(a_surf, (a_x - camera_x, a_y - camera_y))
    else:
        fin_map.draw(screen, camera_x, camera_y, W, H)
    # 绘制当前玩家角色
    screen.blit(cur_surf, (cur_x - camera_x, cur_y - camera_y))

    # ---- 切换动画 ----
    if is_transition:
        alpha = 255
        half = trans_duration // 2
        if trans_progress < half:
            alpha = int(255 * (trans_progress / half))
        else:
            alpha = 255 - int(255 * ((trans_progress - half) / half))
        mask = pygame.Surface((W, H))
        mask.fill((0,0,0))
        mask.set_alpha(alpha)
        screen.blit(mask, (0,0))
        txt = font.render("=== 世界切换中 ===", True, (255,255,255))
        screen.blit(txt, txt.get_rect(center=(W//2, H//2-40)))

    # ---- 信息栏 ----
    terrain_names = {0:'平原',1:'山地',2:'水域',3:'森林',4:'雪山'}
    tx, ty = cur_x//TILE, cur_y//TILE
    if game_stage == 'a_world':
        tid = inf_map.get_tile(tx, ty)
        stage_str = "红世界(无限)"
        if ai_active:
            stage_str += " [AI小红]"
        else:
            stage_str += " [玩家小红]"
    else:
        tid = fin_map.get_tile(tx, ty)
        stage_str = "绿世界(100x100)"
    info = f"{stage_str} | 坐标({tx},{ty}) | 地形:{terrain_names.get(tid,'未知')}"
    if has_shutdown_warning:
        info += " ⚠️系统异常⚠️"
    if crashing:
        info += " 💥崩溃中..."
    txt_surf = font.render(info, True, (255,255,255))
    bg = pygame.Surface((txt_surf.get_width()+10, txt_surf.get_height()+6))
    bg.fill((0,0,0)); bg.set_alpha(200)
    screen.blit(bg, (5,5))
    screen.blit(txt_surf, (10,8))

    # ---- 关闭警告 ----
    if has_shutdown_warning:
        warn_txt = "⚠️ 系统已被入侵，无法正常关闭！"
        warn_surf = warn_font.render(warn_txt, True, (255,0,0))
        if pygame.time.get_ticks() % 800 < 400:
            screen.blit(warn_surf, warn_surf.get_rect(center=(W//2, H-40)))

    # ---- 崩溃特效 ----
    if crashing:
        # 红色闪烁
        if pygame.time.get_ticks() % 200 < 100:
            flash = pygame.Surface((W, H))
            flash.set_alpha(150)
            flash.fill((255, 0, 0))
            screen.blit(flash, (0, 0))
        # 乱码文字
        crash_font = pygame.font.SysFont('SimHei', 48)
        texts = ["⚠️ 系统崩溃 ⚠️", "ERROR 0x0001", "数据丢失", "请立即重启"]
        idx = (pygame.time.get_ticks() // 150) % len(texts)
        txt = crash_font.render(texts[idx], True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=(W//2, H//2)))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()