import os
import time
import urllib.request
import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
import pyautogui
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# CONFIGURAÇÕES
# ============================================================

pyautogui.PAUSE = 0.0

GAME_WIDTH = 1280
GAME_HEIGHT = 720

CENTER_X = GAME_WIDTH // 2
CENTER_Y = GAME_HEIGHT // 2

BOX_SIZE = 250
MARGIN = 30

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

DETECTION_WIDTH = 480
DETECTION_HEIGHT = 270

FRAME_DELAY = 33
DETECTION_EVERY_N_FRAMES = 2

frame_counter = 0
last_results = None
last_timestamp = 0


# ============================================================
# MODELO MEDIAPIPE
# ============================================================

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/"
    "hand_landmarker.task"
)

MODEL_PATH = "hand_landmarker.task"

if not os.path.exists(MODEL_PATH):
    print("Baixando modelo do MediaPipe...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Download concluído!")


# ============================================================
# MEDIAPIPE
# ============================================================

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

detector = vision.HandLandmarker.create_from_options(options)


# ============================================================
# TECLAS E QUADRADOS
# ============================================================

KEY_MAP = {
    'up': 'up',
    'down': 'down',
    'left': 'left',
    'right': 'right'
}

corners = {
    'up': {
        'x': CENTER_X - BOX_SIZE // 2,
        'y': MARGIN,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (0, 255, 0),
        'hex': '#00FF00',
        'active': False
    },
    'down': {
        'x': CENTER_X - BOX_SIZE // 2,
        'y': GAME_HEIGHT - BOX_SIZE - MARGIN,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (255, 0, 0),
        'hex': '#FF0000',
        'active': False
    },
    'left': {
        'x': MARGIN,
        'y': CENTER_Y - BOX_SIZE // 2,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (255, 255, 0),
        'hex': '#FFFF00',
        'active': False
    },
    'right': {
        'x': GAME_WIDTH - BOX_SIZE - MARGIN,
        'y': CENTER_Y - BOX_SIZE // 2,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (0, 136, 255),
        'hex': '#0088FF',
        'active': False
    }
}

last_states = {key: False for key in KEY_MAP}


# ============================================================
# CÂMERA
# ============================================================

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("ERRO: Não foi possível abrir a câmera!")
    detector.close()
    exit()

print("Câmera aberta com sucesso!")


# ============================================================
# JANELA
# ============================================================

root = tk.Tk()
root.title("Air Guitar Hero Overlay")
root.geometry(f"{GAME_WIDTH}x{GAME_HEIGHT}+0+0")
root.overrideredirect(True)
root.wm_attributes("-topmost", True)

# Cor chave para transparência alterada para Magenta (evita cortar tons escuros da câmera)
TRANS_COLOR = '#000001'
root.config(bg=TRANS_COLOR)
root.wm_attributes("-transparentcolor", TRANS_COLOR)


# ============================================================
# CANVAS
# ============================================================

canvas = tk.Canvas(
    root,
    width=GAME_WIDTH,
    height=GAME_HEIGHT,
    bg=TRANS_COLOR,
    highlightthickness=0
)
canvas.pack(fill="both", expand=True)


# ============================================================
# ELEMENTOS DOS CANTOS
# ============================================================

tk_images = {}
canvas_image_ids = {}
canvas_rect_ids = {}
canvas_text_ids = {}

ARROWS = {
    'up': '↑',
    'down': '↓',
    'left': '←',
    'right': '→'
}

for key, c in corners.items():
    canvas_image_ids[key] = canvas.create_image(c['x'], c['y'], anchor='nw')
    
    canvas_rect_ids[key] = canvas.create_rectangle(
        c['x'], c['y'],
        c['x'] + c['w'], c['y'] + c['h'],
        outline=c['hex'], width=4
    )

    canvas_text_ids[key] = canvas.create_text(
        c['x'] + c['w'] // 2,
        c['y'] + c['h'] // 2,
        text=ARROWS[key],
        fill=c['hex'],
        font=("Arial", 100, "bold")
    )


# ============================================================
# FECHAR
# ============================================================

def on_close(event=None):
    for key, key_to_press in KEY_MAP.items():
        if last_states[key]:
            pyautogui.keyUp(key_to_press)
            last_states[key] = False

    cap.release()
    detector.close()
    root.destroy()

root.bind("<Escape>", on_close)


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def update_frame():
    global last_timestamp, frame_counter, last_results

    ret, frame = cap.read()
    if not ret:
        root.after(100, update_frame)
        return

    frame = cv2.flip(frame, 1)

    # Detecção MediaPipe
    detection_frame = cv2.resize(frame, (DETECTION_WIDTH, DETECTION_HEIGHT), interpolation=cv2.INTER_LINEAR)
    detection_frame_rgb = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2RGB)

    timestamp = int(time.perf_counter() * 1000)
    if timestamp <= last_timestamp:
        timestamp = last_timestamp + 1
    last_timestamp = timestamp

    frame_counter += 1
    if last_results is None or frame_counter % DETECTION_EVERY_N_FRAMES == 0:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=detection_frame_rgb)
        last_results = detector.detect_for_video(mp_image, timestamp)

    results = last_results

    # Reset de estados atétil
    for key in corners:
        corners[key]['active'] = False

    if results is not None and results.hand_landmarks:
        for hand_landmarks in results.hand_landmarks:
            index_tip = hand_landmarks[8]
            hand_x = int(index_tip.x * GAME_WIDTH)
            hand_y = int(index_tip.y * GAME_HEIGHT)

            for key, c in corners.items():
                if (c['x'] <= hand_x <= c['x'] + c['w']) and (c['y'] <= hand_y <= c['y'] + c['h']):
                    c['active'] = True

    # Trata as entradas do teclado
    for key, c in corners.items():
        is_active = c['active']
        key_to_press = KEY_MAP[key]

        if is_active and not last_states[key]:
            pyautogui.keyDown(key_to_press)
            last_states[key] = True
        elif not is_active and last_states[key]:
            pyautogui.keyUp(key_to_press)
            last_states[key] = False

    # Redimensiona frame principal
    display_frame = cv2.resize(frame, (GAME_WIDTH, GAME_HEIGHT), interpolation=cv2.INTER_LINEAR)
    frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

    # Atualiza as regiões dos cantos com a imagem do vídeo
    for key, c in corners.items():
        crop = frame_rgb[c['y']:c['y'] + c['h'], c['x']:c['x'] + c['w']].copy()

        if c['active']:
            overlay_color = np.full_like(crop, c['rgb'])
            crop = cv2.addWeighted(crop, 0.6, overlay_color, 0.4, 0)

            canvas.itemconfig(canvas_rect_ids[key], outline="#FFFFFF", width=7)
            canvas.itemconfig(canvas_text_ids[key], fill="white")
        else:
            canvas.itemconfig(canvas_rect_ids[key], outline=c['hex'], width=4)
            canvas.itemconfig(canvas_text_ids[key], fill=c['hex'])

        # Converte a matriz NumPy/OpenCV para o formato compatível com Tkinter
        img_pil = Image.fromarray(crop)
        img_tk = ImageTk.PhotoImage(image=img_pil)

        # Salva referência e atualiza o Canvas
        tk_images[key] = img_tk
        canvas.itemconfig(canvas_image_ids[key], image=img_tk)

    root.after(FRAME_DELAY, update_frame)


# ============================================================
# INICIA
# ============================================================

root.after(0, update_frame)
root.mainloop()