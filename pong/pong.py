import random
import sys
import cv2
import mediapipe as mp
import pygame

# --- CONFIGURAÇÕES INICIAIS ---
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong - Visão Computacional (2 Jogadores)")
clock = pygame.time.Clock()

# Cores (Estilo Clássico / Retrô)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# --- CONFIGURAÇÃO DO MEDIAPIPE (VISÃO COMPUTACIONAL) ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7
)
cap = cv2.VideoCapture(0)

# --- VARIÁVEIS DO JOGO ---
paddle_width, paddle_height = 15, 100
ball_size = 15

# Posições das Raquetes (Jogador 1 na esquerda, Jogador 2 na direita)
p1_x = 35
p1_y = HEIGHT // 2 - paddle_height // 2

p2_x = WIDTH - 50
p2_y = HEIGHT // 2 - paddle_height // 2

# Velocidades
INITIAL_BASE_SPEED = 5.0
ball_speed_x = INITIAL_BASE_SPEED
ball_speed_y = INITIAL_BASE_SPEED

# Bola
ball_x = WIDTH // 2
ball_y = HEIGHT // 2
ball_vel_x = -ball_speed_x * random.choice((1, -1))
ball_vel_y = -ball_speed_y * random.choice((1, -1))

# Placar e Limite
p1_score = 0
p2_score = 0
max_score = 7
game_over = False
winner_text = ""

font = pygame.font.SysFont("Courier New", 50, bold=True)
small_font = pygame.font.SysFont("Courier New", 30, bold=True)

# --- LOOP PRINCIPAL DO JOGO ---
running = True
while running:
  # 1. Captura e Processamento da Câmera (Visão Computacional)
  success, frame = cap.read()
  if success and not game_over:
    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
      for hand_landmarks in results.multi_hand_landmarks:
        wrist_x = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].x
        index_y = hand_landmarks.landmark[
            mp_hands.HandLandmark.INDEX_FINGER_TIP
        ].y
        target_y = int(index_y * HEIGHT) - paddle_height // 2

        if wrist_x < 0.5:
          p1_y = max(0, min(HEIGHT - paddle_height, target_y))
        else:
          p2_y = max(0, min(HEIGHT - paddle_height, target_y))

  # 2. Eventos do Pygame
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      running = False
    elif event.type == pygame.KEYDOWN:
      if game_over and event.key == pygame.K_r:
        # Reinicia o jogo se apertar 'R'
        p1_score = 0
        p2_score = 0
        game_over = False
        ball_speed_x = INITIAL_BASE_SPEED
        ball_speed_y = INITIAL_BASE_SPEED
        ball_x, ball_y = WIDTH // 2, HEIGHT // 2
        ball_vel_x = -ball_speed_x * random.choice((1, -1))
        ball_vel_y = -ball_speed_y * random.choice((1, -1))

  # 3. Lógica Física do Jogo (Apenas se o jogo não acabou)
  if not game_over:
    total_score = p1_score + p2_score

    # Mantém a direção atual proporcional à velocidade atual
    current_dir_x = 1 if ball_vel_x > 0 else -1
    current_dir_y = 1 if ball_vel_y > 0 else -1
    ball_vel_x = current_dir_x * ball_speed_x
    ball_vel_y = current_dir_y * ball_speed_y

    ball_x += ball_vel_x
    ball_y += ball_vel_y

    # Colisão com as paredes superior e inferior
    if ball_y <= 0 or ball_y >= HEIGHT - ball_size:
      ball_vel_y *= -1

    # Retângulos para colisão
    p1_rect = pygame.Rect(p1_x, p1_y, paddle_width, paddle_height)
    p2_rect = pygame.Rect(p2_x, p2_y, paddle_width, paddle_height)
    ball_rect = pygame.Rect(ball_x, ball_y, ball_size, ball_size)

    # Colisão com a raquete do Jogador 1 (Esquerda)
    if ball_rect.colliderect(p1_rect):
      ball_vel_x *= -1
      ball_x = p1_x + paddle_width
      # Aceleração fixa boa ao rebater (caso já tenha passado de 3 pontos no total)
      if total_score >= 3 and ball_speed_x < 15:
        ball_speed_x += 0.4
        ball_speed_y += 0.4

    # Colisão com a raquete do Jogador 2 (Direita)
    if ball_rect.colliderect(p2_rect):
      ball_vel_x *= -1
      ball_x = p2_x - paddle_width
      if total_score >= 3 and ball_speed_x < 15:
        ball_speed_x += 0.4
        ball_speed_y += 0.4

    # Pontuação (Gols)
    if ball_x <= 0:
      p2_score += 1
      # Define a nova velocidade inicial com base na pontuação total atualizada
      new_total = p1_score + p2_score
      if new_total >= 3:
        ball_speed_x = INITIAL_BASE_SPEED * 1.5
        ball_speed_y = INITIAL_BASE_SPEED * 1.5
      else:
        ball_speed_x = INITIAL_BASE_SPEED
        ball_speed_y = INITIAL_BASE_SPEED

      ball_x, ball_y = WIDTH // 2, HEIGHT // 2
      ball_vel_x = ball_speed_x
      ball_vel_y = ball_speed_y * random.choice((1, -1))

    elif ball_x >= WIDTH:
      p1_score += 1
      new_total = p1_score + p2_score
      if new_total >= 3:
        ball_speed_x = INITIAL_BASE_SPEED * 1.5
        ball_speed_y = INITIAL_BASE_SPEED * 1.5
      else:
        ball_speed_x = INITIAL_BASE_SPEED
        ball_speed_y = INITIAL_BASE_SPEED

      ball_x, ball_y = WIDTH // 2, HEIGHT // 2
      ball_vel_x = -ball_speed_x
      ball_vel_y = ball_speed_y * random.choice((1, -1))

    # Verifica se alguém chegou a 10 pontos
    if p1_score >= max_score:
      game_over = True
      winner_text = "Jogador 1 Venceu!"
    elif p2_score >= max_score:
      game_over = True
      winner_text = "Jogador 2 Venceu!"

  # 4. Renderização (Estilo Retrô Original)
  screen.fill(BLACK)

  # Linha central pontilhada
  for y_line in range(0, HEIGHT, 30):
    pygame.draw.rect(screen, WHITE, (WIDTH // 2 - 2, y_line, 4, 15))

  # Desenha raquetes e bola
  pygame.draw.rect(screen, WHITE, pygame.Rect(p1_x, p1_y, paddle_width, paddle_height))
  pygame.draw.rect(screen, WHITE, pygame.Rect(p2_x, p2_y, paddle_width, paddle_height))
  if not game_over:
    pygame.draw.rect(screen, WHITE, pygame.Rect(ball_x, ball_y, ball_size, ball_size))

  # Desenha o Placar
  score_text = font.render(f"{p1_score}     {p2_score}", True, WHITE)
  screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 30))

  # Tela de Fim de Jogo
  if game_over:
    win_render = font.render(winner_text, True, WHITE)
    screen.blit(
        win_render, (WIDTH // 2 - win_render.get_width() // 2, HEIGHT // 2 - 50)
    )

    restart_render = small_font.render(
        "Pressione 'R' para Reiniciar", True, WHITE
    )
    screen.blit(
        restart_render,
        (WIDTH // 2 - restart_render.get_width() // 2, HEIGHT // 2 + 20),
    )

  # Atualiza a tela
  pygame.display.flip()
  clock.tick(60)

# --- ENCERRAMENTO ---
cap.release()
pygame.quit()
sys.exit()