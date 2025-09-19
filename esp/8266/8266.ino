#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// =====================
// Configuración general
// =====================
#define WIFI_SSID "SYSTEM32"
#define WIFI_PASSWORD "edisonp21"

#define WS_HOST "192.168.18.24"
#define WS_PORT 8000
#define WS_PATH "/ws/esp"

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1       // No usamos un pin de reset físico
#define LED_PIN LED_BUILTIN // LED interno del ESP8266 (GPIO2)

// ===================
// Objetos globales
// ===================
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
WebSocketsClient webSocket;

// ===================
// Estado del sistema
// ===================
bool isWebSocketConnected = false;
int currentFaceCount = 0;

// ===================
// Prototipos de funciones
// ===================
void setupWiFi();
void setupOLED();
void setupWebSocket();
void handleWebSocketMessage(const char *message);
void updateDisplay(int faceCount);
void updateLED(int faceCount);

// ===================
// Setup principal
// ===================
void setup()
{
    Serial.begin(115200);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH); // LED apagado (es activo en bajo)

    setupOLED();
    setupWiFi();
    setupWebSocket();
}

// ===================
// Loop principal
// ===================
void loop()
{
    webSocket.loop();
}

// ===================
// Inicializar WiFi
// ===================
void setupWiFi()
{
    display.clearDisplay();
    display.setCursor(0, 0);
    display.setTextSize(1);
    display.setTextColor(WHITE);
    display.println("Conectando a WiFi...");
    display.display();

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Conectando a WiFi");

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\n✅ WiFi conectado");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());

    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("WiFi conectado!");
    display.println(WiFi.localIP());
    display.display();
    delay(1500);
}

// ===================
// Inicializar pantalla OLED
// ===================
void setupOLED()
{
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C))
    {
        Serial.println("❌ No se detectó la pantalla OLED");
        while (true)
            ;
    }

    display.clearDisplay();
    display.setTextColor(WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("Inicializando...");
    display.display();
}

// ===================
// Inicializar WebSocket
// ===================
void setupWebSocket()
{
    webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
    webSocket.setReconnectInterval(3000);

    webSocket.onEvent([](WStype_t type, uint8_t *payload, size_t length)
                      {
    switch (type) {
      case WStype_CONNECTED:
        Serial.println("✅ WebSocket conectado");
        isWebSocketConnected = true;
        display.clearDisplay();
        display.setCursor(0, 0);
        display.setTextSize(1);
        display.println("WS conectado!");
        display.display();
        break;

      case WStype_DISCONNECTED:
        Serial.println("❌ WebSocket desconectado");
        isWebSocketConnected = false;
        display.clearDisplay();
        display.setCursor(0, 0);
        display.setTextSize(1);
        display.println("WS desconectado");
        display.display();
        break;

      case WStype_TEXT:
        payload[length] = '\0';
        handleWebSocketMessage((const char*)payload);
        break;

      default:
        break;
    } });
}

// ===================
// Procesar mensaje JSON
// ===================
void handleWebSocketMessage(const char *message)
{
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, message);

    if (error)
    {
        Serial.print("❌ JSON inválido: ");
        Serial.println(error.c_str());
        return;
    }

    int faceCount = doc["num_faces"] | 0;
    Serial.printf("👤 Rostros detectados: %d\n", faceCount);

    currentFaceCount = faceCount;
    updateDisplay(faceCount);
    updateLED(faceCount);
}

// ===================
// Mostrar datos en OLED
// ===================
void updateDisplay(int faceCount)
{
    display.clearDisplay();
    display.setTextSize(2);
    display.setCursor(0, 10);
    display.print("Rostros:");

    display.setTextSize(3);
    display.setCursor(0, 35);
    display.print(faceCount);
    display.display();
}

// ===================
// Controlar LED
// ===================
void updateLED(int faceCount)
{
    if (faceCount > 0)
    {
        digitalWrite(LED_PIN, LOW); // LED ON (activo en bajo)
    }
    else
    {
        digitalWrite(LED_PIN, HIGH); // LED OFF
    }
}
