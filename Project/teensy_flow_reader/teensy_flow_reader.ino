/*
 * Teensy 4.1 Flow Sensor Reader for RRR - PRODUCTION VERSION
 * ==========================================================
 * 
 * Dedicated I2C sensor reader with UART communication to Pi
 * 
 * Key Features:
 * - Non-blocking I2C operations with timeout
 * - Automatic bus recovery on lockup
 * - Hardware watchdog with strategic feeding
 * - Activity LED for diagnostics
 * - Fast ping response (< 10ms)
 * 
 * Hardware:
 * - Teensy 4.1 connected to Pi via USB (Serial)
 * - SLF3S-0600F flow sensor on Teensy I2C (Wire)
 * - 3.3V power for sensor from Teensy
 * - 2kΩ pullup resistors on SDA/SCL to 3.3V
 * 
 * Communication Protocol:
 * Pi → Teensy: {"cmd":"start","rate":50}
 * Teensy → Pi: {"type":"measurement","flow":123.4,"temp":25.1}
 * 
 * Best Practices:
 * - Follows Sensirion SLF3x datasheet timing specs
 * - Implements I2C clock stretching tolerance
 * - CRC-8 validation for data integrity
 * - Fail-fast error reporting
 */

#include <Wire.h>
#include <ArduinoJson.h>
#include <Watchdog.h>  // Teensy 4.x hardware watchdog

// SLF3S-0600F I2C Configuration
const uint8_t SENSOR_ADDR = 0x08;
const uint16_t START_CMD = 0x3608;  // Start continuous measurement (water mode)
const uint16_t STOP_CMD = 0x3FF9;   // Stop measurement
const uint8_t RESET_ADDR = 0x00;    // General call address for soft reset
const uint8_t RESET_CMD = 0x06;     // Soft reset command

// Communication settings
const unsigned long BAUD_RATE = 115200;
const size_t JSON_BUFFER_SIZE = 256;

// Timing & Safety (per SLF3x datasheet and best practices)
const unsigned long I2C_TIMEOUT_MS = 300;        // Max time for I2C operation
const unsigned long RESET_WAIT_MS = 30;          // Wait after soft reset (datasheet: min 25ms)
const unsigned long BUS_RECOVERY_DELAY_MS = 50;  // Time for bus to settle after recovery
const unsigned long WATCHDOG_FEED_INTERVAL_MS = 500;  // Feed watchdog every 500ms
const uint16_t MAX_CONSECUTIVE_ERRORS = 200;     // Stop streaming after this many errors (increased for rapid pulse testing with EMI)

// I2C Speed (50kHz for maximum reliability with breadboard + EMI from relays)
const uint32_t I2C_CLOCK_HZ = 50000;

// Activity LED (built-in LED for diagnostics)
const int LED_PIN = LED_BUILTIN;
const unsigned long LED_BLINK_MS = 200;  // Blink every 200ms when active

// State variables
bool sensor_running = false;
float sampling_rate = 50.0;  // Hz
unsigned long last_sample_time = 0;
unsigned long sample_interval_us;
uint32_t sample_count = 0;
uint32_t error_count = 0;
uint32_t consecutive_errors = 0;
unsigned long last_watchdog_feed = 0;
unsigned long last_led_toggle = 0;
bool led_state = false;

// Hardware watchdog
Watchdog watchdog;

// JSON buffers
JsonDocument command_doc;
JsonDocument response_doc;

void setup() {
  // Initialize LED for diagnostics
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);  // LED on during startup
  
  // Initialize serial communication with Pi
  Serial.begin(BAUD_RATE);
  // Don't wait forever for serial - Teensy CDC will enumerate when ready
  unsigned long serial_start = millis();
  while (!Serial && (millis() - serial_start < 2000)) {
    // Wait up to 2 seconds for serial connection
  }
  
  // Initialize I2C with conservative settings
  Wire.begin();
  Wire.setClock(I2C_CLOCK_HZ);
  Wire.setTimeout(I2C_TIMEOUT_MS);  // Set I2C timeout (Teensy 4.x feature)
  
  // Initialize hardware watchdog (2 second timeout for faster recovery)
  // This will reset the Teensy if firmware hangs
  // Using 2s instead of 4s for faster hang detection
  watchdog.enable(Watchdog::TIMEOUT_2S);
  last_watchdog_feed = millis();
  
  // Initialize sampling interval
  setSamplingRate(sampling_rate);
  
  // Perform sensor cold-start initialization (reset + warm-up)
  // This ensures sensor is ready with proper calibration
  Wire.beginTransmission(RESET_ADDR);
  Wire.write(RESET_CMD);
  Wire.endTransmission();
  delay(30);  // Reset completion (datasheet: min 25ms)
  watchdog.reset();
  
  // Send a dummy start to initialize sensor, then stop
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(START_CMD >> 8);
  Wire.write(START_CMD & 0xFF);
  Wire.endTransmission();
  delay(60);  // Warm-up delay (datasheet: typical 60ms)
  watchdog.reset();
  
  // Stop sensor (idle until commanded)
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(STOP_CMD >> 8);
  Wire.write(STOP_CMD & 0xFF);
  Wire.endTransmission();
  delay(10);
  
  // LED off after successful init
  digitalWrite(LED_PIN, LOW);
  
  // Send startup message
  sendStatus("Teensy flow reader initialized (I2C @ " + String(I2C_CLOCK_HZ/1000) + "kHz, watchdog enabled, sensor ready)");
  
  delay(50);
}

void loop() {
  unsigned long now = millis();
  
  // ===== CRITICAL: Feed watchdog regularly =====
  // Feed at start of loop to prevent reset during normal operation
  if (now - last_watchdog_feed >= WATCHDOG_FEED_INTERVAL_MS) {
    watchdog.reset();
    last_watchdog_feed = now;
  }
  
  // ===== Activity LED (diagnostics) =====
  // Blink LED when sensor is running to show firmware is alive
  if (sensor_running) {
    if (now - last_led_toggle >= LED_BLINK_MS) {
      led_state = !led_state;
      digitalWrite(LED_PIN, led_state);
      last_led_toggle = now;
    }
  } else {
    digitalWrite(LED_PIN, LOW);  // LED off when idle
  }
  
  // ===== Process commands from Pi =====
  // Non-blocking serial read
  processCommands();
  
  // ===== Sample sensor if running =====
  if (sensor_running) {
    unsigned long now_us = micros();
    if (now_us - last_sample_time >= sample_interval_us) {
      sampleSensor();
      last_sample_time = now_us;
    }
  }
  
  // ===== Feed watchdog again before loop end =====
  watchdog.reset();
  
  // Small delay to prevent CPU spinning
  delayMicroseconds(100);
}

void processCommands() {
  if (!Serial.available()) return;
  
  // Non-blocking read: read available bytes up to newline or timeout
  String command_str = "";
  unsigned long read_start = millis();
  const unsigned long READ_TIMEOUT_MS = 100;
  
  while (Serial.available() && (millis() - read_start < READ_TIMEOUT_MS)) {
    char c = Serial.read();
    if (c == '\n') break;
    if (c >= 32 && c < 127) {  // Printable ASCII only
      command_str += c;
    }
    if (command_str.length() > 200) {  // Prevent buffer overflow
      sendError("Command too long");
      return;
    }
  }
  
  command_str.trim();
  if (command_str.length() == 0) return;
  
  // Parse JSON command
  DeserializationError error = deserializeJson(command_doc, command_str);
  if (error) {
    sendError("Invalid JSON: " + String(error.c_str()));
    return;
  }
  
  String cmd = command_doc["cmd"];
  
  // ===== FAST PATH: Respond to ping immediately =====
  if (cmd == "ping") {
    sendResponse("pong", "");
    return;  // Don't process further
  }
  
  // ===== Other commands =====
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
  else if (cmd == "reset") {
    resetSensor();
  }
  else {
    sendError("Unknown command: " + cmd);
  }
}

void startSensor(float rate) {
  setSamplingRate(rate);
  
  // Send start command to sensor (skip reset on rapid restarts to avoid watchdog timeout)
  // The sensor maintains its calibration between start/stop cycles
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(START_CMD >> 8);    // MSB
  Wire.write(START_CMD & 0xFF);  // LSB
  uint8_t result = Wire.endTransmission();
  
  if (result == 0) {
    // CRITICAL: Minimal delay for I2C transaction to complete
    // Warm-up (60ms) only needed on cold start, not on restart
    // This allows rapid start/stop cycles during pulse testing
    delay(10);  // Brief settling time
    watchdog.reset();
    
    sensor_running = true;
    sample_count = 0;
    error_count = 0;
    consecutive_errors = 0;
    last_sample_time = micros();
    sendStatus("Sensor started @ " + String(rate) + "Hz");
  } else {
    sendError("Failed to start sensor, I2C error: " + String(result));
  }
}

void stopSensor() {
  // CRITICAL: Set flag FIRST to stop sampling loop immediately
  // This prevents race condition where sampleSensor() continues after stop command
  sensor_running = false;
  
  // Send stop command to sensor hardware
  Wire.beginTransmission(SENSOR_ADDR);
  Wire.write(STOP_CMD >> 8);    // MSB  
  Wire.write(STOP_CMD & 0xFF);  // LSB
  Wire.endTransmission();
  
  // Per SLF3x datasheet: Allow sensor to enter idle mode
  delay(10);  // Brief settling time
  
  // Reset LED to OFF state (critical for diagnostics!)
  digitalWrite(LED_PIN, LOW);
  led_state = false;
  
  sendStatus("Sensor stopped (samples:" + String(sample_count) + ", errors:" + String(error_count) + ")");
}

void resetSensor() {
  // Stop sensor first
  if (sensor_running) {
    stopSensor();
    delay(10);
  }
  
  // Perform I2C bus recovery (in case bus is stuck)
  recoverI2CBus();
  
  // Perform soft reset
  Wire.beginTransmission(RESET_ADDR);
  Wire.write(RESET_CMD);
  uint8_t rc = Wire.endTransmission();
  
  // Wait for reset completion
  delay(RESET_WAIT_MS);
  
  // Feed watchdog
  watchdog.reset();
  
  // Clear state
  sensor_running = false;
  sample_count = 0;
  error_count = 0;
  consecutive_errors = 0;
  
  if (rc == 0) {
    sendStatus("Sensor soft reset OK");
  } else {
    sendError("Sensor soft reset failed, I2C error: " + String(rc));
  }
}

// I2C bus recovery - clears bus lockup conditions
void recoverI2CBus() {
  sendStatus("Recovering I2C bus...");
  
  // 1. End current I2C operation
  Wire.end();
  delay(10);
  
  // 2. Reinitialize I2C
  Wire.begin();
  Wire.setClock(I2C_CLOCK_HZ);
  Wire.setTimeout(I2C_TIMEOUT_MS);
  
  // 3. Wait for bus to settle
  delay(BUS_RECOVERY_DELAY_MS);
  
  // 4. Feed watchdog
  watchdog.reset();
  
  sendStatus("I2C bus recovery complete");
}

void setSamplingRate(float rate) {
  sampling_rate = constrain(rate, 1.0, 1000.0);
  sample_interval_us = 1000000.0 / sampling_rate;
}

void sampleSensor() {
  // ===== Request 9 bytes from sensor with timeout =====
  uint8_t bytes_received = Wire.requestFrom(SENSOR_ADDR, (uint8_t)9);
  
  // Check if I2C operation timed out or returned wrong byte count
  if (bytes_received != 9) {
    consecutive_errors++;
    error_count++;
    
    // Report first error and every 50th error to avoid spam
    if (consecutive_errors == 1 || consecutive_errors % 50 == 0) {
      sendError("Sensor read failed: received " + String(bytes_received) + " bytes (consecutive:" + String(consecutive_errors) + ")");
    }
    
    // ===== CRITICAL: Stop streaming after too many consecutive errors =====
    if (consecutive_errors >= MAX_CONSECUTIVE_ERRORS) {
      sendError("Max consecutive errors reached (" + String(MAX_CONSECUTIVE_ERRORS) + "), stopping sensor");
      sensor_running = false;
      
      // Attempt bus recovery
      recoverI2CBus();
    }
    
    return;
  }
  
  // ===== Read 9-byte frame =====
  uint8_t data[9];
  for (int i = 0; i < 9; i++) {
    if (Wire.available()) {
      data[i] = Wire.read();
    } else {
      consecutive_errors++;
      error_count++;
      sendError("Wire.read() failed at byte " + String(i));
      return;
    }
  }
  
  // ===== Verify CRC for flow measurement (bytes 0-2) =====
  uint8_t flow_crc = data[2];
  uint8_t calculated_flow_crc = calculateCRC8(data, 2);
  if (calculated_flow_crc != flow_crc) {
    consecutive_errors++;
    error_count++;
    if (consecutive_errors % 50 == 1) {
      sendError("Flow CRC mismatch (calc:" + String(calculated_flow_crc) + " exp:" + String(flow_crc) + ")");
    }
    return;
  }
  
  // ===== Verify CRC for temperature (bytes 3-5) =====
  uint8_t temp_crc = data[5];
  uint8_t calculated_temp_crc = calculateCRC8(data + 3, 2);
  if (calculated_temp_crc != temp_crc) {
    consecutive_errors++;
    error_count++;
    return; // Skip this sample silently
  }
  
  // ===== Parse raw values =====
  int16_t flow_raw = (data[0] << 8) | data[1];
  int16_t temp_raw = (data[3] << 8) | data[4];
  
  // Handle signed values (two's complement)
  if (flow_raw & 0x8000) flow_raw -= 0x10000;
  if (temp_raw & 0x8000) temp_raw -= 0x10000;
  
  // ===== Apply scaling factors (per SLF3S-0600F datasheet) =====
  float flow_ul_min = flow_raw / 10.0;       // μL/min (scale factor from datasheet)
  float flow_ml_min = flow_ul_min / 1000.0;  // mL/min
  float temp_c = temp_raw / 200.0;           // °C (scale factor from datasheet)
  
  // ===== Send measurement =====
  sendMeasurement(flow_ml_min, temp_c);
  sample_count++;
  
  // Reset consecutive error counter on successful read
  consecutive_errors = 0;
}

uint8_t calculateCRC8(uint8_t* data, uint8_t len) {
  // Sensirion CRC-8: polynomial 0x31, init 0xFF
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
  // CRITICAL: Check if Serial can accept data (non-blocking)
  // If buffer is full, skip this measurement rather than hanging
  if (Serial.availableForWrite() < 100) {
    // Serial buffer nearly full - skip this sample to prevent blocking
    // This prevents firmware hang during high-rate streaming
    return;
  }
  
  response_doc.clear();
  response_doc["type"] = "measurement";
  response_doc["flow"] = serialized(String(flow_ml_min, 4));  // 4 decimal places
  response_doc["temp"] = serialized(String(temp_c, 3));       // 3 decimal places
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
  response_doc["consecutive_errors"] = consecutive_errors;
  response_doc["uptime"] = millis();
  response_doc["i2c_clock"] = I2C_CLOCK_HZ;
  
  serializeJson(response_doc, Serial);
  Serial.println();
}
