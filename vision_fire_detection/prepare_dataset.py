import os
import urllib.request
import zipfile
import shutil

def download_and_extract(url, extract_to):
    zip_path = os.path.join(extract_to, 'temp.zip')
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)
    print(f"Downloading dataset from {url}...")
    urllib.request.urlretrieve(url, zip_path)
    print("Download complete. Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(zip_path)
    print(f"Extracted to {extract_to}")

def prepare_fire_dataset(base_dir='vision_fire_detection/dataset_fire_images'):
    import os
    skip_download = os.getenv('SKIP_DATASET_DOWNLOAD', '0') == '1'
    if skip_download:
        print("Skipping dataset download due to SKIP_DATASET_DOWNLOAD environment variable.")
        return

    # URLs for sample fire and non-fire image datasets (public datasets)
    fire_url = 'https://github.com/Aravindlivewire/Fire-Detection-Dataset/raw/master/Fire_Dataset.zip'
    non_fire_url = 'https://github.com/Aravindlivewire/Fire-Detection-Dataset/raw/master/NonFire_Dataset.zip'

    train_dir = os.path.join(base_dir, 'train')
    val_dir = os.path.join(base_dir, 'val')

    # Create directory structure
    for split in ['train', 'val']:
        for category in ['fire', 'non_fire']:
            dir_path = os.path.join(base_dir, split, category)
            os.makedirs(dir_path, exist_ok=True)

    # Download and extract fire images
    fire_extract_dir = os.path.join(base_dir, 'fire_temp')
    download_and_extract(fire_url, fire_extract_dir)

    # Download and extract non-fire images
    non_fire_extract_dir = os.path.join(base_dir, 'non_fire_temp')
    download_and_extract(non_fire_url, non_fire_extract_dir)

    # Move images to train and val folders (simple split: 80% train, 20% val)
    def move_images(src_dir, dest_dir_train, dest_dir_val):
        images = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        total = len(images)
        train_count = int(0.8 * total)
        for i, img in enumerate(images):
            src_path = os.path.join(src_dir, img)
            if i < train_count:
                shutil.move(src_path, os
            else:
                shutil.move(src_path, os.path.join(dest_dir_val, img))

    move_images(fire_extract_dir, os.path.join(train_dir, 'fire'), os.path.join(val_dir, 'fire'))
    move_images(non_fire_extract_dir, os.path.join(train_dir, 'non_fire'), os.path.join(val_dir, 'non_fire'))

    # Cleanup temp directories
    shutil.rmtree(fire_extract_dir)
    shutil.rmtree(non_fire_extract_dir)

    print("Dataset preparation complete.")
    print(f"Dataset directory: {base_dir}")
    print("Structure:")
    print(f"  train/fire, train/non_fire, val/fire, val/non_fire")

if __name__ == "__main__":
    prepare_fire_dataset()
