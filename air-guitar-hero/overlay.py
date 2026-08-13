import os
import urllib.request
import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
import pyautogui
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Remove a pausa do pyautogui para resposta imediata das teclas
pyautogui.PAUSE = 0.0

GAME_WIDTH = 1280
GAME_HEIGHT = 720
BOX_SIZE = 180

# 1. Download automático do modelo oficial do MediaPipe Tasks (se ainda não existir)
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = "hand_landmarker.task"

if not os.path.exists(MODEL_PATH):
    print("Baixando modelo oficial do MediaPipe (hand_landmarker.task)... Aguarde um instante.")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Download concluído com sucesso!")

# 2. Inicializa o detector com a nova API do MediaPipe
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(options)

# Teclas enviadas para o Clone Hero / Flash Hero
KEY_MAP = {
    'topLeft': 'a',
    'bottomLeft': 's',
    'topRight': 'j',
    'bottomRight': 'k'
}

corners = {
    'topLeft': {'x': 40, 'y': 40, 'w': BOX_SIZE, 'h': BOX_SIZE, 'rgb': (0, 255, 0), 'hex': '#00FF00', 'active': False},
    'topRight': {'x': GAME_WIDTH - BOX_SIZE - 40, 'y': 40, 'w': BOX_SIZE, 'h': BOX_SIZE, 'rgb': (255, 255, 0), 'hex': '#FFFF00', 'active': False},
    'bottomLeft': {'x': 40, 'y': GAME_HEIGHT - BOX_SIZE - 40, 'w': BOX_SIZE, 'h': BOX_SIZE, 'rgb': (255, 0, 0), 'hex': '#FF0000', 'active': False},
    'bottomRight': {'x': GAME_WIDTH - BOX_SIZE - 40, 'y': GAME_HEIGHT - BOX_SIZE - 40, 'w': BOX_SIZE, 'h': BOX_SIZE, 'rgb': (0, 136, 255), 'hex': '#0088FF', 'active': False}
}

last_states = {key: False for key in KEY_MAP.keys()}

# Inicialização da Webcam
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, GAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, GAME_HEIGHT)

# Criação da Janela com transparência nativa do Windows
root = tk.Tk()
root.title("Air Guitar Hero Overlay")
root.geometry(f"{GAME_WIDTH}x{GAME_HEIGHT}+0+0")
root.overrideredirect(True)              # Sem bordas ou barra de título
root.wm_attributes("-topmost", True)     # Sempre sobreposto ao jogo
root.config(bg='black')
root.wm_attributes("-transparentcolor", "black") # Torna tudo que é PRETO 100% transparente

# Canvas transparente
canvas = tk.Canvas(root, width=GAME_WIDTH, height=GAME_HEIGHT, bg='black', highlightthickness=0)
canvas.pack(fill='both', expand=True)

# Cria as referências visuais dos 4 cantos
tk_images = {}
canvas_image_ids = {}
canvas_rect_ids = {}

for key, c in corners.items():
    canvas_image_ids[key] = canvas.create_image(c['x'], c['y'], anchor='nw')
    canvas_rect_ids[key] = canvas.create_rectangle(
        c['x'], c['y'], c['x'] + c['w'], c['y'] + c['h'],
        outline=c['hex'], width=3
    )

# Fechar apertando ESC
def on_close(event=None):
    cap.release()
    detector.close()
    root.destroy()

root.bind("<Escape>", on_close)

def update_frame():
    ret, frame = cap.read()
    if not ret:
        root.after(10, update_frame)
        return

    # Espelha horizontalmente (efeito espelho)
    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (GAME_WIDTH, GAME_HEIGHT))
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detecção de mãos com a nova API do MediaPipe
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
    results = detector.detect(mp_image)

    # Reseta estados dos cantos
    for key in corners:
        corners[key]['active'] = False

    # Rastreamento da ponta do dedo indicador (landmark 8)
    if results.hand_landmarks:
        for hand_landmarks in results.hand_landmarks:
            index_tip = hand_landmarks[8]
            hand_x = int(index_tip.x * GAME_WIDTH)
            hand_y = int(index_tip.y * GAME_HEIGHT)

            for key, c in corners.items():
                if c['x'] <= hand_x <= c['x'] + c['w'] and c['y'] <= hand_y <= c['y'] + c['h']:
                    c['active'] = True

    # Pressiona e solta as teclas automaticamente
    for key, c in corners.items():
        is_active = c['active']
        key_to_press = KEY_MAP.get(key)
        if key_to_press:
            if is_active and not last_states[key]:
                pyautogui.keyDown(key_to_press)
                last_states[key] = True
            elif not is_active and last_states[key]:
                pyautogui.keyUp(key_to_press)
                last_states[key] = False

    # Renderiza apenas os 4 cantos da câmera
    for key, c in corners.items():
        crop = frame_rgb[c['y']:c['y']+c['h'], c['x']:c['x']+c['w']].copy()
        
        # Evita pixels 0,0,0 puro para não vazar partes da câmera
        crop[crop == 0] = 1

        # Realce visual ao tocar no canto
        if c['active']:
            overlay_color = np.full_like(crop, c['rgb'], dtype=np.uint8)
            crop = cv2.addWeighted(crop, 0.6, overlay_color, 0.4, 0)
            canvas.itemconfig(canvas_rect_ids[key], outline='#FFFFFF', width=6)
        else:
            canvas.itemconfig(canvas_rect_ids[key], outline=c['hex'], width=3)

        # Atualiza o quadro visual no Canvas
        img = Image.fromarray(crop)
        tk_images[key] = ImageTk.PhotoImage(image=img)
        canvas.itemconfig(canvas_image_ids[key], image=tk_images[key])

    # Agenda a execução do próximo quadro
    root.after(10, update_frame)

# Inicia o aplicativo
root.after(10, update_frame)
root.mainloop()