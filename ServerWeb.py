#!/usr/bin/env python3
import cv2
import numpy as np
import math
import time

import asyncio
import websockets
import base64
import threading
import queue
import serial

# ============================
# CONFIG
# ============================
WS_PORT = 8765
IMG_SIZE = (224, 224)

UART_PORT = "/dev/ttyUSB0"
UART_BAUD = 115200

frame_queue = queue.Queue()
last_prediction = None
prediction_ready = False

uart_msg = None


# ============================
# UART THREAD
# ============================
def uart_thread():
    global uart_msg
    print("[UART] Inicializando UART...")

    try:
        ser = serial.Serial(UART_PORT, UART_BAUD, timeout=1)
        print(f"[UART] UART conectado a {UART_PORT} ✔")
    except Exception as e:
        print(f"[UART] ERROR UART: {e}")
        return

    while True:
        if uart_msg is not None:
            ser.write((uart_msg + "\n").encode("utf-8"))
            print(f"[UART] → Enviado a ESP32: {uart_msg}")
            uart_msg = None
        time.sleep(0.01)



# ============================
# WEBSOCKET SERVER
# ============================
async def handler(websocket):
    global last_prediction, prediction_ready

    print("[WS] Laptop conectada ✔")

    while True:
        if not frame_queue.empty():
            img = frame_queue.get()

            ok, buffer = cv2.imencode(".jpg", img)
            if ok:
                encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")
                await websocket.send(encoded)
                print("[WS] Imagen enviada a laptop")

            pred = await websocket.recv()
            print(f"[WS] Predicción recibida: {pred}")

            last_prediction = pred
            prediction_ready = True

        await asyncio.sleep(0.01)


async def ws_main():
    async with websockets.serve(handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()


def ws_thread():
    asyncio.run(ws_main())



# ============================
# CONTROLES DE CÁMARA
# ============================
def nothing(x): pass

cv2.namedWindow("Ajustes", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Ajustes", 400, 500)

cv2.createTrackbar("Kernel", "Ajustes", 18, 31, nothing)
cv2.createTrackbar("Canny1", "Ajustes", 2, 255, nothing)
cv2.createTrackbar("Canny2", "Ajustes", 127, 255, nothing)
cv2.createTrackbar("CloseK", "Ajustes", 18, 50, nothing)
cv2.createTrackbar("MinArea", "Ajustes", 1500, 20000, nothing)

cv2.createTrackbar("CircleX", "Ajustes", 653, 1280, nothing)
cv2.createTrackbar("CircleY", "Ajustes", 240, 960, nothing)
cv2.createTrackbar("Radius", "Ajustes", 120, 800, nothing)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ No se pudo abrir la cámara")
    exit()

# ======================================================
# 🔥🔥🔥 MEJORA DE ENFOQUE Y BRILLO (AGREGADO)
# ======================================================

# Apagar auto enfoque (si la cámara lo soporta)
cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)

# Enfoque fijo (prueba entre 0 y 255)
cap.set(cv2.CAP_PROP_FOCUS, 20)

# Bajar brillo de la cámara
cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.3)

# Reducir exposición para evitar blur
cap.set(cv2.CAP_PROP_EXPOSURE, -6)

print("Detector listo. ESC para salir.")



# ============================
# FSM EXACTA ORIGINAL
# ============================
machine_state = 0
prev_state = None
prediction_ready_flag = False

prev_centered = False

last_trigger_time = 0
COOLDOWN_SEC = 0.8



# ============================
# ARRANCAR HILOS
# ============================
threading.Thread(target=uart_thread, daemon=True).start()
threading.Thread(target=ws_thread, daemon=True).start()



# ============================
# LOOP PRINCIPAL
# ============================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # --------------------------
    # SI QUIERES AÚN MÁS OSCURO:
    # frame = cv2.convertScaleAbs(frame, alpha=1, beta=-40)
    # --------------------------

    h, w = frame.shape[:2]

    k = cv2.getTrackbarPos("Kernel", "Ajustes")
    if k % 2 == 0:
        k += 1

    t1 = cv2.getTrackbarPos("Canny1", "Ajustes")
    t2 = cv2.getTrackbarPos("Canny2", "Ajustes")
    close_k = cv2.getTrackbarPos("CloseK", "Ajustes")
    min_area = cv2.getTrackbarPos("MinArea", "Ajustes")

    circle_x = cv2.getTrackbarPos("CircleX", "Ajustes")
    circle_y = cv2.getTrackbarPos("CircleY", "Ajustes")
    circle_r = cv2.getTrackbarPos("Radius", "Ajustes")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (k, k), 0)
    edges = cv2.Canny(blur, t1, t2)

    mk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_k, close_k))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, mk)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_cnt = None
    best_area = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area and area > best_area:
            best_area = area
            best_cnt = cnt

    centered = False
    text = "NO SE DETECTA BLISTER"
    color = (0, 255, 255)

    cv2.circle(frame, (circle_x, circle_y), circle_r, (180, 180, 180), 2)

    if best_cnt is not None:
        x, y, bw, bh = cv2.boundingRect(best_cnt)
        M = cv2.moments(best_cnt)

        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            cv2.circle(frame, (cx, cy), 5, (0, 255, 255), -1)
            cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

            dist = math.hypot(cx - circle_x, cy - circle_y)

            if dist <= circle_r:
                centered = True
                text = "BLISTER CENTRADO (1)"
                color = (0, 255, 0)

    cv2.putText(frame, text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    now = time.time()

    if machine_state == 0:
        uart_msg = "2"

        if centered:
            machine_state = 1
            last_trigger_time = now
            print("→ FSM: Estado 1 (centrado detectado)")

    elif machine_state == 1:
        uart_msg = "3"
        print("[FSM] UART=3 enviado")

        time.sleep(3)
        print("[FSM] Delay de 3 segundos completado. Enviando frame al WS...")

        img_send = cv2.resize(frame, IMG_SIZE)
        img_send = cv2.cvtColor(img_send, cv2.COLOR_BGR2RGB)
        frame_queue.put(img_send)
        print("[WS] Frame enviado a laptop")

        while not prediction_ready:
            time.sleep(0.01)

        print("[WS] Predicción recibida:", last_prediction)
        prediction_ready = False

        machine_state = 2

    elif machine_state == 2:
        uart_msg = "2"
        last_trigger_time = now
        machine_state = 3

    elif machine_state == 3:
        if (now - last_trigger_time) >= 1:
            machine_state = 0

    cv2.imshow("Frame", frame)
    cv2.imshow("Edges", edges)
    cv2.imshow("Closed", closed)

    if cv2.waitKey(10) & 0xFF == 27:
        break

cv2.destroyAllWindows()
