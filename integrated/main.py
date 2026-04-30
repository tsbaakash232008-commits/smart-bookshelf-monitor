
import cv2
import serial
import time
import numpy as np

PORT = "COM3"
BAUD = 9600

print("MODEL 1 : Ultrasonic → Capture → Detection")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not detected")
    exit()

print("Camera started")

try:
    arduino = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    print("Arduino connected on", PORT)
except:
    print("Arduino not detected")
    exit()

count = 0

print("Waiting for trigger...")

while True:

    ret, frame = cap.read()

    if not ret:
        continue

    cv2.imshow("Camera", frame)

    if arduino.in_waiting > 0:

        data = arduino.readline().decode(errors="ignore").strip()

        print("Serial:", data)

        if data != "":

            print("Trigger detected")

            if count == 0:
                cv2.imwrite("before.png", frame)
                print("before.png saved")
                count += 1

            elif count == 1:
                cv2.imwrite("after.png", frame)
                print("after.png saved")
                break

            time.sleep(2)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
arduino.close()

print("Running detection...")

before = cv2.imread("before.png")
after = cv2.imread("after.png")

after = cv2.resize(after,(before.shape[1],before.shape[0]))

diff = cv2.absdiff(before,after)
gray = cv2.cvtColor(diff,cv2.COLOR_BGR2GRAY)

_,th = cv2.threshold(gray,25,255,cv2.THRESH_BINARY)

change = np.sum(th)

if change > 500000:
    print("Shelf Change Detected")
else:
    print("No Change Detected")