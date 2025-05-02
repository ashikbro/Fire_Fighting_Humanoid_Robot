import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

class FireDetector:
    def __init__(self, model_path='vision_fire_detection/fire_detection_cnn.h5'):
        self.model = load_model(model_path)
        self.input_size = (128, 128)

    def preprocess(self, frame):
        img = cv2.resize(frame, self.input_size)
        img = img.astype('float32') / 255.0
        img = np.expand_dims(img, axis=0)
        return img

    def detect_fire(self, frame, threshold=0.5):
        """
        Detect fire in the given frame using the trained CNN model.
        Args:
            frame (numpy.ndarray): Input image frame (BGR).
            threshold (float): Probability threshold to classify fire.
        Returns:
            bool: True if fire detected, False otherwise.
        """
        img = self.preprocess(frame)
        pred = self.model.predict(img)[0][0]
        return pred >= threshold

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)  # Use default camera
    if not cap.isOpened():
        print("Error: Could not open video stream.")
        exit()

    detector = FireDetector()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if detector.detect_fire(frame):
            print("Fire detected!")
        else:
            print("No fire detected.")

        cv2.imshow("Fire Detection CNN", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
