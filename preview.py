import os
import random
import shutil

import rawpy
from PIL import Image

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

def get_preview_images(files_for_date, target_date, max_images=9):
    """files_for_date: caminhos já filtrados pra essa data (vindos do índice do disco)."""
    jpg_ext = (".jpg", ".jpeg", ".thm")
    raw_ext = (".dng", ".arw", ".gpr")
    preview_dir = os.path.join("static", "previews", target_date.strftime("%Y%m%d"))
    os.makedirs(preview_dir, exist_ok=True)

    jpgs = []
    raws = []

    for path in files_for_date:
        if path.lower().endswith(jpg_ext):
            jpgs.append(path)
            if len(jpgs) >= max_images:
                break
        elif path.lower().endswith(raw_ext):
            raws.append(path)

    selected_images = jpgs[:max_images]

    # Se não tiver JPGs suficientes, tenta converter RAWs
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

    # Copia para a pasta final
    final_paths = []
    for path in selected_images:
        filename = os.path.basename(path)
        target = os.path.join(preview_dir, filename)
        if not os.path.exists(target):
            try:
                shutil.copy2(path, target)
            except:
                continue
        final_paths.append(f"/{target.replace(os.sep, '/')}")

    return final_paths
