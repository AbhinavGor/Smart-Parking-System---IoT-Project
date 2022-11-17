#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels

#include <Wire.h>  // Only needed for Arduino 1.6.5 and earlier
#include "SH1106.h" //alis for `#include "SH1106Wire.h"`

#include "Graphic_esp8266_dht22_oledi2c.h"

// Initialize the OLED display using Wire library
SH1106Wire display(0x3c, D2, D1);

void setup() {
  // Initialising the UI will init the display too.
  display.init();
  display.flipScreenVertically();
  display.setFont(ArialMT_Plain_16);
  display.setTextAlignment(TEXT_ALIGN_LEFT);

  display.drawString(5, 0, "Hello World");
}

void loop() {
  
}