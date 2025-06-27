# exif handling functions
import json
import os
from shutil import copy2, rmtree
import re

import exifread
from datetime import date, datetime


# Formatos suportados
COPY_EXTS = ('.dng', '.arw', '.gpr', '.insv')
PHOTO_EXTS = ('.jpg', '.jpeg') + COPY_EXTS
VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.insp')
IMG_EXTS = PHOTO_EXTS + VIDEO_EXTS


def detect_camera(disk_path):
    for root, dirs, files in os.walk(disk_path):
        for file in files:
            if file.lower().endswith(IMG_EXTS):
                try:
                    file_path = os.path.join(root, file)
                    with open(file_path, 'rb') as f:
                        tags = exifread.process_file(f, stop_tag='Image Model')

                    make = tags.get('Image Make')
                    model = tags.get('Image Model')

                    if make and model:
                        return f"{make.values} - {model.values}"
                except Exception:
                    continue

    return None


def mod_date(file_path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path)).date()
    except Exception as e:
        print(f"[mod_date ERRO] {file_path}: {e}")
        return None


def find_dates(disk):
    all_dates = set()

    for root, dirs, files in os.walk(disk):
        for file in files:
            if file.lower().endswith(IMG_EXTS):
                file_path = os.path.join(root, file)
                try:
                    all_dates.add(mod_date(file_path))
                except Exception:
                    continue

    return sorted(all_dates)


def analyze_folder_content(disk, date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    photo_count = 0
    video_count = 0
    total_size_bytes = 0

    for root, _, files in os.walk(disk):
        for file in files:
            path = os.path.join(root, file)
            if mod_date(path) == date_obj:
                ext = os.path.splitext(file)[1].lower()
                if ext in PHOTO_EXTS or ext in VIDEO_EXTS:
                    total_size_bytes += os.path.getsize(path)
                    if ext in PHOTO_EXTS:
                        photo_count += 1
                    else:
                        video_count += 1
    size_mb = round(total_size_bytes / (1024 * 1024), 2)
    size_str = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb / 1024, 2)} GB"
    return {
        "photos": photo_count,
        "videos": video_count,
        "size": size_str
    }


def copy_files(disk, folders, destination):
    dict_panos = {3: "Vertical", 9: "3x3", 21: "180", 33: "360"}

    copied_files = 0
    total_size_bytes = 0

    for folder in folders:
        date_str = folder['date']
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        tag = folder["tag"]
        camera_name = folder.get("camera", {}).get("name", "Unknown Camera")

        main_folder = f"{date_obj.strftime('%Y%m%d')} {tag.title()}"
        base_path = os.path.join(destination, main_folder, camera_name)
        photo_path = os.path.join(base_path, "photo", "others")
        video_path = os.path.join(base_path, "video")

        os.makedirs(photo_path, exist_ok=True)
        os.makedirs(video_path, exist_ok=True)

        for root, _, files in os.walk(disk):
            for file in files:
                path = os.path.join(root, file)

                if mod_date(path) != date_obj:
                    continue

                ext = os.path.splitext(file)[1].lower()

                # Detect panoramas
                is_pano = "pano" in file.lower()
                is_photo = ext in COPY_EXTS
                is_video = ext in VIDEO_EXTS

                if is_photo:
                    # Dentro de pasta chamada PANORAMA?
                    if "panorama" in root.lower():
                        pano_folder = os.path.dirname(path)
                        pano_files = [f for f in os.listdir(pano_folder) if os.path.isfile(os.path.join(pano_folder, f))]
                        pano_count = len(pano_files)

                        pano_type = dict_panos.get(pano_count, "Unknown")
                        pano_base = os.path.join(base_path, "photo", "panoramas")

                        # Procurar pasta disponível com incremento
                        candidate_folder = os.path.join(pano_base, pano_type)
                        index = 1
                        while os.path.exists(os.path.join(candidate_folder)) and \
                                file in os.listdir(os.path.join(candidate_folder)):
                            candidate_folder = os.path.join(pano_base, f"{pano_type}_{index}")
                            index += 1

                        os.makedirs(candidate_folder, exist_ok=True)
                        dest = os.path.join(candidate_folder, file)

                    else:
                        dest = os.path.join(photo_path, file)

                elif is_video:
                    dest = os.path.join(video_path, file)
                else:
                    continue

                copy2(path, dest)
                total_size_bytes += os.path.getsize(path)
                copied_files += 1

        # Remove previews
        date_preview = date_obj.strftime("%Y%m%d")
        preview_folder = os.path.join("static", "previews", date_preview)
        if os.path.exists(preview_folder):
            rmtree(preview_folder)

    size_mb = round(total_size_bytes / (1024 * 1024), 2)
    size_str = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb / 1024, 2)} GB"

    return {
        "copied": copied_files,
        "size": size_str,
        "path": base_path
    }


def load_camera_db():
    with open('cameras.json') as f:
        return json.load(f)