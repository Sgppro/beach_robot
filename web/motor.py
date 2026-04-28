import RPi.GPIO as GPIO
import time

ENA = 12
IN1 = 17
IN2 = 27

ENB = 13
IN3 = 22
IN4 = 23

SERVO = 18

PWM_FREQ = 100
PULSE_MIN = 1.0
PULSE_MAX = 2.0

GPIO.setmode(GPIO.BCM)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setup(SERVO, GPIO.OUT)
pwm_a = GPIO.PWM(ENA, PWM_FREQ)
pwm_b = GPIO.PWM(ENB, PWM_FREQ)
pwm_a.start(0)
pwm_b.start(0)
pwm_s = GPIO.PWM(SERVO, PWM_FREQ)
pwm_s.start(0)


def angle_to_duty(angle):
    pulse_width = PULSE_MIN + (angle / 180.0) * (PULSE_MAX - PULSE_MIN)
    duty = (pulse_width / 20.0) * 100.0
    return duty

def set_angle(pwm, angle):
    duty = angle_to_duty(angle)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.3) 


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

def straight(speed, direction):
    if direction == 1:
        move(speed, "forward", "left")
        move(speed, "forward", "right")
    elif direction == 0:
        move(speed, "backward", "left")
        move(speed, "backward", "right")


class MotorController:
    def execute(self, command):
        if command == "stop":
            stop()
straight(100, 0)
time.sleep(1.5)
stop()
set_angle(pwm_s, 125)
time.sleep(0.5)
straight(100, 1)
time.sleep(7)
stop()
set_angle(pwm_s, 100)
cleanup()
