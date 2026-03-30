import RPi.GPIO as GPIO
import time

SERVO_PIN = 18

# Set up the GPIO numbering mode
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Servos require a 50Hz frequency (a 20ms pulse cycle)
pwm = GPIO.PWM(SERVO_PIN, 50) 

# Start PWM with a 0% duty cycle so it doesn't instantly jitter
pwm.start(0)

def set_angle(angle):
    # This math converts an angle (0 to 180) into the correct duty cycle (2.5 to 12.5)
    duty_cycle = (angle / 18.0) + 2.5
    
    # Temporarily turn on the signal to move the servo
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty_cycle)
    
    # Give the servo time to physically move there
    time.sleep(0.5)
    
    # Turn the signal back off to stop the servo from jittering/buzzing
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

print(f"Testing Servo on BCM Pin {SERVO_PIN}...")

try:
    while True:
        print("Moving to 0 degrees (Left)")
        set_angle(0)
        time.sleep(1)
        
        print("Moving to 90 degrees (Center)")
        set_angle(90)
        time.sleep(1)
        
        print("Moving to 180 degrees (Right)")
        set_angle(180)
        time.sleep(1)
        
        print("Moving back to 90 degrees (Center)")
        set_angle(90)
        time.sleep(1)

except KeyboardInterrupt:
    print("\nExiting test.")
finally:
    # Stop the PWM and clean up the pins
    pwm.stop()
    GPIO.cleanup()
