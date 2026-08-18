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
BOX_SIZE = 250

# Resolução da câmera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Resolução usada pelo MediaPipe
DETECTION_WIDTH = 480
DETECTION_HEIGHT = 270

# Aproximadamente 30 FPS
FRAME_DELAY = 33

# Detecta a cada 2 frames
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

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

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
# TECLAS
# ============================================================

KEY_MAP = {
    'topLeft': 'a',
    'bottomLeft': 's',
    'topRight': 'j',
    'bottomRight': 'k'
}


# ============================================================
# QUADRADOS
# ============================================================

corners = {

    'topLeft': {
        'x': 40,
        'y': 40,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (0, 255, 0),
        'hex': '#00FF00',
        'active': False
    },

    'topRight': {
        'x': GAME_WIDTH - BOX_SIZE - 40,
        'y': 40,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (255, 255, 0),
        'hex': '#FFFF00',
        'active': False
    },

    'bottomLeft': {
        'x': 40,
        'y': GAME_HEIGHT - BOX_SIZE - 40,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (255, 0, 0),
        'hex': '#FF0000',
        'active': False
    },

    'bottomRight': {
        'x': GAME_WIDTH - BOX_SIZE - 40,
        'y': GAME_HEIGHT - BOX_SIZE - 40,
        'w': BOX_SIZE,
        'h': BOX_SIZE,
        'rgb': (0, 136, 255),
        'hex': '#0088FF',
        'active': False
    }
}


last_states = {
    key: False
    for key in KEY_MAP
}


# ============================================================
# CÂMERA
# ============================================================

# ABRE A CÂMERA APENAS UMA VEZ
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Configura depois de abrir
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, 30)


# Verifica se abriu corretamente
if not cap.isOpened():
    print("ERRO: Não foi possível abrir a câmera!")
    print("Tente fechar outros programas que estejam usando a webcam.")
    detector.close()
    exit()


print("Câmera aberta com sucesso!")


# ============================================================
# JANELA
# ============================================================

root = tk.Tk()

root.title("Air Guitar Hero Overlay")

root.geometry(
    f"{GAME_WIDTH}x{GAME_HEIGHT}+0+0"
)

root.overrideredirect(True)

root.wm_attributes(
    "-topmost",
    True
)

root.config(
    bg="black"
)

root.wm_attributes(
    "-transparentcolor",
    "black"
)


# ============================================================
# CANVAS
# ============================================================

canvas = tk.Canvas(
    root,
    width=GAME_WIDTH,
    height=GAME_HEIGHT,
    bg="black",
    highlightthickness=0
)

canvas.pack(
    fill="both",
    expand=True
)


# ============================================================
# CRIA OS ELEMENTOS DOS CANTOS
# ============================================================

tk_images = {}
canvas_image_ids = {}
canvas_rect_ids = {}


for key, c in corners.items():

    canvas_image_ids[key] = canvas.create_image(
        c['x'],
        c['y'],
        anchor='nw'
    )

    canvas_rect_ids[key] = canvas.create_rectangle(
        c['x'],
        c['y'],
        c['x'] + c['w'],
        c['y'] + c['h'],
        outline=c['hex'],
        width=3
    )


# ============================================================
# FECHAR
# ============================================================

def on_close(event=None):

    # Solta todas as teclas
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

    global last_timestamp
    global frame_counter
    global last_results


    # --------------------------------------------------------
    # CAPTURA A CÂMERA
    # --------------------------------------------------------

    ret, frame = cap.read()

    if not ret:
        print("Erro ao ler frame da câmera.")
        root.after(100, update_frame)
        return


    # Espelha
    frame = cv2.flip(frame, 1)


    # --------------------------------------------------------
    # FRAME PEQUENO PARA MEDIAPIPE
    # --------------------------------------------------------

    detection_frame = cv2.resize(
        frame,
        (DETECTION_WIDTH, DETECTION_HEIGHT),
        interpolation=cv2.INTER_LINEAR
    )

    detection_frame_rgb = cv2.cvtColor(
        detection_frame,
        cv2.COLOR_BGR2RGB
    )


    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    timestamp = int(
        time.perf_counter() * 1000
    )

    if timestamp <= last_timestamp:
        timestamp = last_timestamp + 1

    last_timestamp = timestamp


    # --------------------------------------------------------
    # DETECÇÃO DA MÃO
    # --------------------------------------------------------

    frame_counter += 1

    # Faz a primeira detecção imediatamente.
    # Depois detecta a cada N frames.
    if (
        last_results is None
        or frame_counter % DETECTION_EVERY_N_FRAMES == 0
    ):

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=detection_frame_rgb
        )

        last_results = detector.detect_for_video(
            mp_image,
            timestamp
        )


    # Usa o último resultado disponível
    results = last_results


    # --------------------------------------------------------
    # RESETA OS CANTOS
    # --------------------------------------------------------

    for key in corners:
        corners[key]['active'] = False


    # --------------------------------------------------------
    # VERIFICA O DEDO INDICADOR
    # --------------------------------------------------------

    if results is not None and results.hand_landmarks:

        for hand_landmarks in results.hand_landmarks:

            # Ponta do dedo indicador
            index_tip = hand_landmarks[8]

            # Coordenadas normalizadas para a tela
            hand_x = int(
                index_tip.x * GAME_WIDTH
            )

            hand_y = int(
                index_tip.y * GAME_HEIGHT
            )


            # Verifica os 4 quadrados
            for key, c in corners.items():

                dentro_x = (
                    c['x']
                    <= hand_x
                    <= c['x'] + c['w']
                )

                dentro_y = (
                    c['y']
                    <= hand_y
                    <= c['y'] + c['h']
                )

                if dentro_x and dentro_y:
                    c['active'] = True


    # --------------------------------------------------------
    # CONTROLE DAS TECLAS
    # --------------------------------------------------------

    for key, c in corners.items():

        is_active = c['active']
        key_to_press = KEY_MAP[key]


        if is_active and not last_states[key]:

            pyautogui.keyDown(key_to_press)
            last_states[key] = True


        elif not is_active and last_states[key]:

            pyautogui.keyUp(key_to_press)
            last_states[key] = False


    # --------------------------------------------------------
    # REDIMENSIONA PARA A TELA
    # --------------------------------------------------------

    display_frame = cv2.resize(
        frame,
        (GAME_WIDTH, GAME_HEIGHT),
        interpolation=cv2.INTER_LINEAR
    )


    frame_rgb = cv2.cvtColor(
        display_frame,
        cv2.COLOR_BGR2RGB
    )


    # --------------------------------------------------------
    # ATUALIZA OS 4 CANTOS
    # --------------------------------------------------------

    for key, c in corners.items():

        crop = frame_rgb[
            c['y']:c['y'] + c['h'],
            c['x']:c['x'] + c['w']
        ].copy()


        # REALCE
        if c['active']:

            overlay_color = np.full_like(
                crop,
                c['rgb']
            )

            crop = cv2.addWeighted(
                crop,
                0.6,
                overlay_color,
                0.4,
                0
            )

            canvas.itemconfig(
                canvas_rect_ids[key],
                outline="#FFFFFF",
                width=6
            )

        else:

            canvas.itemconfig(
                canvas_rect_ids[key],
                outline=c['hex'],
                width=3
            )


        # Evita preto puro porque ele é transparente
        mask = np.all(
            crop == 0,
            axis=2
        )

        crop[mask] = [1, 1, 1]


        # Converte para imagem do Tkinter
        img = Image.fromarray(crop)

        tk_images[key] = ImageTk.PhotoImage(
            image=img
        )

        canvas.itemconfig(
            canvas_image_ids[key],
            image=tk_images[key]
        )


    # --------------------------------------------------------
    # PRÓXIMO FRAME
    # --------------------------------------------------------

    root.after(
        FRAME_DELAY,
        update_frame
    )


# ============================================================
# INICIA
# ============================================================

root.after(0, update_frame)

root.mainloop()