# Máquina de Control de Calidad Estadístico de Blisters  
## Documentación de Funcionamiento del Software

Este repositorio contiene el código fuente desarrollado para el prototipo **Máquina de Control de Calidad Estadístico de Blisters de Pastillas con Visión Artificial**, correspondiente a la materia **IMT-313 – Diseño Superior de Ingeniería** (UCB).

El sistema implementa una arquitectura distribuida basada en un **microcontrolador ESP32** y una **Raspberry Pi 5**, comunicados mediante **UART**, donde cada dispositivo cumple un rol específico dentro del proceso de inspección automática y control estadístico.

---

## 1. Arquitectura General del Software

El software del proyecto se divide en cuatro componentes principales:

- **ESP32 (Control de bajo nivel y actuación)**
- **Raspberry Pi 5 (Procesamiento, visión artificial y supervisión)**
- **Sistema de comunicación UART entre ambos dispositivos**
- **Modelo de IA (Red Neuronal) para la clasificación**

Esta separación permite aislar las tareas críticas de control del procesamiento intensivo de imágenes, mejorando la estabilidad y escalabilidad del sistema.

---

## 2. Descripción de los Archivos Principales

### 2.1 `esp32code.ino`

**Dispositivo:** ESP32  
**Lenguaje:** C / C++ (Arduino Framework)

Este archivo corresponde al código que se **carga directamente en el microcontrolador ESP32**.  
Su función principal es el **control del sistema de transporte** y la comunicación con la Raspberry Pi.

#### Funcionalidades principales:
- Definición y configuración de los **pines de entrada y salida** del ESP32.
- Control del **driver de motor 4899**, encargado de accionar la cinta transportadora.
- Inicialización y manejo de la **comunicación UART** con la Raspberry Pi.
- Recepción de comandos desde la Raspberry Pi para:
  - Arrancar la cinta transportadora.
  - Detener la cinta transportadora.
- Ejecución de acciones en tiempo real con baja latencia.

El ESP32 actúa como un **nodo de control de bajo nivel**, enfocado exclusivamente en la ejecución segura y determinista del movimiento mecánico.

---

### 2.2 `clientWeb.py` (Cliente Web / Inferencia)

**Dispositivo:** Raspberry Pi 5 (Si se quiere contar con GPU utilizar una laptop o Jetson).  
**Lenguaje:** Python

Este código implementa el **cliente de inferencia del modelo de visión artificial** basado en una **Red Neuronal Convolucional (CNN)**.

#### Funcionalidades principales:
- Recepción de imágenes preprocesadas del sistema de visión.
- Ejecución de la **inferencia del modelo CNN entrenado**.
- Clasificación del blister en una de las siguientes categorías:
  - `BUENO`
  - `MALO`
  - `NADA` (indeterminado o fuera de categoría)
- Retorno de la predicción al proceso principal del sistema.

Este módulo se centra exclusivamente en la **evaluación del estado del blister**, separando la lógica de inferencia del resto del sistema.

---

### 2.3 `serverWeb.py` (Servidor Principal del Sistema)

**Dispositivo:** Raspberry Pi 5  
**Lenguaje:** Python  
**Paradigma:** Multi-threading

Este archivo corresponde al **núcleo del sistema de control en la Raspberry Pi**.  
Implementa una arquitectura **multi-hilo** para ejecutar múltiples procesos en paralelo.

#### Hilos principales del sistema:

##### a) Hilo de Visión Artificial
- Captura de imágenes desde la cámara USB.
- Ajuste y sintonización de la **iluminación** para condiciones controladas.
- Preprocesamiento de imágenes antes de la inferencia.

##### b) Hilo de Inferencia
- Comunicación con `clientWeb.py`.
- Recepción de la clasificación del blister (`BUENO`, `MALO`, `NADA`).
- Decisión lógica basada en el resultado de la CNN.

##### c) Hilo de Comunicación UART
- Envío de comandos al ESP32 vía UART.
- Control del estado de la cinta transportadora:
  - Continuar movimiento.
  - Detener la cinta en caso de detección de blister defectuoso.
- Recepción de estados o confirmaciones desde el ESP32.

##### d) Hilo SCADA / Registro Estadístico
- Registro de cada blister inspeccionado.
- Almacenamiento de datos estadísticos:
  - Cantidad de blisters buenos.
  - Cantidad de blisters defectuosos.
  - Blisters indeterminados.
- Generación de información para trazabilidad y análisis de calidad.

Este enfoque multi-threading permite que el sistema opere de manera **concurrente**, evitando bloqueos entre captura de imagen, inferencia, control mecánico y registro de datos.

---

### 2.4 `model_cnn.pth` (Modelo de Red Neuronal)

**Formato:** PyTorch State Dictionary (`.pth`)  
**Arquitectura:** Red Neuronal Convolucional (CNN)  

Este archivo binario contiene los **pesos y parámetros entrenados** de la red neuronal. Es el "cerebro" del sistema de visión y es cargado dinámicamente por el script `clientWeb.py` al iniciar el sistema.

#### Características Técnicas del Modelo:
- **Entrada (Input):** Imágenes RGB redimensionadas (224x224 px) y normalizadas.
- **Salida (Output):** Vector de probabilidad para las clases definidas.
- **Clases de Entrenamiento:**
  1. **`BUENO`**: Blister completo con todas las pastillas.
  2. **`MALO`**: Blister con faltantes, roturas o defectos.
  3. **`NADA`**: Fondo vacío o ruido.

#### Recursos de Entrenamiento:
Para reproducir el entrenamiento, re-entrenar la red o auditar los datos utilizados, se proporcionan los siguientes enlaces al código fuente y al dataset de imágenes:

> 🔗 **[Ver Código de Entrenamiento en Google Colab](https://colab.research.google.com/drive/1RS7RVlg0_MqOzIrkuBl7jehC0Q-Pum7k)** > 📂 **[Acceder al Dataset de Imágenes en Google Drive](https://drive.google.com/drive/folders/1TJzuEOMxI42iUzIrMuAyHF2DZ2CWeCAV?usp=drive_link)**

#### Ciclo de Vida:
1. **Carga:** Se inicializa una sola vez al arrancar el sistema para optimizar memoria RAM.
2. **Uso:** Recibe tensores de imagen desde `clientWeb.py` y retorna la predicción.
3. **Mantenimiento:** Este archivo puede ser reemplazado por versiones re-entrenadas sin necesidad de modificar el código fuente principal.

---

## 3. Instalación y Dependencias

Para ejecutar los scripts de Python en la Raspberry Pi, es necesario instalar las librerías listadas en el archivo `requirements.txt`. Este archivo contiene todas las dependencias necesarias para el funcionamiento de la visión artificial y la comunicación serial.

**Comando de instalación:**

```bash
pip install -r requirements.txt
```
## 4. Flujo General de Funcionamiento

1. La cinta transportadora desplaza los blisters hacia la zona de inspección.
2. La cámara captura imágenes bajo iluminación controlada.
3. La Raspberry Pi preprocesa la imagen.
4. El modelo CNN realiza la inferencia del estado del blister.
5. El resultado se evalúa:
   - Si el blister es **BUENO**, la cinta continúa.
   - Si el blister es **MALO** o **NADA**, se envía una orden al ESP32.
6. El ESP32 ejecuta la acción correspondiente sobre el motor.
7. El sistema SCADA registra el resultado para análisis estadístico.

---

## 5. Consideraciones de Diseño

- La comunicación UART se utiliza por su **simplicidad y baja latencia**.
- La separación de tareas entre ESP32 y Raspberry Pi mejora la robustez del sistema.
- El diseño está orientado a un **prototipo académico**, no a una instalación industrial certificada.
- El código está estructurado para permitir futuras mejoras, como:
  - Reentrenamiento de la CNN.
  - Integración con sistemas externos.
  - Escalamiento del sistema de inspección.

---

## 6. Alcance del Software

El software desarrollado permite validar el funcionamiento del prototipo bajo condiciones controladas, garantizando:
- Inspección automática de blisters.
- Clasificación mediante visión artificial.
- Control del transporte basado en decisiones inteligentes.
- Registro estadístico de los resultados de inspección.
