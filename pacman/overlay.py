import os
import time
import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
import pyautogui
import mediapipe as mp

# ============================================================
# CONFIGURAÇÕES
# ============================================================

pyautogui.PAUSE = 0.0

root = tk.Tk()
SCREEN_WIDTH = root.winfo_screenwidth()
SCREEN_HEIGHT = root.winfo_screenheight()

CENTER_X = SCREEN_WIDTH // 2
CENTER_Y = SCREEN_HEIGHT // 2

# Dimensões dos blocos
BOX_WIDTH = 380
BOX_HEIGHT = 240
MARGIN = 15

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FOV_SCALE = 2.0  

DETECTION_WIDTH = 480
DETECTION_HEIGHT = 270

FRAME_DELAY = 15

# ============================================================
# MEDIAPIPE
# ============================================================

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=0.3,
    min_tracking_confidence=0.3
)

# ============================================================
# TECLAS E POSICIONAMENTO DAS BORDAS
# ============================================================

KEY_MAP = {
    'up': 'up',
    'down': 'down',
    'left': 'left',
    'right': 'right'
}

corners = {
    'up': {
        'x': CENTER_X - BOX_WIDTH // 2,
        'y': MARGIN,
        'w': BOX_WIDTH,
        'h': BOX_HEIGHT,
        'rgb': (0, 255, 0),
        'hex': '#00FF00',
        'active': False
    },
    'down': {
        'x': CENTER_X - BOX_WIDTH // 2,
        'y': SCREEN_HEIGHT - BOX_HEIGHT - MARGIN,
        'w': BOX_WIDTH,
        'h': BOX_HEIGHT,
        'rgb': (255, 0, 0),
        'hex': '#FF0000',
        'active': False
    },
    'left': {
        'x': MARGIN,
        'y': CENTER_Y - BOX_HEIGHT // 2,
        'w': BOX_WIDTH,
        'h': BOX_HEIGHT,
        'rgb': (255, 255, 0),
        'hex': '#FFFF00',
        'active': False
    },
    'right': {
        'x': SCREEN_WIDTH - BOX_WIDTH - MARGIN,
        'y': CENTER_Y - BOX_HEIGHT // 2,
        'w': BOX_WIDTH,
        'h': BOX_HEIGHT,
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
cap.set(cv2.CAP_PROP_FPS, 60)

if not cap.isOpened():
    print("ERRO: Não foi possível abrir a câmera!")
    hands.close()
    exit()

# ============================================================
# JANELA TRANSPARENTE
# ============================================================

root.title("Air Control Overlay")
root.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}+0+0")
root.overrideredirect(True)
root.wm_attributes("-topmost", True)

TRANS_COLOR = '#000001'
root.config(bg=TRANS_COLOR)
root.wm_attributes("-transparentcolor", TRANS_COLOR)

WINDOW_OPACITY = 0.60  
root.wm_attributes("-alpha", WINDOW_OPACITY)

# ============================================================
# CANVAS
# ============================================================

canvas = tk.Canvas(
    root,
    width=SCREEN_WIDTH,
    height=SCREEN_HEIGHT,
    bg=TRANS_COLOR,
    highlightthickness=0
)
canvas.pack(fill="both", expand=True)

# ============================================================
# ELEMENTOS VISUAIS
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
        outline=c['hex'], width=5
    )

    canvas_text_ids[key] = canvas.create_text(
        c['x'] + c['w'] // 2,
        c['y'] + c['h'] // 2,
        text=ARROWS[key],
        fill=c['hex'],
        font=("Arial", 80, "bold")
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
    hands.close()
    root.destroy()

root.bind("<Escape>", on_close)

# ============================================================
# LOOP PRINCIPAL
# ============================================================

HAND_TOUCH_POINTS = [4, 8, 12, 16, 20, 9]

def update_frame():
    ret, frame = cap.read()
    if not ret:
        root.after(30, update_frame)
        return

    frame = cv2.flip(frame, 1)

    # Detecção MediaPipe
    detection_frame = cv2.resize(frame, (DETECTION_WIDTH, DETECTION_HEIGHT), interpolation=cv2.INTER_LINEAR)
    detection_frame_rgb = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2RGB)

    results = hands.process(detection_frame_rgb)

    # Reset de status
    for key in corners:
        corners[key]['active'] = False

    # Detecção multi-pontos da mão
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            for pt_id in HAND_TOUCH_POINTS:
                pt = hand_landmarks.landmark[pt_id]  # Acesso aos landmarks
                hand_x = int(pt.x * SCREEN_WIDTH)
                hand_y = int(pt.y * SCREEN_HEIGHT)

                for key, c in corners.items():
                    if (c['x'] <= hand_x <= c['x'] + c['w']) and (c['y'] <= hand_y <= c['y'] + c['h']):
                        c['active'] = True

    # Pressionamento das teclas via PyAutoGUI
    for key, c in corners.items():
        is_active = c['active']
        key_to_press = KEY_MAP[key]

        if is_active and not last_states[key]:
            pyautogui.keyDown(key_to_press)
            last_states[key] = True
        elif not is_active and last_states[key]:
            pyautogui.keyUp(key_to_press)
            last_states[key] = False

    # Renderização da câmera nas caixas
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h_cam, w_cam, _ = frame_rgb.shape

    for key, c in corners.items():
        center_cam_x = int((c['x'] + c['w'] / 2) / SCREEN_WIDTH * w_cam)
        center_cam_y = int((c['y'] + c['h'] / 2) / SCREEN_HEIGHT * h_cam)

        crop_w = int((c['w'] / SCREEN_WIDTH * w_cam) * CAMERA_FOV_SCALE)
        crop_h = int((c['h'] / SCREEN_HEIGHT * h_cam) * CAMERA_FOV_SCALE)

        x1 = max(0, center_cam_x - crop_w // 2)
        y1 = max(0, center_cam_y - crop_h // 2)
        x2 = min(w_cam, x1 + crop_w)
        y2 = min(h_cam, y1 + crop_h)

        crop = frame_rgb[y1:y2, x1:x2]
        
        if crop.size != 0:
            crop = cv2.resize(crop, (c['w'], c['h']), interpolation=cv2.INTER_LINEAR)
        else:
            crop = np.zeros((c['h'], c['w'], 3), dtype=np.uint8)

        if c['active']:
            overlay_color = np.full_like(crop, c['rgb'])
            crop = cv2.addWeighted(crop, 0.5, overlay_color, 0.5, 0)
            canvas.itemconfig(canvas_rect_ids[key], outline="#FFFFFF", width=7)
            canvas.itemconfig(canvas_text_ids[key], fill="white")
        else:
            canvas.itemconfig(canvas_rect_ids[key], outline=c['hex'], width=5)
            canvas.itemconfig(canvas_text_ids[key], fill=c['hex'])

        img_pil = Image.fromarray(crop)
        img_tk = ImageTk.PhotoImage(image=img_pil)
        tk_images[key] = img_tk
        canvas.itemconfig(canvas_image_ids[key], image=img_tk)

    root.after(FRAME_DELAY, update_frame)

# ============================================================
# INICIALIZAÇÃO
# ============================================================

root.after(0, update_frame)
root.mainloop()