import RPi.GPIO as GPIO
import time

BUTTON_PIN = 26
DEBOUNCE_TIME = 0.2

# Set up the GPIO numbering mode
GPIO.setmode(GPIO.BCM)

# Set up the pin as an input. 
# (Note: I added a software pull-down resistor just in case your physical button 
# isn't wired with one. This stops the pin from "floating" and triggering randomly).
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def test_callback(channel):
    print("✅ Button pressed! The GPIO setup is working perfectly.")

# Detect the rising edge (when the button is pushed)
GPIO.add_event_detect(BUTTON_PIN, GPIO.RISING, callback=test_callback, bouncetime=int(DEBOUNCE_TIME * 1000))

print(f"Listening for button presses on BCM Pin {BUTTON_PIN}...")
print("Press your button! (Press Ctrl+C to quit)")

try:
    # Keep the script running so it can listen for the event
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nExiting test.")
finally:
    # Always clean up the pins on exit!
    GPIO.cleanup()
