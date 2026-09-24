import random
import sys
import cv2
import mediapipe as mp
import pygame

# --- CONFIGURAÇÕES INICIAIS ---
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong - Visão Computacional")
clock = pygame.time.Clock()

# Cores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# --- CONFIGURAÇÃO DO MEDIAPIPE (OTIMIZADO) ---
mp_hands = mp.solutions.hands
# model_complexity=0 reduz drasticamente o uso de CPU/GPU mantendo boa precisão para o Pong
hands = mp_hands.Hands(
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6,
)
cap = cv2.VideoCapture(0)
# Reduz a resolução da câmera para acelerar o processamento do OpenCV/MediaPipe
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# --- VARIÁVEIS DO JOGO ---
paddle_width, paddle_height = 15, 100
ball_size = 15

# Posições das Raquetes
p1_x = 35
p1_y = HEIGHT // 2 - paddle_height // 2

p2_x = WIDTH - 50
p2_y = HEIGHT // 2 - paddle_height // 2

# Velocidades e Aceleração
INITIAL_BASE_SPEED = 5.0
MAX_BALL_SPEED = 18.0
BALL_ACCELERATION = 0.005  # Aceleração contínua a cada frame de troca

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
winner_text = ""

game_state = "MENU"
game_mode = 1

font = pygame.font.SysFont("Courier New", 50, bold=True)
small_font = pygame.font.SysFont("Courier New", 24, bold=True)


def reset_point(winner_direction=1):
    """Reinicia a bola e a velocidade base após um ponto."""
    global ball_x, ball_y, ball_speed_x, ball_speed_y, ball_vel_x, ball_vel_y
    ball_speed_x = INITIAL_BASE_SPEED
    ball_speed_y = INITIAL_BASE_SPEED
    ball_x, ball_y = WIDTH // 2, HEIGHT // 2
    ball_vel_x = winner_direction * ball_speed_x
    ball_vel_y = ball_speed_y * random.choice((1, -1))


def reset_game():
    """Reinicia o placar e o estado geral do jogo."""
    global p1_score, p2_score, game_over, p1_y, p2_y
    p1_score = 0
    p2_score = 0
    game_over = False
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

        title_render = font.render("PONG IA", True, WHITE)
        option1_render = small_font.render(
            "Pressione [1] - 1 Jogador (vs CPU)", True, WHITE
        )
        option2_render = small_font.render(
            "Pressione [2] - 2 Jogadores", True, WHITE
        )

        screen.blit(
            title_render,
            (WIDTH // 2 - title_render.get_width() // 2, HEIGHT // 4),
        )
        screen.blit(
            option1_render,
            (WIDTH // 2 - option1_render.get_width() // 2, HEIGHT // 2),
        )
        screen.blit(
            option2_render,
            (WIDTH // 2 - option2_render.get_width() // 2, HEIGHT // 2 + 50),
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
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

        pygame.display.flip()
        clock.tick(60)

    # ---------------------------------------------------------
    # TELA DE JOGO
    # ---------------------------------------------------------
    elif game_state == "PLAYING":

        # 1. Processamento de Visão Computacional
        success, frame = cap.read()
        if success and not game_over:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            if results.multi_hand_landmarks:
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
        if game_mode == 1 and not game_over:
            ai_speed = 5.5
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
            elif event.type == pygame.KEYDOWN:
                if game_over:
                    if event.key == pygame.K_r:
                        reset_game()
                    elif event.key == pygame.K_m:
                        game_state = "MENU"

        # 3. Lógica Física e Movimentação
        if not game_over:
            # Aceleração gradativa da bola enquanto o ponto estiver em disputa
            if ball_speed_x < MAX_BALL_SPEED:
                ball_speed_x += BALL_ACCELERATION
                ball_speed_y += BALL_ACCELERATION

            current_dir_x = 1 if ball_vel_x > 0 else -1
            current_dir_y = 1 if ball_vel_y > 0 else -1
            ball_vel_x = current_dir_x * ball_speed_x
            ball_vel_y = current_dir_y * ball_speed_y

            ball_x += ball_vel_x
            ball_y += ball_vel_y

            # Colisão com o teto e chão
            if ball_y <= 0 or ball_y >= HEIGHT - ball_size:
                ball_vel_y *= -1

            p1_rect = pygame.Rect(p1_x, p1_y, paddle_width, paddle_height)
            p2_rect = pygame.Rect(p2_x, p2_y, paddle_width, paddle_height)
            ball_rect = pygame.Rect(ball_x, ball_y, ball_size, ball_size)

            # Colisão com Raquete 1 (Esquerda)
            if ball_rect.colliderect(p1_rect):
                ball_vel_x = abs(ball_vel_x)  # Força a direção para a direita
                ball_x = p1_x + paddle_width
                ball_speed_x += 0.3  # Bônus extra de velocidade na rebatida

            # Colisão com Raquete 2 (Direita)
            if ball_rect.colliderect(p2_rect):
                ball_vel_x = -abs(ball_vel_x)  # Força a direção para a esquerda
                ball_x = p2_x - ball_size
                ball_speed_x += 0.3

            # Pontuação (Gols)
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

        # Linha pontilhada
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

        # Fim de jogo
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
sys.exit()