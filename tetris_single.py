import pygame
import random
import sys
import time
import os
import numpy as np
import moderngl

# --- OpenGL Fisheye Shader Setup ---
FISHEYE_VERTEX_SHADER = '''
    #version 330
    in vec2 vert;
    in vec2 in_text;
    out vec2 v_text;
    void main() {
        gl_Position = vec4(vert, 0.0, 1.0);
        v_text= in_text;
    }
'''

FISHEYE_FRAGMENT_SHADER = '''
    #version 330
    uniform sampler2D Texture;
    uniform sampler2D BgTexture;
    uniform float distortion;
    in vec2 v_text;
    out vec4 f_color;
    void main() {
        // CRT curvature
        vec2 curved = v_text - 0.5;
        curved *= 1.0 + 0.18 * (curved.x * curved.x + curved.y * curved.y);
        vec2 crt_uv = curved + 0.5;

        vec2 uv = crt_uv * 2.0 - 1.0;
        float r2 = dot(uv, uv);
        float denom = 1.0 - distortion * r2;
        if (denom > 0.0) {
            uv = uv / denom;
        }
        vec2 texcoord = (uv + 1.0) / 2.0;

        vec4 color;
        if (texcoord.x < 0.0 || texcoord.x > 1.0 || texcoord.y < 0.0 || texcoord.y > 1.0) {
            color = texture(BgTexture, crt_uv);
        } else {
            color = texture(Texture, texcoord);
        }

        // Vignette (ciemniejsze rogi)
        float vignette = smoothstep(0.8, 0.2, length(curved));
        color.rgb *= vignette;

        f_color = color;
    }
'''

def setup_fisheye_gl(screen_size):
    ctx = moderngl.create_context()
    prog = ctx.program(
        vertex_shader=FISHEYE_VERTEX_SHADER,
        fragment_shader=FISHEYE_FRAGMENT_SHADER
    )
    vertices = np.array([
        -1, -1, 0, 0,
         1, -1, 1, 0,
        -1,  1, 0, 1,
         1,  1, 1, 1,
    ], dtype='f4')
    vbo = ctx.buffer(vertices.tobytes())
    vao = ctx.simple_vertex_array(prog, vbo, 'vert', 'in_text')
    texture = ctx.texture(screen_size, 3)
    texture.repeat_x = False
    texture.repeat_y = False
    return ctx, prog, vao, texture


def render_fisheye_gl(ctx, prog, vao, texture, surface, distortion=0.08):
    arr = pygame.image.tostring(pygame.transform.flip(surface, False, True), "RGB")
    texture.write(arr)
    ctx.clear()
    prog['distortion'].value = distortion
    texture.use(location=0)
    crt_texture.use(location=1)
    prog['Texture'].value = 0
    prog['BgTexture'].value = 1
    vao.render(moderngl.TRIANGLE_STRIP)
    pygame.display.flip()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller ustawia tę zmienną
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)



# Inicjalizacja
pygame.init()
pygame.mixer.init()
try:
    pygame.mixer.music.load(resource_path("theme.mp3"))
    pygame.mixer.music.play(-1)
    drop_sound = pygame.mixer.Sound(resource_path("drop.mp3"))
    clear_sound = pygame.mixer.Sound(resource_path("clear.mp3"))
except Exception as e:
    print("Nie można załadować muzyki:", e)
    drop_sound = None 
    clear_sound = None 

# Czcionki
try:
    tetris_font_path = resource_path("Tetris.ttf")
    title_font = pygame.font.Font(tetris_font_path, 100)
    menu_font = pygame.font.Font(tetris_font_path, 50)
    score_font = pygame.font.Font(tetris_font_path, 30)
except Exception:
    title_font = pygame.font.SysFont('comicsans', 70)
    menu_font = pygame.font.SysFont('comicsans', 50)
    score_font = pygame.font.SysFont('comicsans', 30)

# Stałe
GRID_SIZE = 56
GRID_WIDTH = 10
GRID_HEIGHT = 20
SIDEBAR_WIDTH = 400
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

# Kolory
GB_BG      = (220, 200, 255)   # Jasny fiolet (tło)
GB_GRID    = (120, 80, 180)    # Ciemny fiolet (kratka)
GB_BLOCK   = (180, 120, 220)   # Fiolet (klocki)
GB_ACCENT  = (70, 30, 100)     # Najciemniejszy fiolet (obramowania, tekst)
RED        = GB_ACCENT

WHITE = GB_BG
BLACK = GB_ACCENT
GRAY = GB_GRID
DARK_GRAY = GB_ACCENT
HIGHLIGHT = GB_BLOCK

COLORS = [
    (180, 120, 220),  # I - jasny fiolet
    (160, 100, 200),  # O - średni fiolet
    (140, 80, 180),   # T - ciemniejszy fiolet
    (200, 140, 240),  # L - różowawy fiolet
    (120, 60, 160),   # J - głęboki fiolet
    (170, 110, 210),  # S - pastelowy fiolet
    (150, 90, 190),   # Z - klasyczny fiolet
]

# Kształty klocków
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 1], [1, 0, 0]],  # L
    [[1, 1, 1], [0, 0, 1]],  # J
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]]   # Z
]

# Konfiguracja ekranu
screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
fisheye_ctx, fisheye_prog, fisheye_vao, fisheye_texture = setup_fisheye_gl((SCREEN_WIDTH, SCREEN_HEIGHT))

crt_image = pygame.image.load(resource_path("crt.png")).convert()
crt_image = pygame.transform.scale(crt_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
crt_image = pygame.transform.flip(crt_image, False, True)  # <-- odwrócenie w pionie
crt_texture = fisheye_ctx.texture((SCREEN_WIDTH, SCREEN_HEIGHT), 3, pygame.image.tostring(crt_image, "RGB"))
crt_texture.build_mipmaps()

clock = pygame.time.Clock()
FPS = 60


# Funkcja do dynamicznego centrowania planszy:
def get_margins():
    win_w, win_h = pygame.display.get_surface().get_size()
    margin_left = (win_w - (SIDEBAR_WIDTH + GRID_WIDTH * GRID_SIZE + SIDEBAR_WIDTH)) // 2 + SIDEBAR_WIDTH
    margin_top = (win_h - GRID_HEIGHT * GRID_SIZE) // 2
    return margin_left, margin_top

class Block:
    def __init__(self, x, y, shape, color=None):
        self.x = x
        self.y = y
        self.shape = shape
        if color is None:
            self.color = COLORS[SHAPES.index(shape)]
        else:
            self.color = color
        self.rotation = 0

def _apply_scanlines(screen):
    width, height = screen.get_size()
    scanline_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    for y in range(0, height, 4):
        pygame.draw.line(scanline_surface, (0, 0, 0, 60), (0, y), (width, y))

    screen.blit(scanline_surface, (0, 0))

def _apply_pixelation(screen, pixelation):
    pixelation = {"minimum": 2, "medium": 4, "maximum": 6}.get(pixelation, 2)
    width, height = screen.get_size()
    # Zmniejsz obraz, a potem powiększ z powrotem, uzyskując efekt pikselizacji
    small_surf = pygame.transform.scale(screen, (width // pixelation, height // pixelation))
    screen.blit(pygame.transform.scale(small_surf, (width, height)), (0, 0))

def _apply_flicker(screen):
    if random.randint(0, 20) == 0:
        flicker_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        flicker_surface.fill((0, 0, 0, 10))
        screen.blit(flicker_surface, (0, 0))

def _apply_glow(screen):
    width, height = screen.get_size()
    glow_surf = pygame.transform.smoothscale(screen, (width // 4, height // 4))
    glow_surf = pygame.transform.smoothscale(glow_surf, (width, height))
    glow_surf.set_alpha(100)
    screen.blit(glow_surf, (0, 0))
    screen.blit(glow_surf, (0, 0))

def _add_glitch_effect(height, width, glitch_surface, intensity):
    shift_amount = {"minimum": 10, "medium": 20, "maximum": 40}.get(intensity, 20)
    if random.random() < 0.1:
        y_start = random.randint(0, height - 20)
        slice_height = random.randint(5, 20)
        offset = random.randint(-shift_amount, shift_amount)

        slice_area = pygame.Rect(0, y_start, width, slice_height)
        slice_copy = glitch_surface.subsurface(slice_area).copy()
        glitch_surface.blit(slice_copy, (offset, y_start))

def _add_rolling_static(screen, height, width, intensity):
    # Zmniejsz szansę na pojawienie się linii i zwiększ odstęp
    static_chance = {"minimum": 0.03, "medium": 0.08, "maximum": 0.18}.get(intensity, 0.05)
    static_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # Większy odstęp = mniej linii, np. co 24 piksele
    for y in range(0, height, 24):
        if random.random() < static_chance:
            alpha = random.randint(8, 24)  # subtelniejsza przezroczystość
            color = (177, 177, 177, alpha)
            pygame.draw.line(static_surface, color, (0, y), (width, y))

    screen.blit(static_surface, (0, 0), special_flags=pygame.BLEND_ADD)


class Game:
    def __init__(self):
        self.reset_game()
        self.hold_block = None
        self.hold_used = False 
        
    def reset_game(self):
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_block = self.new_block()
        self.next_block = self.new_block()
        self.hold_block = None
        self.hold_used = False
        self.game_over = False
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.fall_speed = 2.8
        
        
    def new_block(self):
        shape = random.choice(SHAPES)
        return Block(GRID_WIDTH // 2 - len(shape[0]) // 2, 0, shape)
    
    def valid_move(self, block, x_offset=0, y_offset=0):
        for y, row in enumerate(block.shape):
            for x, cell in enumerate(row):
                if cell:
                    new_x = block.x + x + x_offset
                    new_y = block.y + y + y_offset
                    if (new_x < 0 or new_x >= GRID_WIDTH or 
                        new_y >= GRID_HEIGHT or 
                        (new_y >= 0 and self.grid[new_y][new_x])):
                        return False
        return True
    
    def rotate_block(self):
        rotated = [list(row) for row in zip(*self.current_block.shape[::-1])]
        old_shape = self.current_block.shape
        self.current_block.shape = rotated
        if not self.valid_move(self.current_block):
            self.current_block.shape = old_shape
    
    def hold_current_block(self):
        # Pozwala na zamianę tylko raz na jeden klocek spadający
        if self.hold_used:
            return  # Nie pozwól na kolejną zamianę w tej turze

        prev_x = self.current_block.x
        prev_y = self.current_block.y
        if self.hold_block is None:
            new_block = Block(
                GRID_WIDTH // 2 - len(self.current_block.shape[0]) // 2,
                0,
                [row[:] for row in self.current_block.shape],
                self.current_block.color
            )
            self.hold_block = new_block
            self.current_block = self.next_block
            self.next_block = self.new_block()
        else:
            temp = self.current_block
            # Ustaw blok na środku planszy
            new_block = Block(
                GRID_WIDTH // 2 - len(self.hold_block.shape[0]) // 2,
                0,
                [row[:] for row in self.hold_block.shape],
                self.hold_block.color
            )
            # Korekta pozycji w lewo/prawo jeśli blok wystaje poza planszę
            while not self.valid_move(new_block):
                new_block.x -= 1
                if new_block.x < 0:
                    new_block.x = 0
                    break
            self.current_block = new_block
            self.hold_block = Block(
                GRID_WIDTH // 2 - len(temp.shape[0]) // 2,
                0,
                [row[:] for row in temp.shape],
                temp.color
            )
        self.hold_used = True

        # Dodatkowa korekta: jeśli po zamianie blok nadal wystaje, przesuń go w górę
        while not self.valid_move(self.current_block):
            self.current_block.y -= 1
            if self.current_block.y < 0:
                break
 
    def lock_block(self):
        for y, row in enumerate(self.current_block.shape):
            for x, cell in enumerate(row):
                if cell:
                    self.grid[self.current_block.y + y][self.current_block.x + x] = self.current_block.color
                    try:
                        if drop_sound:
                            pygame.mixer.find_channel(True).play(drop_sound)
                    except Exception:
                        pass
        
        self.clear_lines()
        self.current_block = self.next_block
        self.next_block = self.new_block()
        self.hold_used = False  # Reset hold po zablokowaniu klocka
        
        if not self.valid_move(self.current_block):
            self.game_over = True
    
    def clear_lines(self):
        lines_to_clear = [i for i, row in enumerate(self.grid) if all(row)]
        if lines_to_clear:
            # --- ANIMACJA MIGANIA ---
            blink_times = 4
            blink_delay = 100  # ms
            for blink in range(blink_times):
                for i in lines_to_clear:
                    for x in range(GRID_WIDTH):
                        self.grid[i][x] = WHITE if blink % 2 == 0 else COLORS[0]
                margin_left, margin_top = get_margins()
                self.draw(margin_left, margin_top, show_current_block=False)
                pygame.time.delay(blink_delay)
        for i in lines_to_clear:
            del self.grid[i]
            self.grid.insert(0, [0 for _ in range(GRID_WIDTH)])

        lines_cleared = len(lines_to_clear)
        if lines_cleared > 0:
            # --- ODTWÓRZ DŹWIĘK ---
            try:
                if clear_sound:
                    pygame.mixer.find_channel(True).play(clear_sound)
            except Exception:
                pass
            self.lines_cleared += lines_cleared
            self.score += [100, 300, 500, 800][lines_cleared - 1] * self.level
            if self.lines_cleared // 10 > (self.lines_cleared - lines_cleared) // 10:
                self.level += 1
                self.fall_speed = max(0.05, self.fall_speed * 0.8)
    
    def draw_grid(self, margin_left, margin_top):
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell = self.grid[y][x]
                bx = margin_left + x * GRID_SIZE
                by = margin_top + y * GRID_SIZE
                if cell:
                    shape_id = None
                    for idx, color in enumerate(COLORS):
                        if cell == color:
                            shape_id = idx
                            break
                    # Tło klocka
                    pygame.draw.rect(screen, GB_GRID, (bx, by, GRID_SIZE, GRID_SIZE))
                    pygame.draw.rect(screen, cell, (bx+4, by+4, GRID_SIZE-8, GRID_SIZE-8))
                    pygame.draw.rect(screen, GB_BG, (bx+10, by+10, GRID_SIZE-20, GRID_SIZE-20))
                    pygame.draw.rect(screen, GB_ACCENT, (bx, by, GRID_SIZE, GRID_SIZE), 2)
                    # Wzorki jak na Gameboyu
                    if shape_id == 0:  # I
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 2)
                    elif shape_id == 1:  # O
                        pygame.draw.rect(screen, GB_ACCENT, (bx+6, by+6, GRID_SIZE-12, GRID_SIZE-12), 2)
                        pygame.draw.rect(screen, GB_ACCENT, (bx+12, by+12, GRID_SIZE-24, GRID_SIZE-24), 1)
                    elif shape_id == 2:  # T
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.circle(screen, GB_ACCENT, (bx+GRID_SIZE//2, by+GRID_SIZE//2), 3)
                    elif shape_id == 3:  # L
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+GRID_SIZE-8, by+GRID_SIZE-8), (bx+GRID_SIZE-8, by+GRID_SIZE//2), 2)
                        pygame.draw.line(screen, GB_ACCENT, (bx+GRID_SIZE-8, by+GRID_SIZE-8), (bx+GRID_SIZE//2, by+GRID_SIZE-8), 2)
                    elif shape_id == 4:  # J
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+8, by+GRID_SIZE-8), (bx+GRID_SIZE//2, by+GRID_SIZE-8), 2)
                        pygame.draw.line(screen, GB_ACCENT, (bx+8, by+GRID_SIZE-8), (bx+8, by+GRID_SIZE//2), 2)
                    elif shape_id == 5:  # S
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+4, by+GRID_SIZE-8), (bx+GRID_SIZE-8, by+8), 2)
                    elif shape_id == 6:  # Z
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+4, by+8), (bx+GRID_SIZE-8, by+GRID_SIZE-8), 2)
                else:
                    # Puste pole z siatką
                    pygame.draw.rect(screen, GRAY, (bx, by, GRID_SIZE, GRID_SIZE), 1)
    
    def draw_block(self, block, margin_left, margin_top, x_offset=0, y_offset=0):
        # Rozpoznaj typ klocka po oryginalnym shape (niezależnie od obrotu)
        def get_shape_id(shape):
            for idx, s in enumerate(SHAPES):
                if len(shape) == len(s) and len(shape[0]) == len(s[0]):
                    if all([row == srow for row, srow in zip(shape, s)]):
                        return idx
            shape_sum = sum(sum(row) for row in shape)
            for idx, s in enumerate(SHAPES):
                if shape_sum == sum(sum(row) for row in s):
                    return idx
            return -1

        shape_id = get_shape_id(block.shape)
        color = COLORS[shape_id] if shape_id != -1 else GB_BLOCK

        for y, row in enumerate(block.shape):
            for x, cell in enumerate(row):
                if cell:
                    bx = margin_left + (block.x + x + x_offset) * GRID_SIZE
                    by = margin_top + (block.y + y + y_offset) * GRID_SIZE

                    # Cień (na dole i prawo)
                    pygame.draw.rect(screen, (100, 70, 130), (bx+4, by+4, GRID_SIZE, GRID_SIZE), border_radius=6)
                    # Główna bryła
                    pygame.draw.rect(screen, color, (bx, by, GRID_SIZE, GRID_SIZE), border_radius=6)
                    # Gruba ramka
                    pygame.draw.rect(screen, GB_ACCENT, (bx, by, GRID_SIZE, GRID_SIZE), 4, border_radius=6)

        shape_id = get_shape_id(block.shape)
        for y, row in enumerate(block.shape):
            for x, cell in enumerate(row):
                if cell:
                    bx = margin_left + (block.x + x + x_offset) * GRID_SIZE
                    by = margin_top + (block.y + y + y_offset) * GRID_SIZE

                    # Tło klocka
                    pygame.draw.rect(screen, GB_GRID, (bx, by, GRID_SIZE, GRID_SIZE))
                    pygame.draw.rect(screen, GB_BLOCK, (bx+4, by+4, GRID_SIZE-8, GRID_SIZE-8))
                    pygame.draw.rect(screen, GB_BG, (bx+10, by+10, GRID_SIZE-20, GRID_SIZE-20))
                    pygame.draw.rect(screen, GB_ACCENT, (bx, by, GRID_SIZE, GRID_SIZE), 2)

                    # --- WZORKI JAK NA GAMEBOYU ---
                    # I, O, T, L, J, S, Z
                    if shape_id == 0:  # I - kwadrat w kwadracie
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 2)
                    elif shape_id == 1:  # O - podwójna ramka
                        pygame.draw.rect(screen, GB_ACCENT, (bx+6, by+6, GRID_SIZE-12, GRID_SIZE-12), 2)
                        pygame.draw.rect(screen, GB_ACCENT, (bx+12, by+12, GRID_SIZE-24, GRID_SIZE-24), 1)
                    elif shape_id == 2:  # T - kwadrat + kropka
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.circle(screen, GB_ACCENT, (bx+GRID_SIZE//2, by+GRID_SIZE//2), 3)
                    elif shape_id == 3:  # L - kwadrat + L-ka
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+GRID_SIZE-8, by+GRID_SIZE-8), (bx+GRID_SIZE-8, by+GRID_SIZE//2), 2)
                        pygame.draw.line(screen, GB_ACCENT, (bx+GRID_SIZE-8, by+GRID_SIZE-8), (bx+GRID_SIZE//2, by+GRID_SIZE-8), 2)
                    elif shape_id == 4:  # J - kwadrat + J-ka
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+8, by+GRID_SIZE-8), (bx+GRID_SIZE//2, by+GRID_SIZE-8), 2)
                        pygame.draw.line(screen, GB_ACCENT, (bx+8, by+GRID_SIZE-8), (bx+8, by+GRID_SIZE//2), 2)
                    elif shape_id == 5:  # S - dwa rogi
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+4, by+GRID_SIZE-8), (bx+GRID_SIZE-8, by+8), 2)
                    elif shape_id == 6:  # Z - dwa inne rogi
                        pygame.draw.rect(screen, GB_ACCENT, (bx+8, by+8, GRID_SIZE-16, GRID_SIZE-16), 1)
                        pygame.draw.line(screen, GB_ACCENT, (bx+4, by+8), (bx+GRID_SIZE-8, by+GRID_SIZE-8), 2)
    
    def draw_hold_block(self, margin_left, margin_top):
        font = pygame.font.Font(tetris_font_path, 28)
        hold_text = font.render('Hold', True, BLACK)
        panel_x = margin_left + GRID_WIDTH * GRID_SIZE + 60
        panel_y = margin_top + 400
        panel_w = SIDEBAR_WIDTH - 100
        panel_h = 200

        pygame.draw.rect(screen, BLACK, (panel_x-16, panel_y-16, panel_w+32, panel_h+32), 2, border_radius=18)
        pygame.draw.rect(screen, WHITE, (panel_x, panel_y, panel_w, panel_h), 0, border_radius=14)

        text_rect = hold_text.get_rect(center=(panel_x + panel_w//2, panel_y + 28))
        screen.blit(hold_text, text_rect)

        if self.hold_block:
            # Zawsze domyślna orientacja!
            # Znajdź shape_id na podstawie koloru lub shape
            shape_id = None
            for idx, s in enumerate(SHAPES):
                if self.hold_block.shape == s:
                    shape_id = idx
                    break
            if shape_id is None:
                # Jeśli shape nie pasuje, spróbuj po kolorze
                for idx, color in enumerate(COLORS):
                    if self.hold_block.color == color:
                        shape_id = idx
                        break
            # Użyj domyślnego shape z SHAPES
            base_shape = SHAPES[shape_id] if shape_id is not None else self.hold_block.shape
            block_width = len(base_shape[0]) * GRID_SIZE
            block_height = len(base_shape) * GRID_SIZE

            y_offset = panel_y + 80 + (panel_h - 100 - block_height) // 2
            x_offset = panel_x + (panel_w - block_width) // 2

            for y, row in enumerate(base_shape):
                for x, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(
                            screen,
                            self.hold_block.color,
                            [x_offset + x * GRID_SIZE, y_offset + y * GRID_SIZE, GRID_SIZE, GRID_SIZE],
                            0
                        )
                        pygame.draw.rect(
                            screen,
                            BLACK,
                            [x_offset + x * GRID_SIZE, y_offset + y * GRID_SIZE, GRID_SIZE, GRID_SIZE],
                            2
                        )

    def draw_board_gradient(self, margin_left, margin_top):
        # Gradient od jasnego fioletu (góra) do ciemnego fioletu (dół)
        top_color = (220, 200, 255)    # Jasny fiolet
        bottom_color = (145, 120, 179)   # Ciemny fiolet

        height = GRID_HEIGHT * GRID_SIZE
        for i in range(height):
            ratio = i / height
            r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
            g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
            b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
            pygame.draw.line(
                screen,
                (r, g, b),
                (margin_left, margin_top + i),
                (margin_left + GRID_WIDTH * GRID_SIZE - 1, margin_top + i)
            )

    
    def draw_left_panel(self, margin_left, margin_top):
            # Panel boczny po lewej stronie planszy z instrukcją sterowania
            panel_x = margin_left - SIDEBAR_WIDTH
            panel_y = margin_top
            panel_w = SIDEBAR_WIDTH + 100
            panel_h = GRID_HEIGHT * GRID_SIZE

            # Tło panelu i ramka
            pygame.draw.rect(screen, BLACK, (panel_x, panel_y, panel_w, panel_h), 3, border_radius=12)

            # Instrukcja sterowania
            try:
                controls_font = pygame.font.Font(tetris_font_path, 15)
            except Exception:
                controls_font = pygame.font.SysFont('comicsans', 20)
            controls = [
                "Sterowanie:",
                "← →  - ruch w lewo/prawo",
                "↓   -  szybciej w dół",
                "↑   -  obrót klocka",
                "Spacja - drop",
                "Q   -  zamiana",
                "ESC -  pauza"
            ]
            for i, line in enumerate(controls):
                text = controls_font.render(line, True, BLACK)
                screen.blit(text, (panel_x + 20, panel_y + 22 + i * 34))


    def draw(self, margin_left, margin_top, show_current_block=True):
        screen.fill(WHITE)
        border_width = 10
        pygame.draw.rect(screen, BLACK, [margin_left - border_width, margin_top, border_width, GRID_HEIGHT * GRID_SIZE])
        pygame.draw.rect(screen, BLACK, [margin_left + GRID_WIDTH * GRID_SIZE, margin_top, border_width, GRID_HEIGHT * GRID_SIZE])
        self.draw_left_panel(margin_left, margin_top)
        self.draw_board_gradient(margin_left, margin_top)
        self.draw_grid(margin_left, margin_top)
        if show_current_block:
            self.draw_block(self.current_block, margin_left, margin_top)

        pygame.draw.rect(screen, BLACK, [margin_left + GRID_WIDTH * GRID_SIZE, margin_top, SIDEBAR_WIDTH, GRID_HEIGHT * GRID_SIZE], 2, border_radius=12)

        # Informacje
        score_text = score_font.render(f'Score: {self.score}', True, BLACK)
        level_text = score_font.render(f'Level: {self.level}', True, BLACK)
        lines_text = score_font.render(f'Lines: {self.lines_cleared}', True, BLACK)

        screen.blit(score_text, [margin_left + GRID_WIDTH * GRID_SIZE + 20, margin_top + 20])
        screen.blit(level_text, [margin_left + GRID_WIDTH * GRID_SIZE + 20, margin_top + 60])
        screen.blit(lines_text, [margin_left + GRID_WIDTH * GRID_SIZE + 20, margin_top + 100])

        self.draw_next_block(margin_left, margin_top)
        self.draw_hold_block(margin_left, margin_top)
        _apply_scanlines(screen)
        _apply_pixelation(screen, "minimum")
        _apply_flicker(screen)
        _apply_glow(screen)
        _add_glitch_effect(screen.get_height(), screen.get_width(), screen, "maximum")
        _add_rolling_static(screen, screen.get_height(), screen.get_width(), "minimum")
        render_fisheye_gl(fisheye_ctx, fisheye_prog, fisheye_vao, fisheye_texture, screen, distortion=0.15)



    def draw_next_block(self, margin_left, margin_top):
        font = pygame.font.Font(tetris_font_path, 28)
        next_text = font.render('Next', True, BLACK)
        panel_x = margin_left + GRID_WIDTH * GRID_SIZE + 60  # większy margines z lewej
        panel_y = margin_top + 200  # wyżej
        panel_w = SIDEBAR_WIDTH - 100 # szerszy panel
        panel_h = 150  # wyższy panel

        # Grubsza ramka wokół panelu "Next"
        pygame.draw.rect(screen, BLACK, (panel_x-16, panel_y-16, panel_w+32, panel_h+32), 2, border_radius=18)
        pygame.draw.rect(screen, WHITE, (panel_x, panel_y, panel_w, panel_h), 0, border_radius=14)

        # Tekst wyśrodkowany
        text_rect = next_text.get_rect(center=(panel_x + panel_w//2, panel_y + 28))
        screen.blit(next_text, text_rect)

        block = self.next_block
        block_width = len(block.shape[0]) * GRID_SIZE
        block_height = len(block.shape) * GRID_SIZE

        # Większy odstęp od napisu i większy margines od krawędzi
        y_offset = panel_y + 80 + (panel_h - 100 - block_height) // 2
        x_offset = panel_x + (panel_w - block_width) // 2

        for y, row in enumerate(block.shape):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(
                        screen,
                        block.color,
                        [x_offset + x * GRID_SIZE, y_offset + y * GRID_SIZE, GRID_SIZE, GRID_SIZE],
                        0
                    )
                    pygame.draw.rect(
                        screen,
                        BLACK,
                        [x_offset + x * GRID_SIZE, y_offset + y * GRID_SIZE, GRID_SIZE, GRID_SIZE],
                        2
                    )

    
    def run(self):
        fall_time = 0
        paused = False
        started = False

        while not self.game_over:
            if not paused:
                fall_time += clock.get_rawtime() / 200
            clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if paused:
                    resume_button.check_hover(pygame.mouse.get_pos())
                    pause_restart_button.check_hover(pygame.mouse.get_pos())
                    pause_quit_button.check_hover(pygame.mouse.get_pos())
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if resume_button.is_clicked(pygame.mouse.get_pos(), event):
                            paused = False
                        if pause_restart_button.is_clicked(pygame.mouse.get_pos(), event):
                            self.reset_game()
                            paused = False
                            started = False
                            break  # Restart gry, wyjdź z obsługi eventów
                        if pause_quit_button.is_clicked(pygame.mouse.get_pos(), event):
                            return 'menu'
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        paused = False
                    draw_pause()
                    break

                if event.type == pygame.KEYDOWN:
                    if not paused and event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_UP, pygame.K_SPACE, pygame.K_q]:
                        started = True

                    if event.key == pygame.K_LEFT and not paused and self.valid_move(self.current_block, -1, 0):
                        self.current_block.x -= 1
                    if event.key == pygame.K_RIGHT and not paused and self.valid_move(self.current_block, 1, 0):
                        self.current_block.x += 1
                    if event.key == pygame.K_DOWN and not paused and self.valid_move(self.current_block, 0, 1):
                        self.current_block.y += 1
                    if event.key == pygame.K_UP and not paused:
                        self.rotate_block()
                    if event.key == pygame.K_SPACE and not paused:
                        while self.valid_move(self.current_block, 0, 1):
                            self.current_block.y += 1
                        self.lock_block()
                    if event.key == pygame.K_q and not paused:
                        self.hold_current_block()
                    if event.key == pygame.K_ESCAPE:
                            paused = True

            if paused:
                continue

            if fall_time >= self.fall_speed:
                fall_time = 0
                if self.valid_move(self.current_block, 0, 1):
                    self.current_block.y += 1
                else:
                    self.lock_block()
            margin_left, margin_top = get_margins()
            self.draw(margin_left, margin_top)
        return 'game_over'

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, padding_x=24, padding_y=10):
        self.base_x = x
        self.base_y = y
        self.base_width = width
        self.base_height = height
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        self.padding_x = padding_x
        self.padding_y = padding_y
        self.update_rect()

    def update_rect(self):
        text_surface = menu_font.render(self.text, True, BLACK)
        text_width, text_height = text_surface.get_size()
        btn_width = max(self.base_width, text_width + 2 * self.padding_x)
        btn_height = max(self.base_height, text_height + 2 * self.padding_y)
        self.rect = pygame.Rect(
            self.base_x + (self.base_width - btn_width) // 2,
            self.base_y + (self.base_height - btn_height) // 2,
            btn_width,
            btn_height
        )

    def draw(self, surface=None):
        # Rysuj tylko przycisk, nie całą planszę!
        if surface is None:
            surface = screen
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, BLACK, self.rect, 6, border_radius=8)
        text_surface = menu_font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
    
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        return self.is_hovered
    
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

# Przyciski menu
start_button = Button(SCREEN_WIDTH//2 - 100, 360, 200, 50, "Start", GRAY, HIGHLIGHT)
options_button = Button(SCREEN_WIDTH//2 - 100, 470, 200, 50, "Options", GRAY, HIGHLIGHT)
quit_button = Button(SCREEN_WIDTH//2 - 100, 580, 200, 50, "Quit", GRAY, HIGHLIGHT)

# Przyciski game over
restart_button = Button(SCREEN_WIDTH//2 - 100, 350, 200, 50, "Play Again", GRAY, HIGHLIGHT)
menu_button = Button(SCREEN_WIDTH//2 - 100, 470, 200, 50, "Main Menu", GRAY, HIGHLIGHT)

resume_button = Button(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2, 200, 50, "Resume", GRAY, HIGHLIGHT)
pause_restart_button = Button(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 80, 200, 50, "Restart", GRAY, HIGHLIGHT)
pause_quit_button = Button(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 160, 200, 50, "Quit to Menu", GRAY, HIGHLIGHT)

def draw_pause():
    screen.fill(WHITE)
    pause_font = pygame.font.Font(tetris_font_path, 80)
    pause_text = pause_font.render('PAUZA', True, RED)
    pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
    screen.blit(pause_text, pause_rect)
    resume_button.draw(screen)
    pause_quit_button.draw(screen)
    pause_restart_button.draw(screen)

    _apply_scanlines(screen)
    _apply_pixelation(screen, "minimum")
    _apply_flicker(screen)
    _apply_glow(screen)
    _add_glitch_effect(screen.get_height(), screen.get_width(), screen, "maximum")
    _add_rolling_static(screen, screen.get_height(), screen.get_width(), "minimum")

    render_fisheye_gl(fisheye_ctx, fisheye_prog, fisheye_vao, fisheye_texture, screen, distortion=0.15)


def draw_menu():
    screen.fill(WHITE) 
    
    title_text = title_font.render('TETRIS', True, BLACK)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 150))
    screen.blit(title_text, title_rect)
    
    start_button.draw(screen)
    options_button.draw(screen)
    quit_button.draw(screen)

    _apply_scanlines(screen)
    _apply_pixelation(screen, "minimum")
    _apply_flicker(screen)
    _apply_glow(screen)
    _add_glitch_effect(screen.get_height(), screen.get_width(), screen, "maximum")
    _add_rolling_static(screen, screen.get_height(), screen.get_width(), "minimum")

    render_fisheye_gl(fisheye_ctx, fisheye_prog, fisheye_vao, fisheye_texture, screen, distortion=0.15)
    

def draw_game_over(score):
    screen.fill(WHITE)
    
    game_over_text = title_font.render('GAME OVER', True, RED)
    game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, 150))
    screen.blit(game_over_text, game_over_rect)
    
    score_text = menu_font.render(f'Score: {score}', True, BLACK)
    score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, 250))
    screen.blit(score_text, score_rect)
    
    restart_button.draw(screen)
    menu_button.draw(screen)

    _apply_scanlines(screen)
    _apply_pixelation(screen, "minimum")
    _apply_flicker(screen)
    _apply_glow(screen)
    _add_glitch_effect(screen.get_height(), screen.get_width(), screen, "maximum")
    _add_rolling_static(screen, screen.get_height(), screen.get_width(), "minimum")

    render_fisheye_gl(fisheye_ctx, fisheye_prog, fisheye_vao, fisheye_texture, screen, distortion=0.15)

class Slider:
    def __init__(self, x, y, width, min_val=0.0, max_val=1.0, value=1.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = 12
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.handle_radius = 14

    def draw(self, surface):
        # Linia suwaka
        pygame.draw.line(surface, DARK_GRAY, (self.x, self.y + self.height // 2), (self.x + self.width, self.y + self.height // 2), 6)
        # Uchwyt
        handle_x = int(self.x + (self.value - self.min_val) / (self.max_val - self.min_val) * self.width)
        pygame.draw.circle(surface, HIGHLIGHT, (handle_x, self.y + self.height // 2), self.handle_radius)
        pygame.draw.circle(surface, BLACK, (handle_x, self.y + self.height // 2), self.handle_radius, 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            handle_x = int(self.x + (self.value - self.min_val) / (self.max_val - self.min_val) * self.width)
            if abs(mx-handle_x) < self.handle_radius+2 and abs(my-(self.y+self.height//2)) < self.handle_radius+2:
                self.dragging = True
            else:
                self.dragging = False
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if getattr(self, 'dragging', False):
                mx = event.pos[0]
                rel = (mx - self.x) / self.width
                rel = max(0.0, min(1.0, rel))
                self.value = self.min_val + rel * (self.max_val - self.min_val)
                pygame.mixer.music.set_volume(self.value)

back_button = Button(SCREEN_WIDTH//2 - 100, 700, 200, 50, "Back", GRAY, HIGHLIGHT)
volume_slider = Slider(SCREEN_WIDTH//2 - 120, 350, 240, value=pygame.mixer.music.get_volume())
drop_volume_slider = Slider(
    SCREEN_WIDTH//2 - 120, 550, 240,
    value=drop_sound.get_volume() if drop_sound else 1.0
)

def draw_options():
    screen.fill(WHITE)
    title_text = title_font.render('Opcje', True, BLACK)
    title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, 150))
    screen.blit(title_text, title_rect)

    # Etykieta głośności muzyki
    label = menu_font.render("Muzyka", True, BLACK)
    label_rect = label.get_rect(center=(SCREEN_WIDTH//2, 300))
    screen.blit(label, label_rect)
    volume_slider.draw(screen)
    percent = int(volume_slider.value * 100)
    percent_text = score_font.render(f"{percent}%", True, BLACK)
    percent_rect = percent_text.get_rect(center=(SCREEN_WIDTH//2, 400))
    screen.blit(percent_text, percent_rect)

    # Etykieta głośności dźwięku drop
    drop_label = menu_font.render("Dźwięk", True, BLACK)
    drop_label_rect = drop_label.get_rect(center=(SCREEN_WIDTH//2, 400))
    screen.blit(drop_label, (SCREEN_WIDTH//2 - drop_label.get_width()//2, 470))
    drop_volume_slider.draw(screen)
    drop_percent = int(drop_volume_slider.value * 100)
    drop_percent_text = score_font.render(f"{drop_percent}%", True, BLACK)
    drop_percent_rect = drop_percent_text.get_rect(center=(SCREEN_WIDTH//2, 600))
    screen.blit(drop_percent_text, drop_percent_rect)

    back_button.draw(screen)

    _apply_scanlines(screen)
    _apply_pixelation(screen, "minimum")
    _apply_flicker(screen)
    _apply_glow(screen)
    _add_glitch_effect(screen.get_height(), screen.get_width(), screen, "maximum")
    _add_rolling_static(screen, screen.get_height(), screen.get_width(), "minimum")

    render_fisheye_gl(fisheye_ctx, fisheye_prog, fisheye_vao, fisheye_texture, screen, distortion=0.15)

def main():
    game = Game()
    current_screen = 'menu'

    while True:
        mouse_pos = pygame.mouse.get_pos()

        if current_screen == 'menu':
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                start_button.check_hover(mouse_pos)
                quit_button.check_hover(mouse_pos)
                options_button.check_hover(mouse_pos)

                if start_button.is_clicked(mouse_pos, event):
                    game.reset_game()
                    current_screen = 'game'
                if quit_button.is_clicked(mouse_pos, event):
                    pygame.quit()
                    sys.exit()
                if options_button.is_clicked(mouse_pos, event):
                    current_screen = 'options'

            draw_menu()

        elif current_screen == 'options':
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                back_button.check_hover(mouse_pos)
                volume_slider.handle_event(event)
                drop_volume_slider.handle_event(event)
                # Ustaw głośność muzyki na podstawie suwaka
                pygame.mixer.music.set_volume(volume_slider.value)
                # Ustaw głośność dźwięku drop na podstawie suwaka
                try:
                    if drop_sound:
                        drop_sound.set_volume(drop_volume_slider.value)
                except Exception:
                    pass
                if back_button.is_clicked(mouse_pos, event):
                    current_screen = 'menu'
            draw_options()

        elif current_screen == 'game':
            result = game.run()
            if result == 'menu':
                current_screen = 'menu'
            elif result == 'game_over':
                current_screen = 'game_over'

        elif current_screen == 'game_over':
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                restart_button.check_hover(mouse_pos)
                menu_button.check_hover(mouse_pos)

                if restart_button.is_clicked(mouse_pos, event):
                    game.reset_game()
                    current_screen = 'game'
                if menu_button.is_clicked(mouse_pos, event):
                    current_screen = 'menu'

            draw_game_over(game.score)

        clock.tick(FPS)

if __name__ == "__main__":
    main()