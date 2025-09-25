/*
 * Teensy 4.1 Flow Sensor Reader for RRR
 * Dedicated I2C sensor reader with UART communication to Pi
 * 
 * Hardware:
 * - Teensy 4.1 connected to Pi via USB (Serial)
 * - SLF3S-0600F flow sensor on Teensy I2C (Wire)
 * - 3.3V power for sensor from Teensy
 * 
 * Communication Protocol:
 * Pi → Teensy: {"cmd":"start","rate":50}
 * Teensy → Pi: {"flow":123.4,"temp":25.1,"time":1234567890}
 */

#include <Wire.h>
#include <ArduinoJson.h>

// SLF3S-0600F Configuration
const uint8_t SENSOR_ADDR = 0x08;
const uint16_t START_CMD = 0x3608;  // Start continuous measurement (water mode)
const uint16_t STOP_CMD = 0x3FF9;   // Stop measurement

// Communication settings
const unsigned long BAUD_RATE = 115200;
const size_t JSON_BUFFER_SIZE = 200;

// State variables
bool sensor_running = false;
float sampling_rate = 50.0;  // Hz
unsigned long last_sample_time = 0;
unsigned long sample_interval_us;
uint32_t sample_count = 0;
uint32_t error_count = 0;

// Buffers (ArduinoJson v7+)
JsonDocument command_doc;
JsonDocument response_doc;

void setup() {
  // Initialize serial communication with Pi
  Serial.begin(BAUD_RATE);
  while (!Serial && millis() < 3000) {
    // Wait for serial connection or timeout
  }
  
  // Initialize I2C
  Wire.begin();
  Wire.setClock(100000); // 100kHz for reliable communication
  
  // Initialize sampling interval
  setSamplingRate(sampling_rate);
  
  // Send startup message
  sendStatus("Teensy flow reader initialized");
  
  delay(100);
}

void loop() {
  // Process commands from Pi
  processCommands();
  
  // Sample sensor if running
  if (sensor_running && micros() - last_sample_time >= sample_interval_us) {
    sampleSensor();
    last_sample_time = micros();
  }
  
  // Small delay to prevent overwhelming the loop
  delayMicroseconds(100);
}

void processCommands() {
  if (Serial.available()) {
    String command_str = Serial.readStringUntil('\n');
    command_str.trim();
    
    if (command_str.length() == 0) return;
    
    // Parse JSON command
    DeserializationError error = deserializeJson(command_doc, command_str);
    if (error) {
      sendError("Invalid JSON command");
      return;
    }
    
    String cmd = command_doc["cmd"];
    
    if (cmd == "start") {
      float rate = command_doc["rate"] | 50.0;
      startSensor(rate);
    }
    else if (cmd == "stop") {
      stopSensor();
    }
    else if (cmd == "status") {
      sendSensorStatus();
    }
    else if (cmd == "ping") {
      sendResponse("pong", "");
    }
  else if (cmd == "reset") {
      resetSensor();
  }
    else {
      sendError("Unknown command: " + cmd);
    }
  }
}

void startSensor(float rate) {
  setSamplingRate(rate);
  
  // Send start command to sensor
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(START_CMD >> 8);    // MSB
  Wire.write(START_CMD & 0xFF);  // LSB
  uint8_t result = Wire.endTransmission();
  
  if (result == 0) {
    sensor_running = true;
    sample_count = 0;
    error_count = 0;
    sendStatus("Sensor started at " + String(rate) + " Hz");
  } else {
    sendError("Failed to start sensor, I2C error: " + String(result));
  }
}

void stopSensor() {
  // Send stop command to sensor
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(STOP_CMD >> 8);    // MSB  
  Wire.write(STOP_CMD & 0xFF);  // LSB
  Wire.endTransmission();
  
  sensor_running = false;
  sendStatus("Sensor stopped");
}

// Perform SLF3x soft reset per datasheet: general call 0x00, byte 0x06, wait >= 25 ms
void resetSensor() {
  // Ensure streaming is stopped first (best practice before reset)
  if (sensor_running) {
    stopSensor();
    delay(10);
  }

  // General call reset
  Wire.beginTransmission(0x00);
  Wire.write(0x06);
  uint8_t rc = Wire.endTransmission();

  // Wait for reset completion (datasheet: ~25 ms)
  delay(30);

  // Clear counters and state; do NOT auto-start here (host will issue start)
  sensor_running = false;
  sample_count = 0;
  error_count = 0;

  if (rc == 0) {
    sendStatus("Sensor soft reset completed");
  } else {
    sendError("Sensor soft reset failed, I2C error: " + String(rc));
  }
}

void setSamplingRate(float rate) {
  sampling_rate = constrain(rate, 1.0, 1000.0);
  sample_interval_us = 1000000.0 / sampling_rate;
}

void sampleSensor() {
  // Request 9 bytes from sensor
  uint8_t bytes_received = Wire.requestFrom(SENSOR_ADDR, (uint8_t)9);
  
  if (bytes_received != 9) {
    error_count++;
    if (error_count % 100 == 1) { // Report every 100th error to avoid spam
      sendError("Sensor read failed, received " + String(bytes_received) + " bytes");
    }
    return;
  }
  
  // Read 9-byte frame
  uint8_t data[9];
  for (int i = 0; i < 9; i++) {
    data[i] = Wire.read();
  }
  
  // Parse flow measurement (first 3 bytes)
  uint8_t flow_msb = data[0];
  uint8_t flow_lsb = data[1]; 
  uint8_t flow_crc = data[2];
  
  // Verify CRC for flow measurement
  uint8_t calculated_crc = calculateCRC8(data, 2);
  if (calculated_crc != flow_crc) {
    error_count++;
    if (error_count % 50 == 1) {
      sendError("Flow CRC mismatch");
    }
    return;
  }
  
  // Parse temperature (bytes 3-5)
  uint8_t temp_msb = data[3];
  uint8_t temp_lsb = data[4];
  uint8_t temp_crc = data[5];
  
  calculated_crc = calculateCRC8(data + 3, 2);
  if (calculated_crc != temp_crc) {
    error_count++;
    return; // Skip this sample
  }
  
  // Convert to engineering units
  int16_t flow_raw = (flow_msb << 8) | flow_lsb;
  int16_t temp_raw = (temp_msb << 8) | temp_lsb;
  
  // Handle signed values
  if (flow_raw & 0x8000) flow_raw -= 0x10000;
  if (temp_raw & 0x8000) temp_raw -= 0x10000;
  
  // Apply scaling factors (per SLF3S datasheet)
  float flow_ul_min = flow_raw / 10.0;  // μL/min
  float flow_ml_min = flow_ul_min / 1000.0;  // mL/min  
  float temp_c = temp_raw / 200.0;      // °C
  
  // Send measurement data
  sendMeasurement(flow_ml_min, temp_c);
  sample_count++;
  
  // Reset error count on successful reading
  if (error_count > 0) error_count--;
}

uint8_t calculateCRC8(uint8_t* data, uint8_t len) {
  uint8_t crc = 0xFF;
  for (uint8_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (uint8_t bit = 0; bit < 8; bit++) {
      if (crc & 0x80) {
        crc = (crc << 1) ^ 0x31;
      } else {
        crc = crc << 1;
      }
    }
  }
  return crc;
}

void sendMeasurement(float flow_ml_min, float temp_c) {
  response_doc.clear();
  response_doc["type"] = "measurement";
  response_doc["flow"] = flow_ml_min;
  response_doc["temp"] = temp_c;
  response_doc["time"] = millis();
  response_doc["count"] = sample_count;
  
  serializeJson(response_doc, Serial);
  Serial.println();
}

void sendStatus(String message) {
  response_doc.clear();
  response_doc["type"] = "status";
  response_doc["message"] = message;
  response_doc["running"] = sensor_running;
  response_doc["rate"] = sampling_rate;
  response_doc["errors"] = error_count;
  
  serializeJson(response_doc, Serial);
  Serial.println();
}

void sendError(String error_msg) {
  response_doc.clear();
  response_doc["type"] = "error";
  response_doc["error"] = error_msg;
  response_doc["time"] = millis();
  
  serializeJson(response_doc, Serial);
  Serial.println();
}

void sendResponse(String type, String data) {
  response_doc.clear();
  response_doc["type"] = type;
  if (data.length() > 0) {
    response_doc["data"] = data;
  }
  
  serializeJson(response_doc, Serial);
  Serial.println();
}

void sendSensorStatus() {
  response_doc.clear();
  response_doc["type"] = "sensor_status";
  response_doc["running"] = sensor_running;
  response_doc["rate"] = sampling_rate;
  response_doc["samples"] = sample_count;
  response_doc["errors"] = error_count;
  response_doc["uptime"] = millis();
  
  serializeJson(response_doc, Serial);
  Serial.println();
}
