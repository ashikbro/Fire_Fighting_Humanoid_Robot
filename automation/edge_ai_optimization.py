import tensorflow as tf
import onnx
import onnxruntime as ort
import numpy as np
import os
import logging

def convert_to_tflite(model_path, tflite_path):
    """
    Convert a TensorFlow model to TensorFlow Lite format with optimization.
    """
    model = tf.keras.models.load_model(model_path)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    with open(tflite_path, 'wb') as f:
        f.write(tflite_model)
    logging.info(f"Converted TensorFlow model to TFLite and saved to {tflite_path}")

def convert_to_onnx(model_path, onnx_path):
    """
    Convert a TensorFlow model to ONNX format.
    """
    import tf2onnx
    model = tf.keras.models.load_model(model_path)
    spec = (tf.TensorSpec(model.input_shape, tf.float32, name="input"),)
    output_path = onnx_path
    model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, output_path=output_path)
    logging.info(f"Converted TensorFlow model to ONNX and saved to {onnx_path}")

def run_tflite_inference(tflite_model_path, input_data):
    """
    Run inference using TensorFlow Lite model.
    """
    interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    return output_data

def run_onnx_inference(onnx_model_path, input_data):
    """
    Run inference using ONNX model.
    """
    session = ort.InferenceSession(onnx_model_path)
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_data})
    return outputs

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Example usage
    tf_model_path = "models/fire_severity_model_DeepLearning.h5"
    tflite_model_path = "models/fire_severity_model_DeepLearning.tflite"
    onnx_model_path = "models/fire_severity_model_DeepLearning.onnx"

    if os.path.exists(tf_model_path):
        convert_to_tflite(tf_model_path, tflite_model_path)
        convert_to_onnx(tf_model_path, onnx_model_path)
    else:
        logging.error(f"TensorFlow model not found at {tf_model_path}")
