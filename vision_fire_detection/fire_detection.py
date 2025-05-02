import cv2
import numpy as np
from vision_fire_detection.detect_fire_from_image import FireDetector

class FireDetection:
    def __init__(self, method='color_threshold'):
        self.method = method
        if self.method == 'cnn':
            try:
                from vision_fire_detection.detect_fire_from_image import FireDetector
                self.detector = FireDetector()
            except ImportError:
                print("TensorFlow not installed, falling back to color threshold method.")
                self.detector = None
                self.method = 'color_threshold'
        else:
            self.detector = None

    def detect_fire(self, frame):
        if self.method == 'cnn' and self.detector is not None:
            return self.detector.detect_fire(frame)
        else:
            # Default color thresholding method
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_fire = np.array([0, 150, 150])
            upper_fire = np.array([35, 255, 255])
            mask = cv2.inRange(hsv, lower_fire, upper_fire)
            fire_pixels = cv2.countNonZero(mask)
            return fire_pixels > 500

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)  # Use default camera
    if not cap.isOpened():
        print("Error: Could not open video stream.")
        exit()

    # Change method to 'cnn' to use the deep learning model
    fire_detector = FireDetection(method='cnn')

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if fire_detector.detect_fire(frame):
            print("Fire detected!")
        else:
            print("No fire detected.")

        cv2.imshow("Fire Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
