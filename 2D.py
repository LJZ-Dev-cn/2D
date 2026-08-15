import pygame
import random
import math
import sys
import json
import os

# ==================== 配置文件 ====================
CONFIG_PATH = "config.json"

def load_config():
    default = {
        "window": {"width": 800, "height": 600},
        "debug": {"show_on_start": True},
        "gameplay": {"player_speed": 4, "sprint_speed": 8, "ai_speed": 1.5},
        "fragment": {"position_x": 75, "position_y": 75, "require_unlock": True},
        "npc": {"guide_pos_x": 45, "guide_pos_y": 45, "merchant_pos_x": 60, "merchant_pos_y": 30},
        "dialogues": {
            "引路者": {
                "start": {
                    "text": "你好，旅行者。我是这个世界的引路者。",
                    "options": [
                        {"key": "yes", "text": "是的，我从红世界来。", "next": "red_world"},
                        {"key": "no", "text": "不，我只是迷路了。", "next": "lost"},
                        {"key": "who", "text": "你是谁？", "next": "who_am_i"},
                        {"key": "return_fragment", "text": "我找到了一个碎片，想交给你", "next": "return_fragment"}
                    ]
                }
            },
            "商人": {
                "start": {
                    "text": "嘿，旅行者！要看看我的商品吗？",
                    "options": [
                        {"key": "yes", "text": "好啊，有什么？", "next": "goods"},
                        {"key": "no", "text": "不了，我没兴趣。", "next": "no_thanks"},
                        {"key": "info", "text": "你知道世界碎片的事吗？", "next": "fragment_info"}
                    ]
                }
            }
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    else:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=4, ensure_ascii=False)
        return default

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def load_dialogues(config):
    """从配置加载对话，若缺失则使用默认（全局变量 npc1_dialogue, npc2_dialogue）"""
    default_dialogues = {
        "引路者": npc1_dialogue,
        "商人": npc2_dialogue
    }
    if "dialogues" in config and config["dialogues"]:
        loaded = {}
        for name, default_tree in default_dialogues.items():
            if name in config["dialogues"]:
                custom_tree = config["dialogues"][name]
                merged_tree = default_tree.copy()
                for node_key, node_data in custom_tree.items():
                    merged_tree[node_key] = node_data
                loaded[name] = merged_tree
            else:
                loaded[name] = default_tree
        return loaded
    return default_dialogues

# ==================== Perlin 噪声 ====================
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

# ==================== 无限地图 ====================
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
        wx = int(wx); wy = int(wy)
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

# ==================== 有限地图 ====================
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
        for x in range(width):
            self.map[0][x] = self.map[height-1][x] = 0
        for y in range(height):
            self.map[y][0] = self.map[y][width-1] = 0
        self.terrain_colors = {0:(144,238,144),1:(139,90,43),2:(65,105,225),3:(34,139,34),4:(255,255,255)}
        self.tile_cache = {tid: self._make_tile(color) for tid, color in self.terrain_colors.items()}
    def _make_tile(self, color):
        s = pygame.Surface((self.tile_size, self.tile_size)); s.fill(color); return s
    def get_tile(self, x, y):
        x = int(x); y = int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map[y][x]
        return 0
    def is_walkable(self, x, y):
        x = int(x); y = int(y)
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

# ==================== NPC 系统 ====================
class NPC:
    def __init__(self, x, y, name, dialogue_tree, color=(255, 215, 0)):
        self.x, self.y = x, y
        self.name = name
        self.dialogue_tree = dialogue_tree
        self.color = color
        self.radius = 60
        self.current_node = "start"
        self.dialogue_history = []
        self.size = 30
    def is_near(self, px, py):
        dx = self.x + self.size//2 - px
        dy = self.y + self.size//2 - py
        return math.hypot(dx, dy) < self.radius
    def get_current_dialogue(self):
        return self.dialogue_tree.get(self.current_node)
    def choose_option(self, option_key):
        node = self.get_current_dialogue()
        if node and "options" in node:
            for opt in node["options"]:
                if opt["key"] == option_key:
                    self.current_node = opt["next"]
                    self.dialogue_history.append({"speaker": self.name, "text": node["text"], "choice": opt["text"]})
                    return True
        return False
    def reset_dialogue(self):
        self.current_node = "start"
    def is_dialogue_finished(self):
        node = self.get_current_dialogue()
        return not (node and "options" in node and len(node["options"]) > 0)

# ==================== 碎片系统 ====================
class Fragment:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.size = 24
        self.collected = False
        self.radius = 40
    def draw(self, screen, cam_x, cam_y, unlocked=False):
        if self.collected:
            return
        if not unlocked:
            color = (100,100,100)
            alpha = 100
        else:
            glow = 150 + int(105 * math.sin(pygame.time.get_ticks() / 300))
            color = (255, glow, 0)
            alpha = 255
        for r in range(12, 0, -2):
            a = int(alpha * 0.3 * (r / 12))
            surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            col = (255,255,150,a) if unlocked else (100,100,100,a)
            pygame.draw.circle(surf, col, (r, r), r)
            screen.blit(surf, (self.x - cam_x - r + self.size//2, self.y - cam_y - r + self.size//2))
        pygame.draw.circle(screen, color, (self.x - cam_x + self.size//2, self.y - cam_y + self.size//2), self.size//2)
        if unlocked:
            pygame.draw.circle(screen, (255,255,255), (self.x - cam_x + self.size//2 - 4, self.y - cam_y + self.size//2 - 4), 5)
    def is_near(self, px, py):
        if self.collected:
            return False
        dx = self.x + self.size//2 - px
        dy = self.y + self.size//2 - py
        return math.hypot(dx, dy) < self.radius
    def collect(self):
        self.collected = True

# ==================== 默认对话数据 ====================
npc1_dialogue = {
    "start": {
        "text": "你好，旅行者。我是这个世界的引路者。我看你面生，应该是从另一个世界来的吧？",
        "options": [
            {"key": "yes", "text": "是的，我从红世界来。", "next": "red_world"},
            {"key": "no", "text": "不，我只是迷路了。", "next": "lost"},
            {"key": "who", "text": "你是谁？", "next": "who_am_i"},
            {"key": "return_fragment", "text": "我找到了一个碎片，想交给你", "next": "return_fragment"}
        ]
    },
    "red_world": {
        "text": "果然如此。红世界和绿世界本是一体，但被某种力量分开了。你能来到这里，说明你肩负着某种使命。",
        "options": [
            {"key": "mission", "text": "什么使命？", "next": "mission_detail"},
            {"key": "thanks", "text": "谢谢你告诉我这些。", "next": "end"}
        ]
    },
    "lost": {
        "text": "迷路？在这个世界里迷路是很危险的。不过既然你遇到了我，我可以告诉你一些事情。",
        "options": [
            {"key": "tell", "text": "请告诉我。", "next": "mission_detail"},
            {"key": "leave", "text": "不了，我还是自己探索吧。", "next": "end"}
        ]
    },
    "who_am_i": {
        "text": "我是这个世界的守护者，也是红世界和绿世界之间的桥梁。我在这里等待了很久，等待能够穿越两界的人出现。",
        "options": [
            {"key": "why", "text": "为什么要等？", "next": "mission_detail"},
            {"key": "ok", "text": "原来如此。", "next": "end"}
        ]
    },
    "mission_detail": {
        "text": "两个世界正在逐渐分离，如果继续这样下去，整个世界都会崩溃。你需要找到三个世界碎片，将它们合为一体。",
        "options": [
            {"key": "fragment1", "text": "第一个碎片在哪里？", "next": "fragment_info"},
            {"key": "fragment2", "text": "我为什么要相信你？", "next": "trust"}
        ]
    },
    "fragment_info": {
        "text": "第一个碎片就在绿世界的东方祭坛上。找到它之后，回来找我，我会告诉你下一个碎片的位置。",
        "options": [{"key": "ok", "text": "好的，我这就去找。", "next": "end"}]
    },
    "trust": {
        "text": "你不需要相信我。但你看这个——（展示一个发光的碎片）这是第一个世界碎片。如果你能找到它，你就知道我说的是真的了。",
        "options": [{"key": "ok", "text": "好，我会找到它的。", "next": "end"}]
    },
    "return_fragment": {
        "text": "太好了！这就是我提到的世界碎片。你成功完成了第一项考验。记住，你还有两个碎片需要寻找——一个在红世界深处，另一个隐藏在世界的裂缝中。我会在地图上标注下一个碎片的位置。继续前进吧，旅行者。",
        "options": []
    },
    "no_fragment": {
        "text": "你确定吗？我没有感应到碎片的气息。你在开玩笑吧？……算了，等你真正找到碎片再来找我。",
        "options": [{"key": "ok", "text": "好吧，我再去找找。", "next": "end"}]
    },
    "end": {"text": "去吧，旅行者。你的旅途才刚刚开始。", "options": []}
}

npc2_dialogue = {
    "start": {
        "text": "嘿，旅行者！我这边有一些好东西，要不要看看？",
        "options": [
            {"key": "yes", "text": "好啊，有什么？", "next": "goods"},
            {"key": "no", "text": "不了，我没兴趣。", "next": "no_thanks"},
            {"key": "info", "text": "你知道世界碎片的事吗？", "next": "fragment_info"}
        ]
    },
    "goods": {
        "text": "我这里有武器、防具、还有各种稀奇古怪的玩意儿。不过……我注意到你身上没有本地货币。这样吧，如果你能帮我找到失落的货物，我可以免费送你一件装备。",
        "options": [
            {"key": "accept", "text": "成交！", "next": "quest_accept"},
            {"key": "decline", "text": "算了，我没时间。", "next": "end"}
        ]
    },
    "quest_accept": {
        "text": "太好了！我的货物在绿世界西北角的遗迹里。帮我带回来，你会得到丰厚的报酬。",
        "options": [{"key": "ok", "text": "没问题，交给我吧。", "next": "end"}]
    },
    "no_thanks": {
        "text": "好吧，如果你改变主意了，随时来找我。",
        "options": [{"key": "ok", "text": "好的。", "next": "end"}]
    },
    "fragment_info": {
        "text": "世界碎片？那玩意儿可不得了。我听说有一个碎片就在绿世界中央的祭坛上，但那里有守护者看守。我劝你小心点。",
        "options": [
            {"key": "thanks", "text": "多谢提醒。", "next": "end"},
            {"key": "more", "text": "还有其他碎片吗？", "next": "more_fragments"}
        ]
    },
    "more_fragments": {
        "text": "据说一共有三个碎片。一个在中央祭坛，一个在红世界的某处，还有一个……被隐藏在世界的裂缝中。这就是我知道的全部了。",
        "options": [{"key": "thanks", "text": "谢谢，你帮了大忙。", "next": "end"}]
    },
    "end": {"text": "祝你好运，旅行者。", "options": []}
}

# ==================== 任务追踪器 ====================
class QuestTracker:
    def __init__(self):
        self.quests = {}
        self.flags = {}
        self.set_flag("fragment_unlocked", False)
        self.set_flag("has_fragment", False)
        self.set_flag("fragment_returned", False)
    def add_quest(self, qid, title, desc):
        self.quests[qid] = {"title": title, "description": desc, "completed": False}
    def complete_quest(self, qid):
        if qid in self.quests:
            self.quests[qid]["completed"] = True
    def set_flag(self, name, value=True):
        self.flags[name] = value
    def get_flag(self, name, default=False):
        return self.flags.get(name, default)

# ==================== 初始化配置 ====================
config = load_config()
W = config["window"]["width"]
H = config["window"]["height"]
TILE = 32

# ==================== 加载对话 ====================
dialogues = load_dialogues(config)
npc1_dialogue_loaded = dialogues["引路者"]
npc2_dialogue_loaded = dialogues["商人"]

# ==================== Pygame 初始化 ====================
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("TAF Studio - BETA 4.0-snapshot2 调试+配置")
clock = pygame.time.Clock()
font = pygame.font.SysFont('SimHei', 20)
dialogue_font = pygame.font.SysFont('SimHei', 22)
warn_font = pygame.font.SysFont('SimHei', 28)

# 调试变量
show_debug = config["debug"]["show_on_start"]

# 游戏状态
PLAYER_SIZE = 30
a_x, a_y = 0, 0
a_surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE)); a_surf.fill((255,50,50))
b_green_x, b_green_y = 50*TILE, 50*TILE
b_red_x, b_red_y = None, None
b_surf = pygame.Surface((PLAYER_SIZE, PLAYER_SIZE)); b_surf.fill((50,255,50))

inf_map = InfiniteMap(tile_size=TILE, chunk_size=16, scale=12.0, octaves=4)
fin_map = FiniteMap(width=100, height=100, tile_size=TILE, scale=8.0, octaves=4)

guide_x = config["npc"]["guide_pos_x"] * TILE
guide_y = config["npc"]["guide_pos_y"] * TILE
merchant_x = config["npc"]["merchant_pos_x"] * TILE
merchant_y = config["npc"]["merchant_pos_y"] * TILE
npc1 = NPC(guide_x, guide_y, "引路者", npc1_dialogue_loaded, (255,215,0))
npc2 = NPC(merchant_x, merchant_y, "商人", npc2_dialogue_loaded, (0,200,255))
npcs = [npc1, npc2]

frag_x = config["fragment"]["position_x"] * TILE
frag_y = config["fragment"]["position_y"] * TILE
fragment = Fragment(frag_x, frag_y)

quest_tracker = QuestTracker()
quest_tracker.add_quest("find_fragment", "寻找世界碎片", "从东方祭坛取回世界碎片")
quest_tracker.set_flag("met_guide", False)

game_stage = 'a_world'
cur_x, cur_y = a_x, a_y
cur_surf = a_surf
camera_x, camera_y = 0, 0

is_transition = False
trans_progress = 0
trans_duration = 60
_target_stage = None

has_returned_from_green = False
has_shutdown_warning = False
ai_active = False
l_press_count = 0
crashing = False
crash_timer = 60

dialogue_active = False
current_npc = None
dialogue_waiting_for_choice = False
dialogue_choice_options = []

ai_target_x, ai_target_y = None, None

# ==================== 辅助函数 ====================
def update_camera():
    global camera_x, camera_y
    tx = cur_x - W//2 + PLAYER_SIZE//2
    ty = cur_y - H//2 + PLAYER_SIZE//2
    if game_stage == 'b_world':
        tx = max(0, min(tx, fin_map.width*TILE - W))
        ty = max(0, min(ty, fin_map.height*TILE - H))
    camera_x, camera_y = tx, ty

def start_transition(target):
    global is_transition, trans_progress, _target_stage
    if not is_transition:
        is_transition = True
        trans_progress = 0
        _target_stage = target

def trigger_switch():
    global game_stage, cur_x, cur_y, cur_surf, ai_active, has_returned_from_green, has_shutdown_warning
    target = _target_stage
    if target == 'b_world' or (target is None and game_stage == 'a_world'):
        game_stage = 'b_world'
        cur_x, cur_y = b_green_x, b_green_y
        cur_surf = b_surf
        ai_active = False
    else:
        game_stage = 'a_world'
        global b_red_x, b_red_y
        if b_red_x is None:
            b_red_x, b_red_y = a_x + 40, a_y + 40
        cur_x, cur_y = b_red_x, b_red_y
        cur_surf = b_surf
        ai_active = True
        has_returned_from_green = True
        has_shutdown_warning = False

def check_trigger():
    global a_x, a_y
    if game_stage == 'a_world' and not is_transition and not ai_active:
        if math.hypot(a_x - 120*TILE, a_y - 120*TILE) < 20:
            start_transition('b_world')

def move_a_ai():
    global a_x, a_y, ai_target_x, ai_target_y
    if ai_target_x is None or ai_target_y is None or math.hypot(a_x-ai_target_x, a_y-ai_target_y) < 20:
        ai_target_x = random.randint(-100, 100) * TILE
        ai_target_y = random.randint(-100, 100) * TILE
    dx, dy = ai_target_x - a_x, ai_target_y - a_y
    dist = math.hypot(dx, dy)
    if dist == 0:
        return
    speed = config["gameplay"]["ai_speed"]
    move_x, move_y = dx/dist*speed, dy/dist*speed
    nx, ny = a_x + move_x, a_y + move_y
    if can_move_a_inf(nx, a_y):
        a_x = nx
    else:
        ai_target_x = a_x + random.randint(-80, 80)
    if can_move_a_inf(a_x, ny):
        a_y = ny
    else:
        ai_target_y = a_y + random.randint(-80, 80)

def can_move_b_green(x, y):
    for cx, cy in [(x,y),(x+PLAYER_SIZE,y),(x,y+PLAYER_SIZE),(x+PLAYER_SIZE,y+PLAYER_SIZE)]:
        if not fin_map.is_walkable(cx//TILE, cy//TILE):
            return False
    return True

def can_move_a_inf(x, y):
    for cx, cy in [(x,y),(x+PLAYER_SIZE,y),(x,y+PLAYER_SIZE),(x+PLAYER_SIZE,y+PLAYER_SIZE)]:
        if inf_map.get_tile(cx//TILE, cy//TILE) == 2:
            return False
    return True

def can_move_b_inf(x, y):
    for cx, cy in [(x,y),(x+PLAYER_SIZE,y),(x,y+PLAYER_SIZE),(x+PLAYER_SIZE,y+PLAYER_SIZE)]:
        if inf_map.get_tile(cx//TILE, cy//TILE) == 2:
            return False
    return True

def render_dialogue_box(screen, npc, tracker):
    global dialogue_choice_options, dialogue_waiting_for_choice
    node = npc.get_current_dialogue()
    if not node:
        return
    win_w, win_h = screen.get_size()
    fs = max(16, min(26, int(win_w/30)))
    df = pygame.font.SysFont('SimHei', fs)
    sf = pygame.font.SysFont('SimHei', max(14, fs-2))
    bw, bh = int(win_w*0.85), max(200, min(300, int(win_h*0.45)))
    bx, by = (win_w-bw)//2, win_h-bh-10
    box = pygame.Surface((bw, bh)); box.set_alpha(230); box.fill((0,0,0)); screen.blit(box, (bx,by))
    name = df.render(f"{npc.name}:", True, (255,215,0)); screen.blit(name, (bx+10, by+6))
    text = node["text"]
    lines=[]; cur=""
    for ch in text:
        if df.size(cur+ch)[0] <= bw-20:
            cur+=ch
        else:
            lines.append(cur); cur=ch
    if cur: lines.append(cur)
    ty = by+32
    for i in range(min(len(lines),3)):
        screen.blit(df.render(lines[i], True, (255,255,255)), (bx+10, ty+i*(fs+4)))
    opts_y = ty + 3*(fs+4) + 6
    if "options" in node and node["options"]:
        dialogue_choice_options = node["options"]
        dialogue_waiting_for_choice = True
        for i, opt in enumerate(node["options"][:4]):
            key = sf.render(f"[{i+1}]", True, (200,200,200))
            screen.blit(key, (bx+10, opts_y + i*(fs+2)))
            t = opt["text"]
            if sf.size(t)[0] > bw-70:
                while sf.size(t+"...")[0] > bw-70 and len(t)>3:
                    t = t[:-1]
                t += "..."
            screen.blit(sf.render(t, True, (255,255,200)), (bx+50, opts_y + i*(fs+2)))
        if len(node["options"])>4:
            screen.blit(sf.render("... 更多选项", True, (150,150,150)), (bx+10, opts_y+4*(fs+2)))
    else:
        dialogue_waiting_for_choice = False
        screen.blit(sf.render("[按 E 继续 / ESC 关闭]", True, (150,150,150)), (bx+10, by+bh-30))

def draw_quest_tracker(screen, tracker):
    win_w, win_h = screen.get_size()
    x, y = win_w-280, 10
    bg = pygame.Surface((270, 160)); bg.set_alpha(180); bg.fill((0,0,0)); screen.blit(bg, (x,y))
    title = font.render("任务追踪", True, (255,215,0)); screen.blit(title, (x+10, y+5))
    has_frag = tracker.get_flag("has_fragment")
    returned = tracker.get_flag("fragment_returned")
    for qid, q in tracker.quests.items():
        if qid == "find_fragment":
            if returned:
                desc = "✅ 已完成"
            elif has_frag:
                desc = "⏳ 将碎片交给引路者"
            else:
                desc = "⏳ " + q["description"]
            txt = f"{q['title']}: {desc}"
            screen.blit(font.render(txt, True, (255,255,255)), (x+10, y+30))
        else:
            status = "✅" if q["completed"] else "⏳"
            screen.blit(font.render(f"{status} {q['title']}", True, (255,255,255)), (x+10, y+30))
    if has_frag and not returned:
        screen.blit(font.render("💎 持有世界碎片", True, (255,215,0)), (x+10, y+55))

def draw_debug_info(screen):
    if not show_debug:
        return
    bg = pygame.Surface((300, 280)); bg.set_alpha(200); bg.fill((0,0,0)); screen.blit(bg, (10,10))
    line=0
    def r(t, c=(255,255,255)):
        nonlocal line
        screen.blit(font.render(t, True, c), (20, 15+line*22))
        line += 1
    r(f"FPS: {int(clock.get_fps())}", (0,255,0))
    r(f"坐标: ({cur_x//TILE}, {cur_y//TILE})")
    r(f"世界: {'红(无限)' if game_stage=='a_world' else '绿(100x100)'}")
    r(f"控制: {'AI小红' if ai_active else '小红' if game_stage=='a_world' else '小绿'}")
    q = quest_tracker
    r(f"任务: 寻找碎片 - {'✅完成' if q.get_flag('fragment_returned') else '⏳待交还' if q.get_flag('has_fragment') else '⏳寻找中'}")
    r(f"碎片: {'已拾取' if q.get_flag('has_fragment') else '已交还' if q.get_flag('fragment_returned') else '已解锁' if q.get_flag('fragment_unlocked') else '未解锁'}")
    r(f"L键计数: {l_press_count}/10")
    if crashing:
        r("💥 崩溃中...", (255,0,0))
    r(f"配置: {CONFIG_PATH}", (150,150,150))

# ==================== 主循环 ====================
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if has_returned_from_green:
                has_shutdown_warning = True
            else:
                running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F3:
                show_debug = not show_debug
                config["debug"]["show_on_start"] = show_debug
                save_config(config)
                print(f"调试 {'开启' if show_debug else '关闭'}")
            if dialogue_active and current_npc:
                if dialogue_waiting_for_choice:
                    # 处理选项1-4
                    for i in range(1,5):
                        if event.key == getattr(pygame, f'K_{i}'):
                            if len(dialogue_choice_options) >= i:
                                opt = dialogue_choice_options[i-1]
                                if opt["key"] == "return_fragment":
                                    has_frag = quest_tracker.get_flag("has_fragment")
                                    if has_frag and not quest_tracker.get_flag("fragment_returned"):
                                        current_npc.current_node = "return_fragment"
                                        quest_tracker.set_flag("has_fragment", False)
                                        quest_tracker.set_flag("fragment_returned", True)
                                        quest_tracker.complete_quest("find_fragment")
                                        print("碎片已交还！任务完成！")
                                    else:
                                        current_npc.current_node = "no_fragment"
                                    dialogue_waiting_for_choice = False
                                else:
                                    current_npc.choose_option(opt["key"])
                                    if current_npc.name == "引路者" and current_npc.current_node in ["fragment_info", "trust"]:
                                        quest_tracker.set_flag("fragment_unlocked", True)
                                    if current_npc.is_dialogue_finished():
                                        dialogue_waiting_for_choice = False
                            break
                else:
                    if event.key == pygame.K_e:
                        if current_npc.is_dialogue_finished():
                            current_npc.reset_dialogue()
                            dialogue_active = False
                            current_npc = None
                    elif event.key == pygame.K_ESCAPE:
                        current_npc.reset_dialogue()
                        dialogue_active = False
                        current_npc = None
            else:
                if event.key == pygame.K_e and game_stage == 'b_world':
                    if fragment.is_near(cur_x, cur_y) and not fragment.collected:
                        if quest_tracker.get_flag("fragment_unlocked") and not quest_tracker.get_flag("has_fragment"):
                            fragment.collect()
                            quest_tracker.set_flag("has_fragment", True)
                            print("碎片已拾取！")
                        elif quest_tracker.get_flag("has_fragment"):
                            print("已持有碎片")
                        else:
                            print("碎片被封印，需要线索")
                    else:
                        for npc in npcs:
                            if npc.is_near(cur_x, cur_y):
                                dialogue_active = True
                                current_npc = npc
                                npc.reset_dialogue()
                                if npc.name == "引路者":
                                    quest_tracker.set_flag("met_guide", True)
                                break
                if event.key == pygame.K_l:
                    if not is_transition and not crashing:
                        l_press_count += 1
                        if l_press_count >= 10:
                            crashing = True
                            crash_timer = 60
                        if game_stage == 'a_world':
                            if ai_active:
                                b_red_x, b_red_y = cur_x, cur_y
                            start_transition('b_world')
                        else:
                            b_green_x, b_green_y = cur_x, cur_y
                            start_transition('a_world')

    # ---- 崩溃 ----
    if crashing:
        crash_timer -= 1
        if crash_timer <= 0:
            pygame.quit(); sys.exit()

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
        sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = config["gameplay"]["sprint_speed"] if sprint else config["gameplay"]["player_speed"]
        if keys[pygame.K_w]: dy = -speed
        if keys[pygame.K_s]: dy = speed
        if keys[pygame.K_a]: dx = -speed
        if keys[pygame.K_d]: dx = speed

        if game_stage == 'a_world':
            if ai_active:
                move_a_ai()
                if dx != 0:
                    nx = cur_x + dx
                    if can_move_b_inf(nx, cur_y):
                        cur_x = nx
                if dy != 0:
                    ny = cur_y + dy
                    if can_move_b_inf(cur_x, ny):
                        cur_y = ny
                b_red_x, b_red_y = cur_x, cur_y
            else:
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
            pcx = (cur_x if ai_active else a_x) // (inf_map.chunk_size * TILE)
            pcy = (cur_y if ai_active else a_y) // (inf_map.chunk_size * TILE)
            inf_map.update(pcx, pcy, radius=3)
        else:
            if not dialogue_active:
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

    update_camera()

    # ---- 绘制 ----
    screen.fill((0,0,0))
    if game_stage == 'a_world':
        inf_map.draw_visible(screen, camera_x, camera_y, W, H)
        screen.blit(a_surf, (a_x - camera_x, a_y - camera_y))
    else:
        fin_map.draw(screen, camera_x, camera_y, W, H)
        if not fragment.collected:
            fragment.draw(screen, camera_x, camera_y, quest_tracker.get_flag("fragment_unlocked"))
        for npc in npcs:
            sx, sy = npc.x - camera_x, npc.y - camera_y
            pygame.draw.rect(screen, npc.color, (sx, sy, npc.size, npc.size))
            screen.blit(font.render(npc.name, True, (255,255,255)), (sx, sy-25))
            if npc.is_near(cur_x, cur_y) and not dialogue_active:
                screen.blit(font.render("[按 E 对话]", True, (255,255,200)), (sx-20, sy-50))
        if not fragment.collected and fragment.is_near(cur_x, cur_y) and not dialogue_active:
            if quest_tracker.get_flag("has_fragment"):
                screen.blit(font.render("[你已持有碎片]", True, (255,215,0)), (fragment.x-camera_x-70, fragment.y-camera_y-40))
            elif quest_tracker.get_flag("fragment_unlocked"):
                screen.blit(font.render("[按 E 拾取碎片]", True, (255,255,100)), (fragment.x-camera_x-40, fragment.y-camera_y-40))
            else:
                screen.blit(font.render("[碎片被封印]", True, (150,150,150)), (fragment.x-camera_x-50, fragment.y-camera_y-40))
    screen.blit(cur_surf, (cur_x - camera_x, cur_y - camera_y))

    # 切换动画
    if is_transition:
        alpha = 255
        half = trans_duration // 2
        if trans_progress < half:
            alpha = int(255 * (trans_progress / half))
        else:
            alpha = 255 - int(255 * ((trans_progress - half) / half))
        mask = pygame.Surface((W,H)); mask.fill((0,0,0)); mask.set_alpha(alpha); screen.blit(mask, (0,0))
        txt = font.render("=== 世界切换中 ===", True, (255,255,255))
        screen.blit(txt, txt.get_rect(center=(W//2, H//2-40)))

    if dialogue_active and current_npc:
        render_dialogue_box(screen, current_npc, quest_tracker)

    draw_quest_tracker(screen, quest_tracker)
    draw_debug_info(screen)

    # 信息栏
    terrain_names = {0:'平原',1:'山地',2:'水域',3:'森林',4:'雪山'}
    tx, ty = cur_x//TILE, cur_y//TILE
    tid = inf_map.get_tile(tx, ty) if game_stage=='a_world' else fin_map.get_tile(tx, ty)
    stage = "红世界(无限)" if game_stage=='a_world' else "绿世界(100x100)"
    if game_stage=='a_world' and ai_active:
        stage += " [AI小红]"
    elif game_stage=='a_world' and not ai_active:
        stage += " [玩家小红]"
    info = f"{stage} | ({tx},{ty}) | {terrain_names.get(tid,'未知')}"
    if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
        info += " 🏃 疾跑中"
    if quest_tracker.get_flag("has_fragment"):
        info += " 💎 持有碎片"
    if has_shutdown_warning:
        info += " ⚠️系统异常⚠️"
    if crashing:
        info += " 💥崩溃中..."
    ts = font.render(info, True, (255,255,255))
    bg = pygame.Surface((ts.get_width()+10, ts.get_height()+6)); bg.fill((0,0,0)); bg.set_alpha(200)
    screen.blit(bg, (5,5)); screen.blit(ts, (10,8))

    # 关闭警告
    if has_shutdown_warning:
        wt = warn_font.render("⚠️ 系统已被入侵，无法正常关闭！", True, (255,0,0))
        if pygame.time.get_ticks() % 800 < 400:
            screen.blit(wt, wt.get_rect(center=(W//2, H-40)))

    # 崩溃特效
    if crashing:
        if pygame.time.get_ticks() % 200 < 100:
            flash = pygame.Surface((W,H)); flash.set_alpha(150); flash.fill((255,0,0)); screen.blit(flash, (0,0))
        cf = pygame.font.SysFont('SimHei', 48)
        texts = ["⚠️ 系统崩溃 ⚠️", "ERROR 0x0001", "数据丢失", "请立即重启"]
        idx = (pygame.time.get_ticks() // 150) % len(texts)
        txt = cf.render(texts[idx], True, (255,255,255))
        screen.blit(txt, txt.get_rect(center=(W//2, H//2)))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()