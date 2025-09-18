#include <WiFi.h>
#include <ArduinoWebsockets.h>
#include <ArduinoJson.h>

using namespace websockets;


const char* ssid = "OFIClNA";
const char* password = "45074344";
const char* websocket_server = "ws://192.168.101.17:8000/ws/esp";

const int ledPin = 2;


WebsocketsClient client;
bool isConnected = false;


void onMessageCallback(WebsocketsMessage message) {
  String payload = message.data();

  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, payload);

  if (error) {
    Serial.print("Error al parsear JSON: ");
    Serial.println(error.c_str());
    return;
  }

  int num_faces = doc["num_faces"];
  Serial.print("Rostros detectados: ");
  Serial.println(num_faces);

  if (num_faces > 0) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }
}


void onEventsCallback(WebsocketsEvent event, String data) {
  if (event == WebsocketsEvent::ConnectionClosed) {
    Serial.println("WebSocket desconectado");
    isConnected = false;
  } else if (event == WebsocketsEvent::GotPing) {
    client.pong();
  }
}


void setup() {
  Serial.begin(115200);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);


  Serial.print("Conectando a WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());


  client.onMessage(onMessageCallback);
  client.onEvent(onEventsCallback);


  connectWebSocket();
}

void connectWebSocket() {
  Serial.println("Conectando al WebSocket...");
  isConnected = client.connect(websocket_server);

  if (isConnected) {
    Serial.println("✅ WebSocket conectado!");
  } else {
    Serial.println("❌ Fallo al conectar WebSocket");
  }
}

void loop() {
  if (isConnected) {
    client.poll();
  } else {
    Serial.println("Intentando reconectar WebSocket...");
    connectWebSocket();
    delay(2000);
  }

  delay(100);
}