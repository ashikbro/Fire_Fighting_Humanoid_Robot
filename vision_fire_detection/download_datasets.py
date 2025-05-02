import os
import requests
import zipfile
import io

def download_and_extract_zip(url, extract_to):
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)
    print(f"Downloading from {url} ...")
    response = requests.get(url)
    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Extracted to {extract_to}")
    else:
        print(f"Failed to download from {url}, status code: {response.status_code}")

def download_fire_datasets(base_dir='vision_fire_detection/Datasets'):
    import os
    skip_download = os.getenv('SKIP_DATASET_DOWNLOAD', '0') == '1'
    if skip_download:
        print("Skipping dataset download due to SKIP_DATASET_DOWNLOAD environment variable.")
        return

    fire_url = 'https://github.com/Aravindlivewire/Fire-Detection-Dataset/archive/refs/heads/master.zip'
    non_fire_url = 'https://github.com/Aravindlivewire/Fire-Detection-Dataset/archive/refs/heads/master.zip'  # Same repo, will extract both

    download_and_extract_zip(fire_url, base_dir)

    # After extraction, move fire and non-fire images to separate folders
    extracted_dir = os.path.join(base_dir, 'Fire-Detection-Dataset-master')
    fire_src = os.path.join(extracted_dir, 'Fire_Dataset')
    non_fire_src = os.path.join(extracted_dir, 'NonFire_Dataset')

    fire_dest = os.path.join(base_dir, 'fire_images')
    non_fire_dest = os.path.join(base_dir, 'non_fire_images')

    if not os.path.exists(fire_dest):
        os.makedirs(fire_dest)
    if not os.path.exists(non_fire_dest):
        os.makedirs(non_fire_dest)

    # Move files from source to destination
    for filename in os.listdir(fire_src):
        src_file = os.path.join(fire_src, filename)
        dst_file = os.path.join(fire_dest, filename)
        if os.path.isfile(src_file):
            os.rename(src_file, dst_file)

    for filename in os.listdir(non_fire_src):
        src_file = os.path.join(non_fire_src, filename)
        dst_file = os.path.join(non_fire_dest, filename)
        if os.path.isfile(src_file):
            os.rename(src_file, dst_file)

    # Cleanup extracted directory
    import shutil
    shutil.rmtree(extracted_dir)
    print("Dataset download and organization complete.")

if __name__ == "__main__":
    download_fire_datasets()
