import os
import random
import shutil

import rawpy
from PIL import Image
from datetime import date
from utils import mod_date  # se você já tem uma função que retorna .date()

def convert_raw_to_jpg(raw_path, output_path):
    try:
        with rawpy.imread(raw_path) as raw:
            rgb = raw.postprocess()
        img = Image.fromarray(rgb)
        img = img.resize((150, 150))
        img.save(output_path, "JPEG")
        return output_path
    except Exception as e:
        print(f"[Erro] Falha ao converter RAW: {raw_path} — {e}")
        return None

def get_preview_images(disk, target_date, max_images=9):
    jpg_ext = (".jpg", ".jpeg", ".thm")
    raw_ext = (".dng", ".arw", ".gpr")
    preview_dir = os.path.join("static", "previews", target_date.strftime("%Y%m%d"))
    os.makedirs(preview_dir, exist_ok=True)

    jpgs = []
    raws = []

    for root, _, files in os.walk(disk):
        for file in files:
            path = os.path.join(root, file)
            if mod_date(path) != target_date:
                continue

            if file.lower().endswith(jpg_ext):
                jpgs.append(path)
            elif file.lower().endswith(raw_ext):
                raws.append(path)

    selected_images = []

    # 1. Usa JPGs diretos
    if jpgs:
        selected_images.extend(random.sample(jpgs, min(len(jpgs), max_images)))

    # 2. Se faltar, tenta converter RAWs
    if len(selected_images) < max_images:
        needed = max_images - len(selected_images)
        raws_to_convert = random.sample(raws, min(len(raws), needed))
        for raw_path in raws_to_convert:
            filename = os.path.splitext(os.path.basename(raw_path))[0]
            output_path = os.path.join(preview_dir, f"{filename}.jpg")
            if not os.path.exists(output_path):
                result = convert_raw_to_jpg(raw_path, output_path)
                if result:
                    selected_images.append(result)
            else:
                selected_images.append(output_path)

    # 3. Copia JPGs selecionados para preview folder
    final_paths = []
    for path in selected_images:
        filename = os.path.basename(path)
        target = os.path.join(preview_dir, filename)
        if not os.path.exists(target):
            try:
                shutil.copy2(path, target)
            except:
                continue
        print("preview")
        final_paths.append(f"/{target.replace(os.sep, '/')}")

    return final_paths
