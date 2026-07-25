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


# Cache: uma varredura por disco/pasta em vez de uma por data exibida.
# Evita repassar 150GB de cartão a cada preview/stat/cópia.
_disk_index_cache = {}


def scan_disk(disk):
    """Varre o disco/pasta de origem uma única vez, indexando arquivos de mídia por data."""
    index = {}

    for root, _, files in os.walk(disk):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in IMG_EXTS:
                continue

            path = os.path.join(root, file)
            date_obj = mod_date(path)
            if date_obj is None:
                continue

            bucket = index.setdefault(date_obj, {
                "files": [],
                "photo_count": 0,
                "video_count": 0,
                "size_bytes": 0
            })

            try:
                size = os.path.getsize(path)
            except OSError:
                continue

            bucket["files"].append(path)
            bucket["size_bytes"] += size
            if ext in PHOTO_EXTS:
                bucket["photo_count"] += 1
            else:
                bucket["video_count"] += 1

    return index


def get_disk_index(disk, force=False):
    """Retorna o índice de mídia do disco, reaproveitando a varredura entre select/copy."""
    if force or disk not in _disk_index_cache:
        _disk_index_cache[disk] = scan_disk(disk)
    return _disk_index_cache[disk]


def clear_disk_index_cache():
    """Limpa o cache — chamado quando o usuário volta pra tela inicial (troca de cartão)."""
    _disk_index_cache.clear()


def find_dates(index):
    return sorted(index.keys())


def format_stats(bucket):
    size_mb = round(bucket["size_bytes"] / (1024 * 1024), 2)
    size_str = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb / 1024, 2)} GB"
    return {
        "photos": bucket["photo_count"],
        "videos": bucket["video_count"],
        "size": size_str
    }


def _friendly_copy_error(e):
    """Traduz erros comuns do Windows (arquivo em uso, disco cheio) pra algo legível na UI."""
    if getattr(e, "winerror", None) == 32:
        return "File is in use — close it (or the destination folder) in another program and try again."
    if getattr(e, "errno", None) == 28:  # ENOSPC
        return "Destination disk is full."
    if isinstance(e, PermissionError):
        return "Permission denied — check the destination isn't read-only or open elsewhere."
    return str(e)


def copy_files(index, folders, destination):
    dict_panos = {3: "Vertical", 9: "3x3", 21: "180", 33: "360"}

    copied_files = 0
    total_size_bytes = 0
    base_path = destination
    failures = []

    for folder in folders:
        date_str = folder['date']
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        tag = folder["tag"]
        camera_name = folder.get("camera", {}).get("name", "Unknown Camera")

        main_folder = f"{date_obj.strftime('%Y%m%d')} {tag.title()}"
        base_path = os.path.join(destination, main_folder, camera_name)
        photo_path = os.path.join(base_path, "photo")  # <- removido 'others'
        video_path = os.path.join(base_path, "video")

        try:
            os.makedirs(photo_path, exist_ok=True)
            os.makedirs(video_path, exist_ok=True)
        except OSError as e:
            failures.append({"file": main_folder, "reason": _friendly_copy_error(e)})
            continue

        bucket = index.get(date_obj, {"files": []})

        for path in bucket["files"]:
            file = os.path.basename(path)
            root = os.path.dirname(path)
            ext = os.path.splitext(file)[1].lower()
            is_pano_folder = "panorama" in root.lower()
            is_samsung = 'samsung' in camera_name.lower()

            is_photo = ext in COPY_EXTS or (ext in ('.jpg', '.jpeg') and is_samsung)
            is_video = ext in VIDEO_EXTS

            try:
                if is_photo:
                    if is_pano_folder:
                        pano_folder = root
                        pano_files = [f for f in os.listdir(pano_folder) if os.path.isfile(os.path.join(pano_folder, f))]
                        pano_count = len(pano_files)
                        pano_type = dict_panos.get(pano_count, "others")

                        pano_base = os.path.join(base_path, "photo", "panoramas")
                        candidate_folder = os.path.join(pano_base, pano_type)
                        pano_index = 1
                        while os.path.exists(candidate_folder) and file in os.listdir(candidate_folder):
                            candidate_folder = os.path.join(pano_base, f"{pano_type}_{pano_index}")
                            pano_index += 1

                        os.makedirs(candidate_folder, exist_ok=True)
                        dest = os.path.join(candidate_folder, file)
                    else:
                        dest = os.path.join(photo_path, file)

                elif is_video:
                    dest = os.path.join(video_path, file)
                else:
                    continue

                copy2(path, dest)
            except OSError as e:
                failures.append({"file": file, "reason": _friendly_copy_error(e)})
                continue

            total_size_bytes += os.path.getsize(path)
            copied_files += 1

        # Remove previews
        date_preview = date_obj.strftime("%Y%m%d")
        preview_folder = os.path.join("static", "previews", date_preview)
        if os.path.exists(preview_folder):
            try:
                rmtree(preview_folder)
            except OSError:
                pass

    size_mb = round(total_size_bytes / (1024 * 1024), 2)
    size_str = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb / 1024, 2)} GB"

    return {
        "copied": copied_files,
        "size": size_str,
        "path": base_path,
        "failed": failures
    }


def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)


def get_default_destination():
    config = load_config()
    return config.get("last_destination") or os.path.expanduser("~/Desktop/Copy to SSD")


def set_default_destination(path):
    config = load_config()
    config["last_destination"] = path
    save_config(config)



def load_camera_db():
    with open('cameras.json') as f:
        return json.load(f)