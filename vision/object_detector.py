import cv2
from ultralytics import YOLO

class ObjectDetector:
    """
    A class to handle object detection using the YOLOv8 model.
    """
    def __init__(self, model_path='runs/detect/train/weights/best.pt'):
        """
        Initializes the ObjectDetector with a YOLOv8 model.
        
        Args:
            model_path (str): The path to the YOLOv8 model file.
        """
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            print("Creating a dummy model.")
            self.model = self._create_dummy_model()

    def _create_dummy_model(self):
        class DummyModel:
            def __init__(self):
                self.names = {0: 'person', 1: 'fire'}
            def __call__(self, frame):
                return []
        return DummyModel()

    def detect_objects(self, frame):
        """
        Detects objects in a given frame.
        
        Args:
            frame: The input video frame.
            
        Returns:
            A list of detected objects, where each object is a dictionary
            containing the class name, confidence, and bounding box.
        """
        results = self.model(frame)
        detected_objects = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                confidence = box.conf[0]
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                
                detected_objects.append({
                    'class_name': class_name,
                    'confidence': float(confidence),
                    'bounding_box': [int(x1), int(y1), int(x2), int(y2)]
                })
        return detected_objects

    def draw_boxes(self, frame, detected_objects):
        """
        Draws bounding boxes around the detected objects.
        
        Args:
            frame: The input video frame.
            detected_objects: A list of detected objects.
            
        Returns:
            The frame with bounding boxes drawn on it.
        """
        for obj in detected_objects:
            x1, y1, x2, y2 = obj['bounding_box']
            label = f"{obj['class_name']}: {obj['confidence']:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame