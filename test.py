import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
LED_PIN = 12
PWM_FREQ = 100
GPIO.setup(LED_PIN, GPIO.OUT)

pwm = GPIO.PWM(LED_PIN, PWM_FREQ)
pwm.start(0)
try:
    while True:
        for i in range(0,101,5):
            pwm.ChangeDutyCycle(i)
            time.sleep(0.05)

        for i in range(100,-1,-5):
            pwm.ChangeDutyCycle(i)
            time.sleep(0.05)
except KeyboardInterrupt:
    GPIO.cleanup()
    pwm.stop()


