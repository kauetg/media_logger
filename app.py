import json
import os
import platform
import subprocess
from datetime import datetime

import exifread
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from werkzeug.utils import secure_filename

from file_ops import get_external_disks
from preview import get_preview_images
from utils import detect_camera, find_dates, copy_files, analyze_folder_content, load_camera_db
from scraps import get_camera_image_duckduckgo

app = Flask(__name__)

camera_db = load_camera_db()


@app.route('/', methods=['GET', 'POST'])
def home():
    disks = []

    for disk in get_external_disks():
        camera_id = detect_camera(disk)
        if camera_id and camera_id in camera_db:
            camera = camera_db[camera_id]
            disks.append({
                "name": camera["name"],
                "image": camera["image"],
                "disk": disk
            })
        else:
            disks.append({
                "name": "Unknown Device",
                "image": "unknown.jpg",
                "disk": disk
            })


    if request.method == 'POST':
        selected_disk = request.form.get('disk')
        return redirect(url_for('select', disk=selected_disk))

    return render_template('index.html', disks=disks)

@app.route('/select', methods=['GET', 'POST'])
def select():
    disk = request.args.get('disk')

    if not disk or not os.path.exists(disk):
        return "Disk not found", 404

    # Identifica a câmera conectada
    camera_id = detect_camera(disk)
    camera = camera_db.get(camera_id, {
        "name": "Unknown Device",
        "image": "unknown.png"
    })

    # Diretório de destino onde procuramos tags existentes
    destination_base = os.path.expanduser("~/Desktop/Copy to SSD")

    # Coleta todas as datas únicas com conteúdo válido
    detected_dates = find_dates(disk)
    date_cards = []

    for date in sorted(detected_dates):
        raw_date = date.strftime("%Y-%m-%d")
        folder_prefix = date.strftime("%Y%m%d")
        tag = ""

        # Verifica se já existe uma pasta com esse prefixo no destino
        if os.path.exists(destination_base):
            for name in os.listdir(destination_base):
                if name.startswith(folder_prefix):
                    parts = name.split(" ", 1)
                    if len(parts) > 1:
                        tag = parts[1]
                    break  # Achou uma, não precisa procurar mais

        date_info = {
            "raw": raw_date,
            "folder": folder_prefix,
            "display": date.strftime('%d-%b'),
            "preview": get_preview_images(disk, date, max_images=9),
            "stats": analyze_folder_content(disk, raw_date),
            "tag": tag
        }

        date_cards.append(date_info)

    return render_template(
        "select.html",
        disk=disk,
        camera=camera,
        dates=date_cards
    )

@app.route("/cameras")
def camera_list():

    return render_template("cameras.html", camera_db= load_camera_db())

@app.route('/status', methods=["POST"])
def status():
    selected_dates = request.form.getlist("selected_dates")
    disk = request.form.get("disk")
    camera_id = detect_camera(disk)

    camera = camera_db.get(camera_id, {
        "name": "Unknown Device",
        "image": "unknown.png"
    })

    if not selected_dates:
        return "Please select at least one date!", 400

    folders_info = []

    for date_str in selected_dates:
        tag = request.form.get(f"tag_{date_str}")
        if not tag:
            continue

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        folder_name = f"{date_obj.strftime('%Y%m%d')} {tag.title()}"

        folders_info.append({
            "date": date_obj.strftime("%Y-%m-%d"),
            "folder": folder_name,
            "tag": tag,
            "camera": camera
        })

    if not folders_info:
        return "No valid folders to copy!", 400

    # Só renderiza a página e mostra botão para iniciar cópia
    return render_template("status.html", folders=folders_info, disk=disk)


@app.route('/copy', methods=['POST'])
def copy():
    data = request.get_json()
    folders = data.get("folders", [])
    disk = data.get("disk")

    if not folders:
        return jsonify({"error": "No folders provided"}), 400

    # Usa a primeira data, pois o frontend envia um por vez
    date_str = folders[0].get("date")
    stats = analyze_folder_content(disk, date_str)

    destination = os.path.expanduser("~/Desktop/Copy to SSD")
    result = copy_files(disk, folders, destination)

    # Junta os dados do copy com as stats
    result.update({
        "photos": stats["photos"],
        "videos": stats["videos"]
    })

    return jsonify(result)

@app.route("/open_folder")
def open_folder():
    path = request.args.get("path")
    if not os.path.exists(path):
        return "Path not found", 404

    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.Popen(["open", path])
        else:  # Linux
            subprocess.Popen(["xdg-open", path])
        return Response(status=204)
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/add_camera', methods=['POST'])
def add_camera():
    camera_id = request.form['camera_id'].strip()
    name = request.form['name'].strip()
    image_file = request.files.get('image_file')

    # Cria nome padrão de arquivo com base no ID
    filename = secure_filename(camera_id.lower().replace(" ", "_") + ".jpg")
    image_path = os.path.join('static', 'img', 'cameras', filename)

    if image_file and image_file.filename:
        image_file.save(image_path)
    else:
        # Busca imagem automática via scraping
        image_url = get_camera_image_duckduckgo(name)
        if image_url:
            try:
                img_data = requests.get(image_url, timeout=5).content
                with open(image_path, 'wb') as f:
                    f.write(img_data)
            except Exception as e:
                print(f"Failed to fetch image: {e}")
                filename = "unknown.png"
        else:
            filename = "unknown.png"

    # Atualiza o JSON
    with open("cameras.json", 'r+') as f:
        db = json.load(f)
        db[camera_id] = {
            'name': name,
            'image': filename
        }
        f.seek(0)
        json.dump(db, f, indent=2)
        f.truncate()

    return redirect(url_for('camera_list'))

@app.route('/edit_camera/<camera_id>', methods=['POST'])
def edit_camera(camera_id):
    camera_db = load_camera_db()
    if camera_id not in camera_db:
        return "Camera not found", 404

    name = request.form.get('name')
    image_file = request.files.get('image_file')
    image_filename = camera_db[camera_id]['image']  # existing by default
    print(image_file)
    # Se o usuário submeter uma nova imagem
    if image_file and image_file.filename:
        image_filename = secure_filename(image_file.filename)
        image_file.save(os.path.join('static/img/cameras', image_filename))

    camera_db[camera_id] = {
        "name": name,
        "image": image_filename
    }

    with open("cameras.json", "w") as f:
        json.dump(camera_db, f, indent=2)

    return redirect(url_for('camera_list'))

@app.route('/delete_camera/<camera_id>', methods=['POST'])
def delete_camera(camera_id):
    with open('cameras.json', 'r+') as f:
        db = json.load(f)

        if camera_id in db:
            # opcional: remover imagem se não for "unknown.png"
            image_filename = db[camera_id].get("image")
            if image_filename and image_filename != "unknown.png":
                image_path = os.path.join('static', 'img', 'cameras', image_filename)
                if os.path.exists(image_path):
                    os.remove(image_path)

            del db[camera_id]
            f.seek(0)
            json.dump(db, f, indent=2)
            f.truncate()

    return redirect(url_for('camera_list'))


@app.route('/detect_exif', methods=['POST'])
def detect_exif():
    file = request.files['image']
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    temp_path = os.path.join('static/temp', file.filename)
    os.makedirs('static/temp', exist_ok=True)
    file.save(temp_path)

    tags = exifread.process_file(open(temp_path, 'rb'), stop_tag="Model")
    make = str(tags.get("Image Make", "")).strip()
    model = str(tags.get("Image Model", "")).strip()

    os.remove(temp_path)

    if make and model:
        return jsonify({"device_id": f"{make} - {model}"})
    else:
        return jsonify({"device_id": None})

@app.route('/preview_camera_image', methods=['POST'])
def preview_camera_image():
    data = request.get_json()
    camera_name = data.get("name")
    url = get_camera_image_duckduckgo(camera_name)
    print("url eh: " + url)
    return jsonify({"url": url})


if __name__ == '__main__':
    app.run(debug=True)
