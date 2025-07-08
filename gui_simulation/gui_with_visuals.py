import tkinter as tk
from PIL import Image, ImageTk
import os

class VisualComparisonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Model Comparison Visuals")

        self.images = {
            "Precision-Recall Curve": "model_comparison/precision_recall.png",
            "Confusion Matrix": "model_comparison/confusion_matrix.png"
        }

        self.labels = {}

        for idx, (title, path) in enumerate(self.images.items()):
            label = tk.Label(root, text=title, font=("Arial", 14))
            label.grid(row=idx*2, column=0, padx=10, pady=5)
            self.labels[title] = label

            if os.path.exists(path):
                img = Image.open(path)
                img = img.resize((400, 300), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(root, image=photo)
                img_label.image = photo
                img_label.grid(row=idx*2+1, column=0, padx=10, pady=5)
                self.labels[title+"_img"] = img_label
            else:
                no_img_label = tk.Label(root, text="Image not found")
                no_img_label.grid(row=idx*2+1, column=0, padx=10, pady=5)
                self.labels[title+"_img"] = no_img_label

if __name__ == "__main__":
    root = tk.Tk()
    app = VisualComparisonApp(root)
    root.mainloop()
