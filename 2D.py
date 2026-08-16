"""
TAF Studio - BETA 4.0-snapshot4 "完整剧情引导版"

剧情流程：
  序章：红世界醒来，走向光柱 (120,120) -> 穿越到绿世界
  第一章：遇见引路者，接取"寻找世界碎片"任务 -> 碎片解锁
  第二章：前往东方祭坛 (75,75) 拾取碎片 -> 返回交还 -> 获得第二块碎片线索
  第三章：返回红世界 -> 前往遗迹 (400,400) 触发剧情 -> 前往裂缝 (600,600) 最终选择
  结局：三种结局（好/坏/隐藏）
"""

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
        "npc": {
            "guide_pos_x": 45, "guide_pos_y": 45,
            "merchant_pos_x": 60, "merchant_pos_y": 30,
            "watcher_pos_x": 30, "watcher_pos_y": 80,
            "recorder_pos_x": 16, "recorder_pos_y": 16
        },
        "locations": {
            "pillar": [120, 120],
            "ruins": [400, 400],
            "crack": [600, 600]
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 自动补全缺失的键
            for key, val in default.items():
                if key not in config:
                    config[key] = val
                elif key == "npc":
                    for k, v in default["npc"].items():
                        if k not in config["npc"]:
                            config["npc"][k] = v
                elif key == "locations":
                    for k, v in default["locations"].items():
                        if k not in config["locations"]:
                            config["locations"][k] = v
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return config
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
    default_dialogues = {
        "引路者": npc1_dialogue,
        "商人": npc2_dialogue,
        "守夜人": npc3_dialogue,
        "记录者": npc4_dialogue
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

# ==================== 地图系统 ====================
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

# ==================== 新增剧情物体 ====================
class Pillar:
    """光柱（引导玩家走向入口）"""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 60
        self.active = True
    def draw(self, screen, cam_x, cam_y):
        if not self.active:
            return
        t = pygame.time.get_ticks() / 500
        height = 60 + 20 * math.sin(t)
        # 光柱本体
        for i in range(10):
            alpha = 100 - i * 8
            width = 30 - i * 2
            y_offset = i * 6
            surf = pygame.Surface((width*2, 4), pygame.SRCALPHA)
            surf.fill((255, 255, 200, alpha))
            screen.blit(surf, (self.x - cam_x - width + 10, self.y - cam_y - height + y_offset))
        # 发光核心
        pygame.draw.circle(screen, (255, 255, 220), (int(self.x - cam_x), int(self.y - cam_y - height)), 20)
        pygame.draw.circle(screen, (255, 255, 150), (int(self.x - cam_x), int(self.y - cam_y - height)), 10)
    def is_near(self, px, py):
        return math.hypot(self.x - px, self.y - py) < self.radius

class Ruins:
    """遗迹（第二块碎片线索）"""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 60
        self.active = True
        self.triggered = False
    def draw(self, screen, cam_x, cam_y):
        if not self.active:
            return
        # 灰色石块
        rect = pygame.Rect(self.x - cam_x - 20, self.y - cam_y - 20, 40, 40)
        pygame.draw.rect(screen, (150, 150, 150), rect)
        pygame.draw.rect(screen, (100, 100, 100), rect, 2)
        # 发光符文
        t = pygame.time.get_ticks() / 300
        alpha = 150 + int(105 * math.sin(t))
        for i in range(3):
            angle = t + i * 2.1
            dx = 25 * math.cos(angle)
            dy = 25 * math.sin(angle)
            pygame.draw.circle(screen, (200, 200, 100, alpha), 
                               (int(self.x - cam_x + dx), int(self.y - cam_y + dy)), 4)
        if self.triggered:
            # 激活后显示绿色光环
            pygame.draw.circle(screen, (0, 255, 0, 100), (int(self.x - cam_x), int(self.y - cam_y)), 35, 2)
    def is_near(self, px, py):
        return math.hypot(self.x - px, self.y - py) < self.radius

class Crack:
    """世界裂缝（最终场景）"""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = 70
        self.active = True
        self.ending_triggered = False
    def draw(self, screen, cam_x, cam_y):
        if not self.active:
            return
        t = pygame.time.get_ticks() / 200
        # 紫色漩涡
        for i in range(8):
            angle = t + i * math.pi/4
            r = 25 + 15 * math.sin(t + i)
            px = self.x + r * math.cos(angle) - cam_x
            py = self.y + r * math.sin(angle) - cam_y
            pygame.draw.circle(screen, (180, 80, 255), (int(px), int(py)), 6)
        # 内部光环
        for j in range(3):
            r = 15 + 8 * math.sin(t * 1.5 + j)
            pygame.draw.circle(screen, (220, 150, 255, 80), 
                               (int(self.x - cam_x), int(self.y - cam_y)), int(r), 2)
        # 中心高亮
        pygame.draw.circle(screen, (255, 200, 255), (int(self.x - cam_x), int(self.y - cam_y)), 10)
    def is_near(self, px, py):
        return math.hypot(self.x - px, self.y - py) < self.radius

# ==================== 完整剧情对话 ====================
npc1_dialogue = {
    "start": {
        "text": "你终于来了。我一直在等一个人——一个能从红世界穿越过来的人。看来你就是那个被选中的人。",
        "options": [
            {"key": "who", "text": "你是谁？", "next": "who_am_i"},
            {"key": "mission", "text": "什么被选中的人？", "next": "mission_intro"},
            {"key": "exit", "text": "我只是路过而已。", "next": "exit_goodbye"}
        ]
    },
    "who_am_i": {
        "text": "我是这个世界的引路者。很久以前，这里叫‘融合世界’，是红与蓝交汇的地方。但现在，一切都在分裂。",
        "options": [
            {"key": "split", "text": "为什么会分裂？", "next": "mission_intro"},
            {"key": "exit", "text": "我明白了。", "next": "exit_goodbye"}
        ]
    },
    "mission_intro": {
        "text": "两个世界正在逐渐分离。如果继续这样下去，红世界和绿世界都会崩塌。只有找回三块世界碎片，才能重新缝合它们。",
        "options": [
            {"key": "fragment1", "text": "第一块碎片在哪里？", "next": "fragment_info"},
            {"key": "doubt", "text": "我怎么知道你说的是真的？", "next": "trust_check"},
            {"key": "exit", "text": "我再想想。", "next": "exit_goodbye"}
        ]
    },
    "fragment_info": {
        "text": "第一块碎片就在绿世界东方的祭坛上。那里曾经是两界交汇的中心，现在只剩下一块发光的石头。你拿到它，就知道我没有说谎。",
        "options": [
            {"key": "ok", "text": "好，我这就去找。", "next": "quest_accepted"},
            {"key": "exit", "text": "我还没准备好。", "next": "exit_goodbye"}
        ]
    },
    "quest_accepted": {
        "text": "去吧。记住：碎片会回应你的意志。你越是渴望找到它，它就越容易显现在你面前。",
        "options": []
    },
    "trust_check": {
        "text": "你不需要相信我。等你找到了碎片，自然会明白。",
        "options": [
            {"key": "ok", "text": "好吧，我去看看。", "next": "quest_accepted"},
            {"key": "exit", "text": "我还没准备好。", "next": "exit_goodbye"}
        ]
    },
    "return_fragment": {
        "text": "太好了！这就是第一块碎片——‘融合之核’。你做得很好。现在，第二块碎片在红世界深处的遗迹里，坐标大约在 (400, 400)。那里有一块古老的石碑，上面记载着碎片的秘密。",
        "options": [
            {"key": "thanks", "text": "谢谢你，我这就去。", "next": "next_quest"},
            {"key": "ask_more", "text": "我该怎么找到遗迹？", "next": "ruins_hint"}
        ]
    },
    "ruins_hint": {
        "text": "从你来的地方——红世界——一直往深处走。你会看到一片被遗忘的废墟。那里就是遗迹。",
        "options": [
            {"key": "thanks", "text": "明白了。", "next": "next_quest"}
        ]
    },
    "next_quest": {
        "text": "我已经完成了我的使命。接下来，你要靠自己了。记住：碎片之间会互相感应，你手中的碎片会指引你找到下一个。",
        "options": []
    },
    "no_fragment": {
        "text": "你还没有碎片。空手而归可不是什么好兆头。",
        "options": [
            {"key": "ok", "text": "好吧，我再去找找。", "next": "start"}
        ]
    },
    "exit_goodbye": {
        "text": "你可以随时回来。但记住——时间不多了。",
        "options": []
    }
}

npc2_dialogue = {
    "start": {
        "text": "嘿，旅行者！我在这破地方待了三年，你是第一个活人。要不要看看我收藏的‘真正的宝贝’？",
        "options": [
            {"key": "yes", "text": "好啊，什么宝贝？", "next": "goods"},
            {"key": "no", "text": "不用了，我不需要。", "next": "no_thanks"},
            {"key": "info", "text": "你听说过世界碎片吗？", "next": "fragment_info"}
        ]
    },
    "goods": {
        "text": "我有一只‘会说话’的镜子，一个能预知未来的沙漏，还有……（压低声音）一张通往红世界深处的藏宝图。你想要哪个？",
        "options": [
            {"key": "map", "text": "藏宝图我感兴趣。", "next": "map_quest"},
            {"key": "skeptic", "text": "你这些东西看起来全是假的。", "next": "skeptic_response"},
            {"key": "exit", "text": "我改主意了，算了。", "next": "no_thanks"}
        ]
    },
    "map_quest": {
        "text": "明智的选择。这张地图标注了红世界深处一座遗迹的位置——据说那里面藏着第二块世界碎片。不过，我可不是白送的。你要帮我做一件事。",
        "options": [
            {"key": "what", "text": "什么事？", "next": "map_task"},
            {"key": "decline", "text": "那算了，我没时间。", "next": "no_thanks"}
        ]
    },
    "map_task": {
        "text": "绿世界北边有个‘守夜人’，他欠我一样东西——一块黑色的石头。你去帮我拿回来，这张地图就是你的了。",
        "options": [
            {"key": "accept", "text": "成交！", "next": "quest_accept"},
            {"key": "decline", "text": "太麻烦了，不干。", "next": "no_thanks"}
        ]
    },
    "quest_accept": {
        "text": "很好！找到守夜人，告诉他‘商人托你来的’。他会明白的。",
        "options": []
    },
    "skeptic_response": {
        "text": "假的？哈哈，你最好希望这些都是假的。因为如果它们是真的，那这个世界就比你想的更疯狂。",
        "options": [
            {"key": "ok", "text": "……好吧。", "next": "no_thanks"}
        ]
    },
    "fragment_info": {
        "text": "碎片？你也在找碎片？呵，看来引路者那老家伙没少忽悠人。不过……我确实听说过第三块碎片的消息。它在‘裂缝’里。",
        "options": [
            {"key": "tell_me", "text": "裂缝在哪里？", "next": "crack_hint"},
            {"key": "exit", "text": "谢了，我该走了。", "next": "no_thanks"}
        ]
    },
    "crack_hint": {
        "text": "裂缝没有固定的位置。它会在两界之间游走。你唯一能做的，就是带着碎片去感应它。我猜，它可能出现在红世界深处某个地方。",
        "options": [
            {"key": "thanks", "text": "明白了，谢谢。", "next": "no_thanks"}
        ]
    },
    "no_thanks": {
        "text": "好吧，祝你好运。如果你改变主意，我还在老地方。",
        "options": []
    }
}

npc3_dialogue = {
    "start": {
        "text": "你身上有引路者的气息……也有碎片的气味。你是什么人？",
        "options": [
            {"key": "traveler", "text": "我只是路过这里。", "next": "suspicious"},
            {"key": "fragment", "text": "我在找世界碎片。", "next": "fragment_seeker"},
            {"key": "merchant", "text": "商人托我来找你要一样东西。", "next": "merchant_quest"}
        ]
    },
    "suspicious": {
        "text": "路过？呵，这片区域没有‘路过’这种说法。你来这里，总有原因。",
        "options": [
            {"key": "truth", "text": "好吧，我在找世界碎片。", "next": "fragment_seeker"},
            {"key": "lie", "text": "真的只是路过。", "next": "exit_goodbye"}
        ]
    },
    "fragment_seeker": {
        "text": "又一个寻找碎片的人……你已经拿到了第一块吧？我感应到你身上有融合之核的气息。听着，第二块碎片确实在红世界深处，但你找不到入口——除非你有引路者的指引。",
        "options": [
            {"key": "guide", "text": "引路者让我来找你？", "next": "guide_connection"},
            {"key": "exit", "text": "我自己也能找到。", "next": "exit_goodbye"}
        ]
    },
    "guide_connection": {
        "text": "他……他还记得我。很久以前，我们三个人——我、引路者、商人——曾经试图修复这个世界。但失败了。我们各自选择了不同的道路。",
        "options": [
            {"key": "what_happened", "text": "发生了什么？", "next": "past_story"},
            {"key": "exit", "text": "我不想深究。", "next": "exit_goodbye"}
        ]
    },
    "past_story": {
        "text": "那是一次失败的仪式。我们试图用三块碎片缝合两界，但最后一块碎片——也就是‘裂缝之核’——在仪式中消失了。从那天起，裂缝开始扩大。",
        "options": [
            {"key": "where", "text": "碎片消失在哪里了？", "next": "crack_location"},
            {"key": "exit", "text": "这太沉重了。", "next": "exit_goodbye"}
        ]
    },
    "crack_location": {
        "text": "裂缝之核的最后一次出现，是在红世界的坐标 (600, 600) 附近。但那里已经变成了混沌区——没有地图，没有方向，只有混乱。",
        "options": [
            {"key": "thanks", "text": "谢谢你告诉我这些。", "next": "exit_goodbye"}
        ]
    },
    "merchant_quest": {
        "text": "商人？他还欠我一条命呢！……算了，那块石头给你。告诉商人，这次我不跟他计较，但下次见面，他最好亲自来见我。",
        "options": [
            {"key": "take", "text": "我替他谢谢你了。", "next": "stone_received"},
            {"key": "exit", "text": "我会转告他的。", "next": "exit_goodbye"}
        ]
    },
    "stone_received": {
        "text": "拿着吧，这块石头可以指引你找到第三块碎片的位置。不要弄丢了。",
        "options": []
    },
    "exit_goodbye": {
        "text": "愿你找到你想要的答案。",
        "options": []
    }
}

npc4_dialogue = {
    "start": {
        "text": "哦？你居然走到了这里。很少有人能找到我。你在找碎片？还是……在找答案？",
        "options": [
            {"key": "answer", "text": "我在找答案。", "next": "answer_path"},
            {"key": "fragment", "text": "我在找碎片。", "next": "fragment_hint"},
            {"key": "who_are_you", "text": "你是谁？", "next": "who_am_i_recorder"}
        ]
    },
    "who_am_i_recorder": {
        "text": "我是记录者。这个世界的创造者——是的，你没有听错。这里的一切都是我写的代码。可惜……我的造物们开始失控了。",
        "options": [
            {"key": "wait", "text": "等等，你是说这个世界是假的？", "next": "reality_check"},
            {"key": "exit", "text": "我接受不了这个。", "next": "exit_goodbye"}
        ]
    },
    "reality_check": {
        "text": "你觉得‘真实’是什么意思？你面前的屏幕、你手里的键盘、你玩的游戏……不也是代码吗？",
        "options": [
            {"key": "philosophy", "text": "所以你也像我一样被困在里面？", "next": "recorder_trap"},
            {"key": "exit", "text": "我得走了。", "next": "exit_goodbye"}
        ]
    },
    "recorder_trap": {
        "text": "不，我是自愿留在这里的。这个世界是我创造的故事，我想看着它完成。但你需要完成你自己的故事。",
        "options": [
            {"key": "how", "text": "我怎么才能完成它？", "next": "final_hint"},
            {"key": "exit", "text": "……我该走了。", "next": "exit_goodbye"}
        ]
    },
    "final_hint": {
        "text": "找到三块碎片，然后去裂缝的中心。那里……（微笑）有一扇门。",
        "options": [
            {"key": "thanks", "text": "谢谢。", "next": "exit_goodbye"}
        ]
    },
    "fragment_hint": {
        "text": "碎片会找到你的——只要你想找到它们。记住：碎片不是死物，它们会回应你的意志。",
        "options": [
            {"key": "thanks", "text": "我会记住的。", "next": "exit_goodbye"}
        ]
    },
    "answer_path": {
        "text": "答案不是别人给你的。你会在旅途中找到它。",
        "options": [
            {"key": "ok", "text": "我明白了。", "next": "exit_goodbye"}
        ]
    },
    "exit_goodbye": {
        "text": "去吧，旅行者。故事还在继续。",
        "options": []
    }
}

# ==================== 任务追踪器 ====================
class QuestTracker:
    def __init__(self):
        self.quests = {}
        self.flags = {}
        self.set_flag("fragment_unlocked", False)
        self.set_flag("has_fragment", False)
        self.set_flag("fragment_returned", False)
        self.set_flag("merchant_quest_accept", False)
        self.set_flag("stone_received", False)
        self.set_flag("met_recorder", False)
        self.set_flag("final_unlocked", False)
        self.set_flag("ruins_triggered", False)
    def add_quest(self, qid, title, desc):
        self.quests[qid] = {"title": title, "description": desc, "completed": False}
    def complete_quest(self, qid):
        if qid in self.quests:
            self.quests[qid]["completed"] = True
    def set_flag(self, name, value=True):
        self.flags[name] = value
    def get_flag(self, name, default=False):
        return self.flags.get(name, default)

# ==================== 主程序 ====================
def main():
    config = load_config()
    W = config["window"]["width"]
    H = config["window"]["height"]
    TILE = 32

    dialogues = load_dialogues(config)
    npc1_dialogue_loaded = dialogues["引路者"]
    npc2_dialogue_loaded = dialogues["商人"]
    npc3_dialogue_loaded = dialogues["守夜人"]
    npc4_dialogue_loaded = dialogues["记录者"]

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("TAF Studio - 完整剧情引导版")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('SimHei', 20)
    dialogue_font = pygame.font.SysFont('SimHei', 22)
    warn_font = pygame.font.SysFont('SimHei', 28)

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

    # NPC
    guide_x = config["npc"]["guide_pos_x"] * TILE
    guide_y = config["npc"]["guide_pos_y"] * TILE
    merchant_x = config["npc"]["merchant_pos_x"] * TILE
    merchant_y = config["npc"]["merchant_pos_y"] * TILE
    watcher_x = config["npc"]["watcher_pos_x"] * TILE
    watcher_y = config["npc"]["watcher_pos_y"] * TILE
    recorder_x = config["npc"]["recorder_pos_x"] * TILE
    recorder_y = config["npc"]["recorder_pos_y"] * TILE

    npc1 = NPC(guide_x, guide_y, "引路者", npc1_dialogue_loaded, (255,215,0))
    npc2 = NPC(merchant_x, merchant_y, "商人", npc2_dialogue_loaded, (0,200,255))
    npc3 = NPC(watcher_x, watcher_y, "守夜人", npc3_dialogue_loaded, (100,100,255))
    npc4 = NPC(recorder_x, recorder_y, "记录者", npc4_dialogue_loaded, (200,100,255))
    npcs = [npc1, npc2, npc3, npc4]

    # 碎片
    frag_x = config["fragment"]["position_x"] * TILE
    frag_y = config["fragment"]["position_y"] * TILE
    fragment = Fragment(frag_x, frag_y)

    # 剧情物体
    pillar_pos = config["locations"]["pillar"]
    ruins_pos = config["locations"]["ruins"]
    crack_pos = config["locations"]["crack"]
    pillar = Pillar(pillar_pos[0]*TILE, pillar_pos[1]*TILE)
    ruins = Ruins(ruins_pos[0]*TILE, ruins_pos[1]*TILE)
    crack = Crack(crack_pos[0]*TILE, crack_pos[1]*TILE)

    # 任务追踪器
    quest_tracker = QuestTracker()
    quest_tracker.add_quest("find_fragment", "寻找世界碎片", "从东方祭坛取回世界碎片")
    quest_tracker.set_flag("met_guide", False)

    # 世界状态
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

    # 剧情阶段
    story_stage = 0  # 0=序章, 1=第一章, 2=第二章, 3=第三章, 4=结局
    ending_shown = False
    ending_text = ""
    ending_timer = 0

    # ==================== 辅助函数 ====================
    def update_camera():
        nonlocal camera_x, camera_y
        tx = cur_x - W//2 + PLAYER_SIZE//2
        ty = cur_y - H//2 + PLAYER_SIZE//2
        if game_stage == 'b_world':
            tx = max(0, min(tx, fin_map.width*TILE - W))
            ty = max(0, min(ty, fin_map.height*TILE - H))
        camera_x, camera_y = tx, ty

    def start_transition(target):
        nonlocal is_transition, trans_progress, _target_stage
        if not is_transition:
            is_transition = True
            trans_progress = 0
            _target_stage = target

    def trigger_switch():
        nonlocal game_stage, cur_x, cur_y, cur_surf, ai_active, has_returned_from_green, has_shutdown_warning, story_stage
        target = _target_stage
        if target == 'b_world' or (target is None and game_stage == 'a_world'):
            game_stage = 'b_world'
            cur_x, cur_y = b_green_x, b_green_y
            cur_surf = b_surf
            ai_active = False
            if story_stage == 0:
                story_stage = 1
                print("📖 第一章：绿世界，引路者")
        else:
            game_stage = 'a_world'
            nonlocal b_red_x, b_red_y
            if b_red_x is None:
                b_red_x, b_red_y = a_x + 40, a_y + 40
            cur_x, cur_y = b_red_x, b_red_y
            cur_surf = b_surf
            ai_active = True
            has_returned_from_green = True
            has_shutdown_warning = False
            if story_stage == 2:
                story_stage = 3
                print("📖 第三章：返回红世界，寻找遗迹")

    def check_events():
        nonlocal story_stage, ending_shown, ending_text, ending_timer
        # 1. 光柱触发（序章）
        if game_stage == 'a_world' and not is_transition and not ai_active and story_stage == 0:
            if pillar.is_near(a_x, a_y):
                print("📖 序章完成：穿越到绿世界")
                start_transition('b_world')
                pillar.active = False

        # 2. 遗迹触发（第二章结束，第三章）
        if game_stage == 'a_world' and ai_active and story_stage == 3:
            if ruins.is_near(cur_x, cur_y) and not ruins.triggered:
                # 触发遗迹剧情
                ruins.triggered = True
                quest_tracker.set_flag("ruins_triggered", True)
                quest_tracker.add_quest("find_third", "寻找第三块碎片", "前往世界裂缝 (600,600)")
                print("📖 遗迹激活：第三块碎片在裂缝中")
                # 可以直接弹出对话提示（或显示消息）
                # 这里简单用print，也可以扩展为对话窗口
                # 给玩家一些反馈
                ending_text = "遗迹中浮现一行文字：'第三块碎片隐藏在裂缝深处，坐标 (600, 600)'"
                ending_timer = 180  # 显示3秒

        # 3. 裂缝触发（结局）
        if game_stage == 'a_world' and ai_active and story_stage == 3:
            if crack.is_near(cur_x, cur_y) and not crack.ending_triggered:
                crack.ending_triggered = True
                story_stage = 4
                # 触发结局选择（这里简化，直接进入好结局）
                # 实际可以做成对话选择，但为了演示，我们直接播放好结局
                ending_shown = True
                ending_text = "你走进裂缝，用三块碎片缝合了两界。世界重归完整。\n\n—— 好结局 ——"
                print("🎉 好结局达成！")

    def move_a_ai():
        nonlocal a_x, a_y, ai_target_x, ai_target_y
        if ai_target_x is None or ai_target_y is None or math.hypot(a_x-ai_target_x, a_y-ai_target_y) < 20:
            if story_stage == 3 and game_stage == 'a_world':
                # 第三章：走向遗迹 (400,400) 然后走向裂缝 (600,600)
                if not ruins.triggered:
                    ai_target_x = ruins_pos[0] * TILE
                    ai_target_y = ruins_pos[1] * TILE
                else:
                    ai_target_x = crack_pos[0] * TILE
                    ai_target_y = crack_pos[1] * TILE
            else:
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
        nonlocal dialogue_choice_options, dialogue_waiting_for_choice
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
        bg = pygame.Surface((270, 180)); bg.set_alpha(180); bg.fill((0,0,0)); screen.blit(bg, (x,y))
        title = font.render("任务追踪", True, (255,215,0)); screen.blit(title, (x+10, y+5))
        has_frag = tracker.get_flag("has_fragment")
        returned = tracker.get_flag("fragment_returned")
        y_offset = 30
        for qid, q in tracker.quests.items():
            if qid == "find_fragment":
                if returned:
                    desc = "✅ 已完成"
                elif has_frag:
                    desc = "⏳ 将碎片交给引路者"
                else:
                    desc = "⏳ " + q["description"]
                txt = f"{q['title']}: {desc}"
                screen.blit(font.render(txt, True, (255,255,255)), (x+10, y+y_offset))
                y_offset += 25
            else:
                status = "✅" if q["completed"] else "⏳"
                txt = f"{status} {q['title']}"
                screen.blit(font.render(txt, True, (255,255,255)), (x+10, y+y_offset))
                y_offset += 25
        if has_frag and not returned:
            screen.blit(font.render("💎 持有世界碎片", True, (255,215,0)), (x+10, y+y_offset))
        # 显示目标指引（第三章）
        if tracker.get_flag("ruins_triggered") and not tracker.get_flag("final_unlocked"):
            screen.blit(font.render("→ 前往裂缝 (600,600)", True, (200,200,255)), (x+10, y+y_offset+25))
        elif story_stage == 3 and not tracker.get_flag("ruins_triggered"):
            screen.blit(font.render("→ 前往遗迹 (400,400)", True, (200,200,255)), (x+10, y+y_offset+25))

    def draw_debug_info(screen):
        if not show_debug:
            return
        bg = pygame.Surface((350, 330)); bg.set_alpha(200); bg.fill((0,0,0)); screen.blit(bg, (10,10))
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
        story_names = ["序章", "第一章", "第二章", "第三章", "结局"]
        r(f"剧情: {story_names[story_stage] if story_stage < 5 else '?'}")
        if crashing:
            r("💥 崩溃中...", (255,0,0))
        r(f"配置: {CONFIG_PATH}", (150,150,150))

    # ==================== 主循环 ====================
    running = True
       # ==================== 主循环 ====================
    running = True
    while running:
        for event in pygame.event.get():
            # ---- 结局画面：按任意键退出（最高优先级） ----
            if ending_shown:
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    running = False
                continue  # 结局状态下不处理任何其他事件

            # ---- 窗口关闭 ----
            if event.type == pygame.QUIT:
                if has_returned_from_green:
                    has_shutdown_warning = True
                else:
                    running = False

            # ---- 键盘事件 ----
            if event.type == pygame.KEYDOWN:
                # F3 调试
                if event.key == pygame.K_F3:
                    show_debug = not show_debug
                    config["debug"]["show_on_start"] = show_debug
                    save_config(config)
                    print(f"调试 {'开启' if show_debug else '关闭'}")

                # ---- 对话处理 ----
                if dialogue_active and current_npc:
                    if dialogue_waiting_for_choice:
                        for i in range(1, 5):
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
                                            story_stage = 2
                                            print("📖 第二章：碎片已交还，寻找第二块碎片")
                                        else:
                                            current_npc.current_node = "no_fragment"
                                        dialogue_waiting_for_choice = False
                                    else:
                                        current_npc.choose_option(opt["key"])
                                        if current_npc.name == "引路者" and current_npc.current_node in ["fragment_info", "trust_check"]:
                                            quest_tracker.set_flag("fragment_unlocked", True)
                                        if current_npc.name == "商人" and opt["key"] == "accept":
                                            quest_tracker.set_flag("merchant_quest_accept", True)
                                        if current_npc.name == "守夜人" and opt["key"] == "take":
                                            quest_tracker.set_flag("stone_received", True)
                                        if current_npc.name == "记录者":
                                            quest_tracker.set_flag("met_recorder", True)
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

                # ---- 非对话状态的按键 ----
                else:
                    # E 键交互（碎片/NPC/遗迹/裂缝）
                    if event.key == pygame.K_e:
                        if game_stage == 'b_world':
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
                        elif game_stage == 'a_world':
                            if ai_active:
                                if ruins.is_near(cur_x, cur_y) and not ruins.triggered:
                                    ruins.triggered = True
                                    quest_tracker.set_flag("ruins_triggered", True)
                                    quest_tracker.add_quest("find_third", "寻找第三块碎片", "前往世界裂缝 (600,600)")
                                    print("遗迹激活")
                                elif crack.is_near(cur_x, cur_y) and not crack.ending_triggered:
                                    crack.ending_triggered = True
                                    story_stage = 4
                                    ending_shown = True
                                    ending_text = "你走进裂缝，用三块碎片缝合了两界。世界重归完整。\n\n—— 好结局 ——"
                                    print("好结局达成！")

                    # L 键切换世界
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
                    # 事件检测（AI移动中）
                    check_events()
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
                    check_events()
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
            # 绘制光柱（如果未消失）
            pillar.draw(screen, camera_x, camera_y)
            # 绘制遗迹
            ruins.draw(screen, camera_x, camera_y)
            # 绘制裂缝
            crack.draw(screen, camera_x, camera_y)
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

        # ---- 切换动画 ----
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

        # ---- 对话界面 ----
        if dialogue_active and current_npc:
            render_dialogue_box(screen, current_npc, quest_tracker)

        # ---- 任务追踪器 ----
        draw_quest_tracker(screen, quest_tracker)

        # ---- 调试面板 ----
        draw_debug_info(screen)

        # ---- 信息栏 ----
        terrain_names = {0:'平原',1:'山地',2:'水域',3:'森林',4:'雪山'}
        tx, ty = cur_x//TILE, cur_y//TILE
        tid = inf_map.get_tile(tx, ty) if game_stage=='a_world' else fin_map.get_tile(tx, ty)
        stage = "红世界(无限)" if game_stage=='a_world' else "绿世界(100x100)"
        if game_stage=='a_world' and ai_active:
            stage += " [AI小红]"
        elif game_stage=='a_world' and not ai_active:
            stage += " [玩家小红]"
        story_names = ["序章", "第一章", "第二章", "第三章", "结局"]
        info = f"{stage} | ({tx},{ty}) | {terrain_names.get(tid,'未知')} | 📖{story_names[story_stage] if story_stage < 5 else '?'}"
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

        # ---- 结局画面 ----
        if ending_shown:
            # 半透明黑色覆盖
            overlay = pygame.Surface((W,H))
            overlay.set_alpha(200)
            overlay.fill((0,0,0))
            screen.blit(overlay, (0,0))
            # 结束文字
            lines = ending_text.split('\n')
            for i, line in enumerate(lines):
                txt = font.render(line, True, (255,255,255))
                screen.blit(txt, txt.get_rect(center=(W//2, H//2 - 30 + i*40)))
            # 提示
            hint = font.render("按任意键退出", True, (200,200,200))
            screen.blit(hint, hint.get_rect(center=(W//2, H//2 + 80)))
            # 简单处理退出：按任意键关闭
            # 但为了不干扰事件循环，在事件中检测

        # ---- 关闭警告 ----
        if has_shutdown_warning:
            wt = warn_font.render("⚠️ 系统已被入侵，无法正常关闭！", True, (255,0,0))
            if pygame.time.get_ticks() % 800 < 400:
                screen.blit(wt, wt.get_rect(center=(W//2, H-40)))

        # ---- 崩溃特效 ----
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

if __name__ == "__main__":
    main()