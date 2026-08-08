#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Wire.h>
#include <BH1750.h>
#include <DHT.h>
#include <ArduinoJson.h>

/******** 引脚 ********/

#define SDA_PIN 5
#define SCL_PIN 6

#define SOIL_PIN 1

#define DHT_PIN 4
#define DHT_TYPE DHT22

#define PUMP_PIN 9

/******** 对象 ********/

BH1750 lightMeter;
DHT dht(DHT_PIN, DHT_TYPE);

/******** WiFi ********/

const char* ssid = "iPhone";
const char* password = "1234567890";

/******** Render API ********/

const char* serverUrl =
"https://plantmeta-api.onrender.com/api/sensor/upload";

WiFiClientSecure client;

/******** 土壤校准 ********/

const int dryValue = 3200;
const int wetValue = 800;

/******** 自动浇水阈值 ********/

float autoWaterThreshold = 30.0;

/******** 水泵状态 ********/

bool pumpStatus = false;

bool watering = false;
unsigned long waterStartTime = 0;
unsigned long waterDuration = 0;

int getFakeSoilRaw() {

    static int value = 2200;

    value += random(-25, 25);   // 小波动
    value += 5;                 // 慢慢变干

    // 模拟浇水
    if (value > 2600) {
        value -= random(500, 900);
    }

    value = constrain(value, 1000, 3000);

    return value;
}

void setup() {

    Serial.begin(115200);

    /******** I2C ********/

    Wire.begin(SDA_PIN, SCL_PIN);

    /******** BH1750 ********/

    if (!lightMeter.begin()) {

        Serial.println("BH1750初始化失败");

    } else {

        Serial.println("BH1750初始化成功");
    }

    /******** DHT22 ********/

    dht.begin();

    Serial.println("DHT22初始化成功");

    /******** 土壤湿度 ********/

    pinMode(SOIL_PIN, INPUT);

    /********水泵 ********/

    pinMode(PUMP_PIN, OUTPUT);

    // 默认关闭水泵
    digitalWrite(PUMP_PIN, LOW);

    /******** WiFi ********/

    WiFi.begin(ssid, password);

    Serial.print("连接WiFi");

    while (WiFi.status() != WL_CONNECTED) {

        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWiFi连接成功");

    Serial.println(WiFi.localIP());

    /******** HTTPS ********/

    client.setInsecure();
}

void loop() {

    /******** 光照 ********/

    float lux = lightMeter.readLightLevel();

    if (lux < 0) {
        lux = 0;
    }

    /******** 土壤湿度 ********/

    int soilRaw = getFakeSoilRaw();

    Serial.print("soilRaw = ");
    Serial.println(soilRaw);

    float soilPercent = map(
        soilRaw,
        dryValue,
        wetValue,
        0,
        100
    );

    soilPercent = constrain(
        soilPercent,
        0,
        100
    );
            Serial.print("soilPercent = ");
    Serial.println(soilPercent);

    /******** DHT22 ********/

    float temp = dht.readTemperature();

    float hum = dht.readHumidity();

    if (isnan(temp) || isnan(hum)) {

        Serial.println("DHT22读取失败");

        temp = 0;
        hum = 0;
    }

    /******** 自动浇水 ********/

    if (soilPercent < autoWaterThreshold) {

        Serial.println("土壤过干");

        Serial.println("启动水泵");

        pumpStatus = true;

        // 打开水泵
        digitalWrite(PUMP_PIN, HIGH);

        delay(700);

        // 关闭水泵
        digitalWrite(PUMP_PIN, LOW);

        pumpStatus = false;

        Serial.println("浇水完成");
    }

    /******** JSON ********/

    String json =
    "{"
    "\"device_id\":\"plant_box_01\","
    "\"plant_id\":\"pothos_01\","
    "\"soil_moisture_raw\":" + String(soilRaw) + ","
    "\"soil_moisture_percent\":" + String(soilPercent,2) + ","
    "\"light_lux\":" + String(lux,2) + ","
    "\"air_temperature\":" + String(temp,2) + ","
    "\"air_humidity\":" + String(hum,2) + ","
    "\"pump_status\":\"" + String(pumpStatus ? "on" : "off") + "\""
    "}";

    /******** 上传 ********/

    HTTPClient http;

    http.begin(client, serverUrl);

    http.addHeader(
        "Content-Type",
        "application/json"
    );

    int code = http.POST(json);

    /******** 检查控制指令（关键就在这里） ********/

    // HTTPClient cmdhttp;
    // cmdhttp.begin("https://plantmeta-api.onrender.com/api/control/latest");

    // int cmdcode = cmdhttp.GET();

    // if (cmdcode == 200) {

    //     String payload = cmdhttp.getString();

    //     StaticJsonDocument<200> doc;
    //     deserializeJson(doc, payload);

    //     String command = doc["command"];
    //     int duration = doc["duration_ms"];

    //     Serial.println(command);
    //     Serial.println(duration);

    //     if (command == "water") {

    //         Serial.println("开始浇水");

    //     watering = true;
    //     waterStartTime = millis();
    //     waterDuration = duration;

    //     digitalWrite(PUMP_PIN, HIGH);

    //     }
    // }

    // cmdhttp.end();

    /******** 串口输出 ********/

    Serial.println("\n======上传======");

    Serial.println(json);

    Serial.print("土壤原始值: ");
    Serial.println(soilRaw);

    Serial.print("土壤湿度: ");
    Serial.print(soilPercent);
    Serial.println("%");

    Serial.print("空气温度: ");
    Serial.print(temp);
    Serial.println(" °C");

    Serial.print("空气湿度: ");
    Serial.print(hum);
    Serial.println("%");

    Serial.print("光照: ");
    Serial.print(lux);
    Serial.println(" lux");

    Serial.print("状态码: ");
    Serial.println(code);

    if (code > 0) {

        Serial.println(http.getString());

    } else {

        Serial.println("上传失败");
    }

    http.end();

    Serial.println("====================");

    delay(5000);

//     if (watering) {

//     if (millis() - waterStartTime >= waterDuration) {

//         digitalWrite(PUMP_PIN, LOW);
//         watering = false;

//         Serial.println("浇水结束");
//     }
// }
}
