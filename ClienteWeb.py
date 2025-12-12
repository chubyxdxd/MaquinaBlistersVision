import asyncio
import websockets
import base64
import numpy as np
import cv2
import threading

import torch
import torch.nn as nn
from torchvision import transforms, models

from scada_server import update_scada, run_scada

RASPI_IP = "192.168.65.95"
WS_PORT = 8765

MODEL_PATH = "resnet_blisters_best.pth"
IMG_SIZE = (224, 224)
CLASSES = ["bueno", "malo", "nada"]
PRED_MAP = {"bueno": 0, "malo": 1, "nada": 2}

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("🔥 PyTorch corriendo en:", device)

print("Cargando modelo RESNET .pth...")

model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, 3)

# CARGAR PESOS
state_dict = torch.load(MODEL_PATH, map_location=device)
model.load_state_dict(state_dict)
model.to(device)
model.eval()

print("✔ Modelo PyTorch cargado correctamente\n")

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize(IMG_SIZE),
    transforms.Normalize((0.5,0.5,0.5),
                         (0.5,0.5,0.5))
])

# SCADA
threading.Thread(target=run_scada, daemon=True).start()

async def listen():
    uri = f"ws://{RASPI_IP}:{WS_PORT}"
    print(f"[PC] Conectando a {uri}...")

    async with websockets.connect(uri) as websocket:
        print("[PC] Conectado ✔")

        while True:
            encoded = await websocket.recv()
            jpg = base64.b64decode(encoded)
            arr = np.frombuffer(jpg, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # frame
            img = transform(frame_rgb)
            img = img.unsqueeze(0).to(device)

            with torch.no_grad():
                logits = model(img)
                probs = torch.softmax(logits, dim=1)[0]
                idx = probs.argmax().item()

            label = CLASSES[idx]
            prob = probs[idx].item()

            print(f"[PC] → {label} ({prob:.4f})")

            update_scada(label, frame_rgb, prob)

            await websocket.send(str(PRED_MAP[label]))


if __name__ == "__main__":
    asyncio.run(listen())
