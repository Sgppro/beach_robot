import RPi.GPIO as GPIO
import time

ENA = 12
IN1 = 17
IN2 = 27

ENB = 13
IN3 = 22
IN4 = 23

PWM_FREQ = 100

GPIO.setmode(GPIO.BCM)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
pwm_a = GPIO.PWM(ENA, PWM_FREQ)
pwm_b = GPIO.PWM(ENB, PWM_FREQ)
pwm_a.start(0)
pwm_b.start(0)

def move(speed, direction='forward', motor='left'):
    if speed < 0:
        speed = 0
    elif speed > 100:
        speed = 100

    if motor == "left":
        in1, in2 = IN1, IN2
        pwm = pwm_a
    elif motor == "right":
        in1, in2 = IN3, IN4
        pwm = pwm_b

    if direction == 'forward':
        GPIO.output(in1, GPIO.HIGH)
        GPIO.output(in2, GPIO.LOW)
        print("moving forward")
    elif direction == 'backward':
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.HIGH)
        print("moving backward")
    
    pwm.ChangeDutyCycle(speed)


def stop():
    pwm_a.ChangeDutyCycle(0)
    pwm_b.ChangeDutyCycle(0)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    print("stop")

def cleanup():
    pwm_a.stop()
    pwm_b.stop()
    GPIO.cleanup()



move(100, "forward")
time.sleep(5)
stop()

cleanup()
