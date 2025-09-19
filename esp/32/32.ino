#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include <ArduinoJson.h>

using namespace websockets;

// =====================
// Configuración general
// =====================
const char* WIFI_SSID = "OFIClNA";
const char* WIFI_PASSWORD = "45074344";

const char* WS_SERVER = "ws://192.168.37.166:8000/ws/esp";

const int LED_PIN = 2; // LED incorporado ESP32 (GPIO2)

// ===================
// Objetos globales
// ===================
WebsocketsClient webSocket;

// ===================
// Estado del sistema
// ===================
bool isWebSocketConnected = false;
int currentFaceCount = 0;

// ===================
// Prototipos de funciones
// ===================
void setupWiFi();
void setupWebSocket();
void handleWebSocketMessage(const String &message);
void updateLED(int faceCount);
void connectWebSocket();

// ===================
// Setup principal
// ===================
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // LED apagado inicialmente

  setupWiFi();

  webSocket.onMessage([](WebsocketsMessage message) {
    handleWebSocketMessage(message.data());
  });

  webSocket.onEvent([](WebsocketsEvent event, String data) {
    switch (event) {
      case WebsocketsEvent::ConnectionOpened:
        Serial.println("✅ WebSocket conectado");
        isWebSocketConnected = true;
        break;

      case WebsocketsEvent::ConnectionClosed:
        Serial.println("❌ WebSocket desconectado");
        isWebSocketConnected = false;
        break;

      case WebsocketsEvent::GotPing:
        Serial.println("Ping recibido, enviando pong");
        webSocket.pong();
        break;

      case WebsocketsEvent::GotPong:
        Serial.println("Pong recibido");
        break;

      default:
        break;
    }
  });

  connectWebSocket();
}

// ===================
// Loop principal
// ===================
void loop() {
  if (isWebSocketConnected) {
    webSocket.poll();
  } else {
    static unsigned long lastAttemptTime = 0;
    unsigned long now = millis();

    // Reconectar cada 3 segundos
    if (now - lastAttemptTime > 3000) {
      lastAttemptTime = now;
      Serial.println("Intentando reconectar WebSocket...");
      connectWebSocket();
    }
  }

  delay(10);
}

// ===================
// Funciones
// ===================

void setupWiFi() {
  Serial.print("Conectando a WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void connectWebSocket() {
  Serial.println("Conectando al WebSocket...");
  isWebSocketConnected = webSocket.connect(WS_SERVER);

  if (isWebSocketConnected) {
    Serial.println("✅ WebSocket conectado!");
  } else {
    Serial.println("❌ Fallo al conectar WebSocket");
  }
}

void handleWebSocketMessage(const String &message) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, message);

  if (error) {
    Serial.print("❌ JSON inválido: ");
    Serial.println(error.c_str());
    return;
  }

  int faceCount = doc["num_faces"] | 0;
  Serial.printf("👤 Rostros detectados: %d\n", faceCount);

  currentFaceCount = faceCount;
  updateLED(faceCount);
}

void updateLED(int faceCount) {
  if (faceCount > 0) {
    digitalWrite(LED_PIN, HIGH);  // LED ON
  } else {
    digitalWrite(LED_PIN, LOW);   // LED OFF
  }
}
