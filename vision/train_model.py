from ultralytics import YOLO

def train_fire_detection_model():
    """
    Trains a YOLOv8 model to detect fire based on the provided dataset.
    """
    # Load a pre-trained model
    model = YOLO('yolov8n.pt')

    # Train the model using the 'data.yaml' dataset configuration
    try:
        model.train(data='data.yaml', epochs=50, imgsz=640)
        print("Training complete.")
        # The trained model will be saved in the 'runs/detect/train' directory
        # by default. The best model is usually named 'best.pt'.
    except Exception as e:
        print(f"An error occurred during training: {e}")
        print("Please ensure the dataset is available at the path specified in 'data.yaml'.")

if __name__ == '__main__':
    train_fire_detection_model()