import pygame
import chess
import chess.engine
import os
import math
import sys

# --- EXE İÇİN DOSYA YOLU DÜZENLEYİCİ ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- YAPILANDIRMA ---
BOARD_SIZE = 640
BAR_WIDTH = 40  
WIDTH, HEIGHT = BOARD_SIZE + BAR_WIDTH, BOARD_SIZE
SQ_SIZE = BOARD_SIZE // 8
PIECE_SIZE = int(SQ_SIZE * 0.90)
ICON_SIZE = int(SQ_SIZE * 0.45)

ENGINE_PATH = resource_path("stockfish-windows-x86-64-avx2.exe")
TEXTURE_DIR = resource_path("texture")
SOUND_DIR = resource_path("sound")

def load_assets():
    images = {}
    for color in ['w', 'b']:
        for piece in ['P', 'R', 'N', 'B', 'Q', 'K']:
            path = os.path.join(TEXTURE_DIR, f"{color}{piece}.png")
            if os.path.exists(path):
                img = pygame.image.load(path)
                images[color + piece] = pygame.transform.smoothscale(img, (PIECE_SIZE, PIECE_SIZE))
    
    icons = {
        "brilliant": "brilliant_1024x.png", "great": "great_find_1024x.png",
        "best": "best_1024x.png", "excellent": "excellent_1024x.png",
        "good": "good_1024x.png", "inaccuracy": "inaccuracy_1024x.png",
        "mistake": "mistake_1024x.png", "blunder": "blunder_1024x.png",
        "book": "book_1024x.png", "mate": "mate_1024x.png",
        "king_dead": "king_dead.png" 
    }
    for key, filename in icons.items():
        path = os.path.join(TEXTURE_DIR, filename)
        if os.path.exists(path):
            img = pygame.image.load(path)
            images[key] = pygame.transform.smoothscale(img, (ICON_SIZE, ICON_SIZE))
            
    pygame.mixer.init()
    sounds = {}
    for n in ["move", "capture", "check", "checkmate", "start"]:
        path = os.path.join(SOUND_DIR, f"{n}.mp3")
        if os.path.exists(path):
            sounds[n] = pygame.mixer.Sound(path)
    return images, sounds

def get_win_pct(engine, board):
    try:
        info = engine.analyse(board, chess.engine.Limit(time=0.1))
        score = info["score"].white().score(mate_score=10000)
        return 50 + 50 * (2 / (1 + math.exp(-0.0036822 * score)) - 1)
    except: return 50

def draw_winning_bar(screen, win_pct):
    white_h = int(HEIGHT * (win_pct / 100))
    black_h = HEIGHT - white_h
    pygame.draw.rect(screen, (35, 34, 32), (BOARD_SIZE, 0, BAR_WIDTH, black_h))
    pygame.draw.rect(screen, (240, 240, 240), (BOARD_SIZE, black_h, BAR_WIDTH, white_h))
    font = pygame.font.SysFont("Arial", 14, bold=True)
    val = int(win_pct if win_pct > 50 else 100-win_pct)
    txt_color = (0,0,0) if win_pct > 50 else (255,255,255)
    label = font.render(f"%{val}", True, txt_color)
    screen.blit(label, (BOARD_SIZE + 5, HEIGHT - 25 if win_pct > 50 else 10))

def analyze_move(board, move, engine):
    temp_board = board.copy()
    temp_board.push(move)
    if temp_board.is_checkmate(): return "mate"
    
    info = engine.analyse(board, chess.engine.Limit(depth=12))
    best_move = info["pv"][0]
    score_before = info["score"].relative.score(mate_score=10000)
    
    is_capture = board.is_capture(move)
    board.push(move)
    info_after = engine.analyse(board, chess.engine.Limit(depth=12))
    score_after = -info_after["score"].relative.score(mate_score=10000)
    board.pop()

    diff = score_before - score_after
    if board.fullmove_number <= 8 and move == best_move: return "book"
    if move == best_move:
        if is_capture and diff < 10: return "brilliant"
        return "best"
    if diff < 20: return "excellent"
    if diff < 100: return "inaccuracy"
    if diff < 300: return "mistake"
    return "blunder"

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)
    pygame.display.set_caption("Chess Pro - Chess.com Style")
    clock = pygame.time.Clock() 
    
    images, sounds = load_assets()
    board = chess.Board()
    
    try:
        engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
    except: return

    if "start" in sounds: sounds["start"].play()

    dragged_piece, drag_start_sq, last_analysis = None, None, None
    win_pct = 50
    dead_king_sq = None 
    legal_destinations = [] # Tıklanan taşın gidebileceği kareler

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            
            if e.type == pygame.MOUSEBUTTONDOWN and mouse_pos[0] < BOARD_SIZE:
                c, r = mouse_pos[0]//SQ_SIZE, 7-(mouse_pos[1]//SQ_SIZE)
                sq = chess.square(c, r)
                p = board.piece_at(sq)
                if p and p.color == board.turn:
                    dragged_piece, drag_start_sq = p, sq
                    # Hareket edebileceği yerleri hesapla
                    legal_destinations = [m.to_square for m in board.legal_moves if m.from_square == sq]
                else:
                    legal_destinations = []

            if e.type == pygame.MOUSEBUTTONUP:
                if dragged_piece:
                    c, r = mouse_pos[0]//SQ_SIZE, 7-(mouse_pos[1]//SQ_SIZE)
                    target = chess.square(c, r)
                    move = chess.Move(drag_start_sq, target)
                    
                    if dragged_piece.piece_type == chess.PAWN:
                        if (dragged_piece.color == chess.WHITE and chess.square_rank(target) == 7) or \
                           (dragged_piece.color == chess.BLACK and chess.square_rank(target) == 0):
                            move.promotion = chess.QUEEN

                    if move in board.legal_moves:
                        is_capture_move = board.is_capture(move)
                        res_type = analyze_move(board, move, engine)
                        last_analysis = {"sq": target, "type": res_type}
                        
                        board.push(move) 

                        if board.is_checkmate():
                            if "checkmate" in sounds: sounds["checkmate"].play()
                            dead_king_sq = board.king(board.turn)
                        elif board.is_check(): 
                            if "check" in sounds: sounds["check"].play()
                        elif is_capture_move:
                            if "capture" in sounds: sounds["capture"].play()
                        else: 
                            if "move" in sounds: sounds["move"].play()
                        
                        win_pct = get_win_pct(engine, board)
                        legal_destinations = []
                    
                    dragged_piece, drag_start_sq = None, None

        # --- ÇİZİM ---
        screen.fill((40, 40, 40))
        for r in range(8):
            for c in range(8):
                sq = chess.square(c, 7-r)
                color = pygame.Color("#eeeed2") if (r + c) % 2 == 0 else pygame.Color("#b58863")
                
                if dead_king_sq == sq:
                    color = pygame.Color("#f44336")

                pygame.draw.rect(screen, color, (c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

                # HAREKET NOKTALARI ÇİZİMİ
                if sq in legal_destinations:
                    center = (c * SQ_SIZE + SQ_SIZE // 2, r * SQ_SIZE + SQ_SIZE // 2)
                    if board.piece_at(sq): # Eğer karede rakip taş varsa (Yeme hamlesi)
                        pygame.draw.circle(screen, (0, 0, 0, 30), center, SQ_SIZE // 2, 5) # Halka
                    else: # Boş kareyse
                        s = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
                        pygame.draw.circle(s, (0, 0, 0, 30), (SQ_SIZE//2, SQ_SIZE//2), SQ_SIZE // 6)
                        screen.blit(s, (c*SQ_SIZE, r*SQ_SIZE))

        draw_winning_bar(screen, win_pct)

        for sq in chess.SQUARES:
            if sq == drag_start_sq: continue
            p = board.piece_at(sq)
            col, row = chess.square_file(sq), 7-chess.square_rank(sq)
            
            if p:
                img = images.get(('w' if p.color else 'b') + p.symbol().upper())
                if img: screen.blit(img, img.get_rect(center=(col*SQ_SIZE + SQ_SIZE//2, row*SQ_SIZE + SQ_SIZE//2)))
            
            if last_analysis and last_analysis["sq"] == sq and last_analysis["type"]:
                icon = images.get(last_analysis["type"])
                if icon: screen.blit(icon, (col*SQ_SIZE + SQ_SIZE - ICON_SIZE, row*SQ_SIZE))
            
            if dead_king_sq == sq:
                d_icon = images.get("king_dead")
                if d_icon: screen.blit(d_icon, (col*SQ_SIZE + SQ_SIZE - ICON_SIZE, row*SQ_SIZE))

        if dragged_piece:
            img = images.get(('w' if dragged_piece.color else 'b') + dragged_piece.symbol().upper())
            if img: screen.blit(img, img.get_rect(center=mouse_pos))

        pygame.display.flip()
        clock.tick(240) 

    engine.quit()
    pygame.quit()

if __name__ == "__main__":
    main()
