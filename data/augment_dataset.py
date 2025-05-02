import pandas as pd
import numpy as np
from sklearn.utils import resample
import os

def augment_dataset(input_path='data/fire_data_bangladesh.csv', output_path='data/fire_data_bangladesh_augmented.csv', augmentation_factor=3):
    """
    Augment the tabular fire severity dataset by resampling and adding noise.

    Parameters:
    - input_path: path to the original dataset CSV
    - output_path: path to save the augmented dataset CSV
    - augmentation_factor: how many times to increase the dataset size
    """
    if not os.path.exists(input_path):
        print(f"Input dataset file {input_path} not found.")
        return

    df = pd.read_csv(input_path)

    # Basic checks for required columns
    required_columns = ['Temperature', 'SmokeDensity', 'GasLevel', 'Humidity', 'FireSeverity']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Missing columns in dataset: {missing_columns}")
        return

    augmented_dfs = [df]

    for i in range(augmentation_factor - 1):
        # Resample with replacement
        resampled_df = resample(df, replace=True, n_samples=len(df), random_state=i)

        # Add small Gaussian noise to numeric columns
        noise_std = {
            'Temperature': 0.5,
            'SmokeDensity': 5,
            'GasLevel': 2,
            'Humidity': 1
        }
        for col in noise_std:
            if col in resampled_df.columns:
                noise = np.random.normal(0, noise_std[col], size=resampled_df.shape[0])
                resampled_df[col] = resampled_df[col] + noise

        augmented_dfs.append(resampled_df)

    augmented_df = pd.concat(augmented_dfs, ignore_index=True)

    # Save augmented dataset
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    augmented_df.to_csv(output_path, index=False)
    print(f"Augmented dataset saved to {output_path}")

if __name__ == "__main__":
    augment_dataset()
