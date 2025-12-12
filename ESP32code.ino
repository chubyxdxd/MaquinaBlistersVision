// =============================
// CONFIGURACIÓN LEDS
// =============================
#define LED_BUENO 2
#define LED_MALO 4
#define LED_NADA 5

// =============================
// CONFIGURACIÓN MOTOR A4988
// =============================
#define dirPin 26
#define stepPin 25
#define enablePin 27
#define stepsPerRevolution 50

bool motorActivo = false;     // estado real del motor
bool enclavadoStop = false;   // enclavamiento de parada
char c = '0';                 // último comando recibido


// =============================
// DETENER MOTOR
// =============================
void detenerMotor() {
  motorActivo = false;
  enclavadoStop = true;          
  digitalWrite(enablePin, HIGH); 
  digitalWrite(stepPin, LOW);
  Serial.println("Motor detenido (3)");
}


// =============================
// ACTIVAR MOTOR
// =============================
void activarMotor() {
  enclavadoStop = false;      
  motorActivo = true;
  digitalWrite(enablePin, LOW);  
  digitalWrite(dirPin, HIGH);    
  Serial.println("Motor activado (2)");
}


// =============================
// MOVER MOTOR
// =============================
void moverMotor() {
  if (!motorActivo) return;   // PROTECCIÓN REAL
  if (enclavadoStop) return;  // PROTECCIÓN REAL

  digitalWrite(dirPin, HIGH);
  digitalWrite(stepPin, HIGH);
  delayMicroseconds(2500);
  digitalWrite(stepPin, LOW);
  delayMicroseconds(2500);
}



// =============================
// SETUP
// =============================
void setup() {
  Serial.begin(115200);

  pinMode(LED_BUENO, OUTPUT);
  pinMode(LED_MALO, OUTPUT);
  pinMode(LED_NADA, OUTPUT);

  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(enablePin, OUTPUT);

  digitalWrite(enablePin, LOW); 

  Serial.println("ESP32 listo.");
}



// =============================
// LOOP PRINCIPAL
// =============================
void loop() {

  // --- UART RECEPTION ---
  if (Serial.available()) {
    c = Serial.read();

    if (c == '\n' || c == '\r') 
      return;

    Serial.print("Recibido: ");
    Serial.println(c);

    digitalWrite(LED_BUENO, LOW);
    digitalWrite(LED_MALO, LOW);
    digitalWrite(LED_NADA, LOW);

    if (c == '2') {
      digitalWrite(LED_NADA, HIGH);
      activarMotor();      
    }
    else if (c == '3') {
      digitalWrite(LED_MALO, HIGH);
      detenerMotor();      
    }
  }

  // --- MOTOR LOOP ---
  moverMotor();
}
