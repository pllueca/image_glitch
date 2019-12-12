import os
import os.path as osp
import uuid
import glob
import shutil
import hashlib

from flask import Flask, flash, request, redirect, url_for, render_template, jsonify
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeSerializer
import requests

from glitch.apps import glitch_image, glitch_video

signer = URLSafeSerializer("super-secret")

UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"
ALLOWED_EXTENSIONS = {"image": ["png", "jpg", "jpeg"], "video": ["mov", "mp4", "ts"]}

IMAGE_OPTIONS = {
    "intensity_noise":   {
        "label": "Noise Intensity",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5
    },
    "intensity_fractal": {
        "label": "Fractal Intensity",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5
    },
    "block_movement":    {
        "label": "Block Movement",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5
    },
    "block_size":        {
        "label": "Block Size",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5
    },
    "channels_movement": {
        "label": "Channels Movement",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5
    }
}

VIDEO_OPTIONS = {
    "min_effect_length": {
        "label": "Minimum effect duration (in frames)",
        "min": 1, "max": 10, "step": 1, "default": 1
    },
    "max_effect_length": {
        "label": "Maximum effect duration (in frames)",
        "min": 5, "max": 30, "step": 1, "default": 15
    },
    "block_size": {
        "label": "Block Size",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5
    },
    "block_effect": {
        "label": "Block Effect Amount",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5
    }
}

app = Flask(__name__, static_folder=STATIC_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SECRET_KEY"] = "1234asdf"

# create dirs if needed
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)
for media_type in ALLOWED_EXTENSIONS:
    os.makedirs(os.path.join(UPLOAD_FOLDER, media_type), exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, media_type), exist_ok=True)


def allowed_file(filename, filetype):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS[filetype]
    )


def file_extension(filename):
    return filename.rsplit(".", 1)[1].lower()


def get_file_type(filename):
    ext = file_extension(filename)
    for ftype in ALLOWED_EXTENSIONS:
        if ext in ALLOWED_EXTENSIONS[ftype]:
            return ftype
    return "Unknown"


def hash_file(filename: str) -> str:
    with open(filename, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def get_options(file_type, request) -> object:
    opt = IMAGE_OPTIONS if file_type == 'image' else VIDEO_OPTIONS  
    return { key: request.args.get(key) for key in opt.keys() }

@app.route("/glitch/<string:gid>", methods=["GET"])
def glitch(gid):
    filepath = signer.loads(gid)
    file_type = get_file_type(filepath)
    extension = file_extension(filepath)
    file_hash = hash_file(filepath)
    
    options = get_options(file_type, request)
    
    print(f"Submitted options: {options}")

    if not osp.exists(osp.join(STATIC_FOLDER, file_type, file_hash)):
        os.makedirs(osp.join(STATIC_FOLDER, file_type, file_hash))
        new_filepath = osp.join(
            STATIC_FOLDER, file_type, file_hash, f"original.{extension}"
        )
        shutil.copy(filepath, new_filepath)
        filepath = new_filepath
        current_glitch_num = 0
        other_glitches = []
    else:
        # glitch files are postfixed with -glitch-XX.ext
        other_glitches = glob.glob(
            osp.join(STATIC_FOLDER, file_type, file_hash, "*_glitch_*")
        )
        current_glitch_num = len(other_glitches)

    glitched_fname = f"{file_hash}_glitch_{current_glitch_num}.{extension}"
    current_glitch_num += 1

    glitched_filepath = osp.join(STATIC_FOLDER, file_type, file_hash, glitched_fname)

    if file_type == "image":
        glitch_image(filepath, glitched_filepath, options)
    elif file_type == "video":
        glitch_video(filepath, glitched_filepath, options)

    return render_template(
        "glitch.html",
        glitched_fname=osp.join(file_type, file_hash, glitched_fname),
        file_type=file_type,
    )


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        file = request.files.get("file", "")
        if file == "" or file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        file_type = request.form["file_type"]
        
        options_dict = IMAGE_OPTIONS if file_type == 'image' else VIDEO_OPTIONS
        options = { key: request.form[key] for key in options_dict.keys() }

        if file_type not in ALLOWED_EXTENSIONS.keys():
            flash("No file type selected")
            return redirect(request.url)

        if allowed_file(file.filename, file_type):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file_type, filename)
            file.save(filepath)
        else:
            flash("Invalid filetype")
            return redirect(request.url)

        gid = signer.dumps(filepath)
        return redirect(url_for("glitch", gid=gid, **options))

    else:  # Method GET
        return render_template("home.html",
                                    allowed_extensions=ALLOWED_EXTENSIONS,
                                    image_options=IMAGE_OPTIONS,
                                    video_options=VIDEO_OPTIONS)


@app.route("/health_check", methods=["GET"])
def health_check():
    return jsonify({"state": "running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
