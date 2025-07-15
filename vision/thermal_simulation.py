import numpy as np
import cv2

def estimate_temperature_from_frame(frame: np.ndarray, bounding_box: list) -> float:
    """
    Simulates a thermal camera by estimating the temperature of a fire
    based on the color intensity within its bounding box.

    Args:
        frame: The video frame containing the fire.
        bounding_box: The bounding box of the fire [x1, y1, x2, y2].

    Returns:
        The estimated temperature in Celsius.
    """
    x1, y1, x2, y2 = bounding_box
    fire_roi = frame[y1:y2, x1:x2]

    if fire_roi.size == 0:
        return 25.0  # Ambient temperature

    # Convert to HSV to better isolate color intensity
    hsv_roi = cv2.cvtColor(fire_roi, cv2.COLOR_BGR2HSV)

    # Define range for red/yellow colors (common in fires)
    lower_red = np.array([0, 120, 70])
    upper_red = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv_roi, lower_red, upper_red)

    lower_red = np.array([170, 120, 70])
    upper_red = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv_roi, lower_red, upper_red)

    # Combine the masks
    red_mask = mask1 + mask2

    # Calculate the average intensity of the "hot" pixels
    masked_hsv = cv2.bitwise_and(hsv_roi, hsv_roi, mask=red_mask)
    
    # We'll use the Value channel (intensity) for temperature mapping
    v_channel = masked_hsv[:, :, 2]
    
    # Get all non-zero intensity values
    hot_pixels = v_channel[v_channel > 0]
    
    if hot_pixels.size == 0:
        return 25.0 # Ambient temperature
        
    # Calculate the average intensity of the fire pixels
    average_intensity = np.mean(hot_pixels)
    
    # Map the average intensity to a temperature range (e.g., 100°C to 1000°C)
    # This provides a more nuanced estimation than just pixel count
    ambient_temp = 25.0
    max_fire_temp = 1000.0
    
    # Normalize intensity (0-255) to a 0-1 scale
    normalized_intensity = average_intensity / 255.0
    
    estimated_temp = ambient_temp + (max_fire_temp - ambient_temp) * normalized_intensity

    return estimated_temp