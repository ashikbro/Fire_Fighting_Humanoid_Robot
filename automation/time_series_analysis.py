import collections
import numpy as np
import logging

class TimeSeriesFlameDetector:
    """
    Time-series analysis for flame presence to reduce false positives.
    Maintains a sliding window of recent flame detection results and confirms
    fire presence based on consistency over time.
    """

    def __init__(self, window_size=5, threshold=0.6):
        """
        :param window_size: Number of recent frames to consider
        :param threshold: Minimum fraction of positive detections to confirm fire
        """
        self.window_size = window_size
        self.threshold = threshold
        self.detections = collections.deque(maxlen=window_size)

    def add_detection(self, detected):
        """
        Add a new detection result (True/False).
        """
        self.detections.append(detected)
        logging.info(f"Added detection: {detected}. Current window: {list(self.detections)}")

    def is_fire_confirmed(self):
        """
        Returns True if the fraction of positive detections in the window exceeds threshold.
        """
        if len(self.detections) < self.window_size:
            return False  # Not enough data yet
        positive_fraction = np.mean(self.detections)
        logging.info(f"Positive detection fraction: {positive_fraction}")
        return positive_fraction >= self.threshold

    def reset(self):
        """
        Reset the detection window.
        """
        self.detections.clear()
        logging.info("Detection window reset.")

if __name__ == "__main__":
    # Example usage
    detector = TimeSeriesFlameDetector(window_size=5, threshold=0.6)
    test_sequence = [False, True, True, True, False, True, True]
    for i, val in enumerate(test_sequence):
        detector.add_detection(val)
        print(f"Frame {i+1}: Detection={val}, Fire Confirmed={detector.is_fire_confirmed()}")
