import pandas as pd
from sklearn.utils import resample
import os

def augment_dataset(input_path='data/fire_data_bangladesh.csv', output_path='data/fire_data_bangladesh_augmented.csv'):
    if not os.path.exists(input_path):
        print(f"Input dataset file '{input_path}' not found.")
        return

    df = pd.read_csv(input_path)

    # Check class distribution
    class_counts = df['FireSeverity'].value_counts()
    max_count = class_counts.max()

    # Separate classes
    dfs = []
    for cls in class_counts.index:
        df_cls = df[df['FireSeverity'] == cls]
        # Upsample minority classes to max_count
        if len(df_cls) < max_count:
            df_upsampled = resample(df_cls,
                                    replace=True,
                                    n_samples=max_count,
                                    random_state=42)
            dfs.append(df_upsampled)
        else:
            dfs.append(df_cls)

    # Combine all classes
    df_augmented = pd.concat(dfs)

    # Shuffle dataset
    df_augmented = df_augmented.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save augmented dataset
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_augmented.to_csv(output_path, index=False)
    print(f"Augmented dataset saved to '{output_path}'")

if __name__ == "__main__":
    augment_dataset()
