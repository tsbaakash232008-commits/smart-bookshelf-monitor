
import cv2

print("MODEL 3 : Capture Only")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not detected")
    exit()

print("Press SPACE twice to capture")

count = 0

while True:

    ret, frame = cap.read()
    cv2.imshow("Camera", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == 32:

        if count == 0:
            cv2.imwrite("before.png", frame)
            print("before.png saved")

        elif count == 1:
            cv2.imwrite("after.png", frame)
            print("after.png saved")
            break

        count += 1

    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()

print("Capture complete")
