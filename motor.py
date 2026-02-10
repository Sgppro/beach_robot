import RPi.GPIO as GPIO
import time

motor1clk = 17
motor1anti = 27
motor1pwm = 12

GPIO.cleanup()

GPIO.setmode(GPIO.BCM)

GPIO.setup(motor1clk, GPIO.OUT)
GPIO.setup(motor1anti, GPIO.OUT)
GPIO.setup(motor1pwm, GPIO.OUT)

pwm1 = GPIO.PWM(motor1pwm, 1000)
pwm1.start(0)

def stopPwm():
    pwm1.ChangeDutyCycle(0)
    pwm1.stop()

def forward(speed):
    stopPwm()
    GPIO.output(motor1clk, GPIO.HIGH)
    GPIO.output(motor1anti, GPIO.LOW)
    pwm1.ChangeDutyCycle(speed)
    print(speed)


forward(50)
print("a")

while True:
    time.sleep(10)    
