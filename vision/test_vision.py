import cv2
from object_detector import ObjectDetector

def run_multi_object_detection():
    """
    Performs real-time object detection for humans and fire using a YOLOv8 model.
    """
    # Initialize the object detector with the default YOLOv8 model.
    # This model can detect 'person' but not 'fire'.
    # To detect fire, you would need a model trained on a fire dataset.
    detector = ObjectDetector(model_path='yolov8n.pt')

    # Initialize the webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from webcam.")
            break

        # Detect all objects in the frame
        detected_objects = detector.detect_objects(frame)

        # Filter for 'person' and 'fire' detections
        person_detections = [obj for obj in detected_objects if obj['class_name'] == 'person']
        fire_detections = [obj for obj in detected_objects if obj['class_name'] == 'fire']

        # Draw bounding boxes for all desired objects
        frame_with_boxes = detector.draw_boxes(frame, person_detections + fire_detections)

        # Create a status message
        status_items = []
        if person_detections:
            status_items.append(f"Humans: {len(person_detections)}")
        if fire_detections:
            status_items.append(f"Fire: {len(fire_detections)}")
        
        status_text = ", ".join(status_items) if status_items else "No humans or fire detected"
        
        # Display the status on the frame
        cv2.putText(frame_with_boxes, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Display the resulting frame
        cv2.imshow('Multi-Object Detection', frame_with_boxes)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the capture and destroy windows
    cap.release()
    cv2.destroyAllWindows()
    print("Multi-object detection test finished.")

if __name__ == '__main__':
    run_multi_object_detection()