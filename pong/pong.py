import random
import sys
import cv2
import mediapipe as mp
import pygame

# --- CONFIGURAÇÕES INICIAIS ---
pygame.init()

# Tela Cheia Nativa
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()

pygame.display.set_caption("Pong - Visão Computacional")
clock = pygame.time.Clock()

# Cores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (180, 180, 180)

# --- CONFIGURAÇÃO DO MEDIAPIPE ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6,
)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

HAND_CONNECTIONS = mp_hands.HAND_CONNECTIONS

# --- VARIÁVEIS DO JOGO ---
paddle_width, paddle_height = 15, 100
ball_size = 15

# Posições das Raquetes
p1_x = 35
p1_y = HEIGHT // 2 - paddle_height // 2

p2_x = WIDTH - 50
p2_y = HEIGHT // 2 - paddle_height // 2

# Velocidades e Aceleração
INITIAL_BASE_SPEED = 8.0
MAX_BALL_SPEED = 22.0
BALL_ACCELERATION = 0.005

ball_speed_x = INITIAL_BASE_SPEED
ball_speed_y = INITIAL_BASE_SPEED

# Bola
ball_x = WIDTH // 2
ball_y = HEIGHT // 2
ball_vel_x = -ball_speed_x * random.choice((1, -1))
ball_vel_y = -ball_speed_y * random.choice((1, -1))

# Placar e Controle de Estado
p1_score = 0
p2_score = 0
max_score = 7
game_over = False
is_paused = False
winner_text = ""

game_state = "MENU"
game_mode = 1

font = pygame.font.SysFont("Courier New", 50, bold=True)
small_font = pygame.font.SysFont("Courier New", 24, bold=True)
button_font = pygame.font.SysFont("Courier New", 18, bold=True)

# Retângulos dos Botões da Interface de Jogo
btn_pause_rect = pygame.Rect(WIDTH - 190, 15, 80, 32)
btn_menu_rect = pygame.Rect(WIDTH - 95, 15, 80, 32)

# Retângulo do Botão Sair no Menu
btn_quit_menu_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 120, 200, 45)


def draw_hand_landmarks(surface, landmarks_list):
    """Converte e desenha os pontos e conexões das mãos na tela do Pygame."""
    for hand_landmarks in landmarks_list:
        points = []
        for lm in hand_landmarks.landmark:
            px = int(lm.x * WIDTH)
            py = int(lm.y * HEIGHT)
            points.append((px, py))

        for connection in HAND_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            pygame.draw.line(
                surface, GRAY, points[start_idx], points[end_idx], 2
            )

        for idx, pt in enumerate(points):
            if idx in (8, 0):
                pygame.draw.circle(surface, RED, pt, 6)
            else:
                pygame.draw.circle(surface, GREEN, pt, 4)


def draw_ui_buttons(surface):
    """Desenha os botões interativos de Pause e Menu durante a partida."""
    mouse_pos = pygame.mouse.get_pos()

    # Botão Pause
    pause_color = (
        LIGHT_GRAY if btn_pause_rect.collidepoint(mouse_pos) else DARK_GRAY
    )
    pygame.draw.rect(surface, pause_color, btn_pause_rect, border_radius=5)
    pygame.draw.rect(surface, WHITE, btn_pause_rect, 2, border_radius=5)
    p_text = "RES" if is_paused else "PAUSE"
    p_render = button_font.render(p_text, True, WHITE)
    surface.blit(
        p_render,
        (
            btn_pause_rect.x + (btn_pause_rect.width - p_render.get_width()) // 2,
            btn_pause_rect.y
            + (btn_pause_rect.height - p_render.get_height()) // 2,
        ),
    )

    # Botão Menu
    menu_color = (
        LIGHT_GRAY if btn_menu_rect.collidepoint(mouse_pos) else DARK_GRAY
    )
    pygame.draw.rect(surface, menu_color, btn_menu_rect, border_radius=5)
    pygame.draw.rect(surface, WHITE, btn_menu_rect, 2, border_radius=5)
    m_render = button_font.render("MENU", True, WHITE)
    surface.blit(
        m_render,
        (
            btn_menu_rect.x + (btn_menu_rect.width - m_render.get_width()) // 2,
            btn_menu_rect.y
            + (btn_menu_rect.height - m_render.get_height()) // 2,
        ),
    )


def reset_point(winner_direction=1):
    """Reinicia a bola e define a velocidade base (com acelerador pós-3 pontos)."""
    global ball_x, ball_y, ball_speed_x, ball_speed_y, ball_vel_x, ball_vel_y

    total_score = p1_score + p2_score
    if total_score >= 3:
        current_base = INITIAL_BASE_SPEED * 1.5
    else:
        current_base = INITIAL_BASE_SPEED

    ball_speed_x = current_base
    ball_speed_y = current_base
    ball_x, ball_y = WIDTH // 2, HEIGHT // 2
    ball_vel_x = winner_direction * ball_speed_x
    ball_vel_y = ball_speed_y * random.choice((1, -1))


def reset_game():
    """Reinicia o placar e as posições."""
    global p1_score, p2_score, game_over, is_paused, p1_y, p2_y
    p1_score = 0
    p2_score = 0
    game_over = False
    is_paused = False
    p1_y = HEIGHT // 2 - paddle_height // 2
    p2_y = HEIGHT // 2 - paddle_height // 2
    reset_point(random.choice((1, -1)))


# --- LOOP PRINCIPAL DO JOGO ---
running = True
while running:

    # ---------------------------------------------------------
    # TELA DE MENU
    # ---------------------------------------------------------
    if game_state == "MENU":
        screen.fill(BLACK)
        mouse_pos = pygame.mouse.get_pos()

        title_render = font.render("PONG IA", True, WHITE)
        option1_render = small_font.render(
            "Pressione [1] - 1 Jogador (vs CPU)", True, WHITE
        )
        option2_render = small_font.render(
            "Pressione [2] - 2 Jogadores", True, WHITE
        )
        option_quit_render = small_font.render(
            "Pressione [S] - Sair do Jogo", True, WHITE
        )

        screen.blit(
            title_render,
            (WIDTH // 2 - title_render.get_width() // 2, HEIGHT // 4),
        )
        screen.blit(
            option1_render,
            (WIDTH // 2 - option1_render.get_width() // 2, HEIGHT // 2 - 30),
        )
        screen.blit(
            option2_render,
            (WIDTH // 2 - option2_render.get_width() // 2, HEIGHT // 2 + 20),
        )
        screen.blit(
            option_quit_render,
            (
                WIDTH // 2 - option_quit_render.get_width() // 2,
                HEIGHT // 2 + 70,
            ),
        )

        # Desenhar Botão Clicável de Sair
        btn_quit_color = (
            LIGHT_GRAY
            if btn_quit_menu_rect.collidepoint(mouse_pos)
            else DARK_GRAY
        )
        pygame.draw.rect(
            screen, btn_quit_color, btn_quit_menu_rect, border_radius=8
        )
        pygame.draw.rect(screen, WHITE, btn_quit_menu_rect, 2, border_radius=8)
        quit_txt_render = button_font.render("SAIR DO JOGO", True, WHITE)
        screen.blit(
            quit_txt_render,
            (
                btn_quit_menu_rect.x
                + (btn_quit_menu_rect.width - quit_txt_render.get_width()) // 2,
                btn_quit_menu_rect.y
                + (btn_quit_menu_rect.height - quit_txt_render.get_height())
                // 2,
            ),
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_quit_menu_rect.collidepoint(event.pos):
                    running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    game_mode = 1
                    reset_game()
                    game_state = "PLAYING"
                elif event.key == pygame.K_2:
                    game_mode = 2
                    reset_game()
                    game_state = "PLAYING"
                elif event.key in (pygame.K_s, pygame.K_ESCAPE):
                    running = False

        pygame.display.flip()
        clock.tick(60)

    # ---------------------------------------------------------
    # TELA DE JOGO
    # ---------------------------------------------------------
    elif game_state == "PLAYING":

        current_landmarks = None

        # 1. Processamento da Visão Computacional
        success, frame = cap.read()
        if success and not game_over and not is_paused:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                current_landmarks = results.multi_hand_landmarks
                for hand_landmarks in results.multi_hand_landmarks:
                    wrist_x = hand_landmarks.landmark[
                        mp_hands.HandLandmark.WRIST
                    ].x
                    index_y = hand_landmarks.landmark[
                        mp_hands.HandLandmark.INDEX_FINGER_TIP
                    ].y
                    target_y = int(index_y * HEIGHT) - paddle_height // 2

                    if game_mode == 1:
                        p1_y = max(0, min(HEIGHT - paddle_height, target_y))
                    else:
                        if wrist_x < 0.5:
                            p1_y = max(0, min(HEIGHT - paddle_height, target_y))
                        else:
                            p2_y = max(0, min(HEIGHT - paddle_height, target_y))

        # Movimento da IA (1 Jogador)
        if game_mode == 1 and not game_over and not is_paused:
            ai_speed = 7.0  # Velocidade ajustada da CPU
            paddle_center = p2_y + paddle_height // 2
            if paddle_center < ball_y:
                p2_y += ai_speed
            elif paddle_center > ball_y:
                p2_y -= ai_speed

            p2_y = max(0, min(HEIGHT - paddle_height, p2_y))

        # 2. Eventos do Pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_pause_rect.collidepoint(event.pos) and not game_over:
                    is_paused = not is_paused
                elif btn_menu_rect.collidepoint(event.pos):
                    game_state = "MENU"

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_p, pygame.K_SPACE) and not game_over:
                    is_paused = not is_paused
                elif event.key in (pygame.K_m, pygame.K_ESCAPE):
                    game_state = "MENU"
                elif game_over and event.key == pygame.K_r:
                    reset_game()

        # 3. Lógica Física do Jogo
        if not game_over and not is_paused:
            if ball_speed_x < MAX_BALL_SPEED:
                ball_speed_x += BALL_ACCELERATION
                ball_speed_y += BALL_ACCELERATION

            current_dir_x = 1 if ball_vel_x > 0 else -1
            current_dir_y = 1 if ball_vel_y > 0 else -1
            ball_vel_x = current_dir_x * ball_speed_x
            ball_vel_y = current_dir_y * ball_speed_y

            ball_x += ball_vel_x
            ball_y += ball_vel_y

            # Colisão Teto / Chão
            if ball_y <= 0 or ball_y >= HEIGHT - ball_size:
                ball_vel_y *= -1

            p1_rect = pygame.Rect(p1_x, p1_y, paddle_width, paddle_height)
            p2_rect = pygame.Rect(p2_x, p2_y, paddle_width, paddle_height)
            ball_rect = pygame.Rect(ball_x, ball_y, ball_size, ball_size)

            # Colisão com Raquete 1
            if ball_rect.colliderect(p1_rect):
                ball_vel_x = abs(ball_vel_x)
                ball_x = p1_x + paddle_width
                ball_speed_x += 0.3

            # Colisão com Raquete 2
            if ball_rect.colliderect(p2_rect):
                ball_vel_x = -abs(ball_vel_x)
                ball_x = p2_x - ball_size
                ball_speed_x += 0.3

            # Pontuação
            if ball_x <= 0:
                p2_score += 1
                reset_point(winner_direction=1)

            elif ball_x >= WIDTH:
                p1_score += 1
                reset_point(winner_direction=-1)

            # Condição de Fim de Jogo
            if p1_score >= max_score:
                game_over = True
                winner_text = "Jogador 1 Venceu!"
            elif p2_score >= max_score:
                game_over = True
                winner_text = (
                    "Computador Venceu!"
                    if game_mode == 1
                    else "Jogador 2 Venceu!"
                )

        # 4. Renderização
        screen.fill(BLACK)

        if current_landmarks:
            draw_hand_landmarks(screen, current_landmarks)

        # Linha central pontilhada
        for y_line in range(0, HEIGHT, 30):
            pygame.draw.rect(screen, WHITE, (WIDTH // 2 - 2, y_line, 4, 15))

        # Raquetes e Bola
        pygame.draw.rect(
            screen, WHITE, pygame.Rect(p1_x, p1_y, paddle_width, paddle_height)
        )
        pygame.draw.rect(
            screen, WHITE, pygame.Rect(p2_x, p2_y, paddle_width, paddle_height)
        )
        if not game_over:
            pygame.draw.rect(
                screen, WHITE, pygame.Rect(ball_x, ball_y, ball_size, ball_size)
            )

        # Placar
        score_text = font.render(f"{p1_score}     {p2_score}", True, WHITE)
        screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 30))

        # Desenhar Botões UI
        draw_ui_buttons(screen)

        # Overlay de Pause
        if is_paused and not game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            pause_render = font.render("JOGO PAUSADO", True, WHITE)
            resume_hint = small_font.render(
                "Pressione 'P' ou Espaço para Continuar", True, WHITE
            )
            screen.blit(
                pause_render,
                (
                    WIDTH // 2 - pause_render.get_width() // 2,
                    HEIGHT // 2 - 40,
                ),
            )
            screen.blit(
                resume_hint,
                (WIDTH // 2 - resume_hint.get_width() // 2, HEIGHT // 2 + 20),
            )

        # Tela de Fim de Jogo
        if game_over:
            win_render = font.render(winner_text, True, WHITE)
            screen.blit(
                win_render,
                (WIDTH // 2 - win_render.get_width() // 2, HEIGHT // 2 - 60),
            )

            restart_render = small_font.render(
                "Pressione 'R' para Reiniciar", True, WHITE
            )
            screen.blit(
                restart_render,
                (
                    WIDTH // 2 - restart_render.get_width() // 2,
                    HEIGHT // 2 + 10,
                ),
            )

            menu_render = small_font.render(
                "Pressione 'M' para Voltar ao Menu", True, WHITE
            )
            screen.blit(
                menu_render,
                (WIDTH // 2 - menu_render.get_width() // 2, HEIGHT // 2 + 50),
            )

        pygame.display.flip()
        clock.tick(60)

# --- ENCERRAMENTO ---
cap.release()
pygame.quit()
sys.exit()222