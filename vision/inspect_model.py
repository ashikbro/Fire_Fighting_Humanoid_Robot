from tensorflow.keras.models import load_model

def inspect_model_architecture():
    """
    Loads a Keras model and prints its summary to reveal the expected input shape.
    """
    model_path = 'vision_fire_detection/dataset_fire_images/fire_detection_cnn.h5'
    try:
        model = load_model(model_path)
        print("Model loaded successfully. Here is the architecture summary:")
        model.summary()
    except Exception as e:
        print(f"Error loading or inspecting model: {e}")

if __name__ == '__main__':
    inspect_model_architecture()