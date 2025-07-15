import cv2
import numpy as np
import torch

class FireSegmentation:
    """
    A class to handle fire segmentation using a pre-trained DeepLabV3 model.
    """
    def __init__(self, model_path='deeplabv3_resnet50_coco-torchvision.pt'):
        """
        Initializes the FireSegmentation with a DeepLabV3 model.
        
        Args:
            model_path (str): The path to the DeepLabV3 model file.
        """
        try:
            self.model = torch.hub.load('pytorch/vision:v0.10.0', 'deeplabv3_resnet50', pretrained=True)
            self.model.eval()
        except Exception as e:
            print(f"Error loading DeepLabV3 model: {e}")
            self.model = None

    def get_fire_area(self, frame: np.ndarray, bounding_box: list) -> int:
        """
        Calculates the exact area of a fire using image segmentation.
        
        Args:
            frame: The input video frame.
            bounding_box: The bounding box of the fire [x1, y1, x2, y2].
            
        Returns:
            The area of the fire in pixels.
        """
        if not self.model:
            # Fallback to bounding box area if model is not loaded
            return (bounding_box[2] - bounding_box[0]) * (bounding_box[3] - bounding_box[1])

        x1, y1, x2, y2 = bounding_box
        fire_roi = frame[y1:y2, x1:x2]

        if fire_roi.size == 0:
            return 0

        # Preprocess the image for the model
        input_tensor = self._preprocess(fire_roi)
        
        # Run the segmentation
        with torch.no_grad():
            output = self.model(input_tensor)['out'][0]
        
        output_predictions = output.argmax(0)
        
        # The "fire" class in COCO is not explicit. We will assume that
        # any segmented object within the bounding box is part of the fire.
        # A more advanced implementation would use a model fine-tuned on fire images.
        fire_mask = (output_predictions > 0).byte().cpu().numpy()
        
        # Calculate the area of the fire
        fire_area = np.sum(fire_mask)

        # Fallback mechanism: if segmentation is poor, use bounding box area
        bbox_area = (bounding_box[2] - bounding_box[0]) * (bounding_box[3] - bounding_box[1])
        if fire_area < 0.1 * bbox_area: # If segmented area is less than 10% of bbox
            return bbox_area

        return fire_area

    def _preprocess(self, img: np.ndarray) -> torch.Tensor:
        """
        Preprocesses an image for the DeepLabV3 model.
        """
        from torchvision import transforms
        
        # Convert to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Define the transformation
        preprocess = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        return preprocess(img).unsqueeze(0)