# media_logger

 Media Logger

**Media Logger** is a Flask-based tool for organizing and managing media files (photos and videos) from multiple cameras. It helps identify cameras using EXIF data, suggests thumbnail images, and sorts files into structured folders based on date, camera type, media type, and panorama format.

---

## 🚀 Features

- Upload a sample photo to auto-detect EXIF camera info
- Automatically fill in camera name and fetch suggested images
- Create and edit camera profiles via a web interface
- Organize files into structured folders:
  - By date (e.g., `20250506 Praia de Ipanema`)
  - By camera name (e.g., `DJI Air 3`)
  - By media type (`photo/`, `video/`, `photo/panoramas/`)
- Detect and classify panoramas by type (Vertical, 3x3, 180°, 360°)
- Lightweight, responsive UI built with Bootstrap 5
- EXIF preview and organization logic based on file modification date

---

## 📁 Folder Structure Example

20250506 Praia de Ipanema/
├── DJI Air 3/
│ ├── photo/
│ │ ├── others/
│ │ └── panoramas/
│ │ ├── 3x3/
│ │ ├── 3x3_1/
│ │ └── 180/
│ └── video/

yaml
Copy
Edit

---

## 🛠 Requirements

- Python 3.8+
- pip

---

## 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/media-logger.git
cd media-logger

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python app.py
Then visit http://localhost:5000 in your browser.

## 🖥 Technologies Used
Python 3

Flask

Bootstrap 5

EXIFRead

rawpy + Pillow (for RAW preview)

JavaScript (vanilla)

📸 Panorama Types Supported
Count	Type
3	Vertical
9	3x3
21	180°
33	360°

🤖 Auto Camera Detection
When uploading a test image, the app will:

Extract EXIF make & model

Pre-fill the camera ID field

Suggest a thumbnail image using DuckDuckGo

📜 License
This project is licensed under the MIT License.

👤 Author
Developed by Kaue Senger
GitHub @kauetg











