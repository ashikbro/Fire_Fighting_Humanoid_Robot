import os
import shutil
import logging

def organize_images(source_fire_dir: str, source_non_fire_dir: str, base_dir: str = 'vision_fire_detection/dataset_fire_images') -> None:
    train_dir = os.path.join(base_dir, 'train')
    val_dir = os.path.join(base_dir, 'val')

    # Create directory structure
    for split in ['train', 'val']:
        for category in ['fire', 'non_fire']:
            dir_path = os.path.join(base_dir, split, category)
            os.makedirs(dir_path, exist_ok=True)

    def move_images(src_dir: str, dest_dir_train: str, dest_dir_val: str) -> None:
        images = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        total = len(images)
        train_count = int(0.8 * total)
        for i, img in enumerate(images):
            src_path = os.path.join(src_dir, img)
            if i < train_count:
                shutil.move(src_path, os.path.join(dest_dir_train, img))
            else:
                shutil.move(src_path, os.path.join(dest_dir_val, img))

    move_images(source_fire_dir, os.path.join(train_dir, 'fire'), os.path.join(val_dir, 'fire'))
    move_images(source_non_fire_dir, os.path.join(train_dir, 'non_fire'), os.path.join(val_dir, 'non_fire'))

    logging.info("Dataset organization complete.")
    logging.info(f"Organized dataset directory: {base_dir}")
    logging.info("Structure:")
    logging.info(f"  train/fire, train/non_fire, val/fire, val/non_fire")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse

    parser = argparse.ArgumentParser(description='Organize fire detection dataset into train/val folders.')
    parser.add_argument('--fire_dir', type=str, required=True, help='Path to directory containing fire images.')
    parser.add_argument('--non_fire_dir', type=str, required=True, help='Path to directory containing non-fire images.')
    parser.add_argument('--output_dir', type=str, default='vision_fire_detection/dataset_fire_images', help='Output base directory.')

    args = parser.parse_args()

    organize_images(args.fire_dir, args.non_fire_dir, args.output_dir)
