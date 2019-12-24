import os
import os.path as osp
import uuid
import glob
import shutil
import hashlib
import sass

from flask import Flask, flash, request, redirect, url_for, render_template, send_file, jsonify
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeSerializer
from sassutils.wsgi import SassMiddleware
from random import sample

import requests

from glitch.apps import glitch_image, glitch_video

signer = URLSafeSerializer("super-secret")

UPLOAD_FOLDER = "uploads"
STATIC_FOLDER = "static"
ASSETS_FOLDER = "assets"

ALLOWED_EXTENSIONS = {"image": ["png", "jpg", "jpeg"], "video": ["mov", "mp4", "ts"]}

COMMON_OPTIONS = {
    "noise_intensity":   {
        "label": "Noise Intensity",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5,
        "type": float
    },
    "noise_amount": {
        "label": "Noise Amount",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5,
        "type": float
    },
    "channels_movement": {
        "label": "Channels Movement",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5,
        "type": float
    },
    "block_size": {
        "label": "Block Size",
        "min": 0, "max": 1, "step": 0.01, "default": 0.5,
        "type": float
    },
    "block_count": {
        "label": "Block Count",
        "min": 0, "max": 100, "step": 1, "default": 15,
        "type": int
    }
}

IMAGE_OPTIONS = {
    **COMMON_OPTIONS
}

VIDEO_OPTIONS = {
    "min_effect_length": {
        "label": "Minimum effect duration (in frames)",
        "min": 1, "max": 10, "step": 1, "default": 1,
        "type": int
    },
    "max_effect_length": {
        "label": "Maximum effect duration (in frames)",
        "min": 5, "max": 30, "step": 1, "default": 15,
        "type": int
    },
    "scanlines_intensity": {
        "label": "Scanlines intensity",
        "min": 0, "max": 1, "step": 0.01, "default": 0,
        "type": float
    },
    "scanlines_size": {
        "label": "Scanlines size",
        "min": 0, "max": 20, "step": 1, "default": 8,
        "type": int
    },
    "scanlines_spacing": {
        "label": "Scanlines spacing",
        "min": 0, "max": 5, "step": 0.1, "default": 2,
        "type": float
    },
    **COMMON_OPTIONS
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

# Compile sass
os.makedirs(f"{STATIC_FOLDER}/css", exist_ok=True)

app.wsgi_app = SassMiddleware(app.wsgi_app, {
    'glitch_app': ('assets/scss', 'static/css', '/static/css')
})


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
    return { key: opt[key]['type'](request.args.get(key)) for key in opt.keys() }


@app.route("/glitch/<string:file_type>", methods=["GET", "POST"])
def glitch(file_type):
    options = IMAGE_OPTIONS if file_type == 'image' else VIDEO_OPTIONS
    params  = { key: options[key]['type'](options[key]['default']) for key in options.keys() }

    if request.method == "POST":
        reuse_last_file = False

        file = request.files.get("file", "")
        if file == "" or file.filename == "":
            if request.form['filename']:
                reuse_last_file = True
            else:
                flash("No selected file")
                return redirect(request.url)
        
        params = { key: options[key]['type'](request.form[key]) for key in options.keys() }
        print(f"Submitted params: {params}")
        
        if not reuse_last_file:
            if allowed_file(file.filename, file_type):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], file_type, filename)
                file.save(filepath)
            else:
                flash("Invalid filetype")
                return redirect(request.url)
        else:
            fname = request.form['filename']
            file_hash = os.path.basename(fname).split('_')[0]
            filepath = osp.join(STATIC_FOLDER, file_type, file_hash, f"original.{file_extension(fname)}")

        extension = file_extension(filepath)
        file_hash = hash_file(filepath)
        
        previously_glitched = osp.exists(osp.join(STATIC_FOLDER, file_type, file_hash))
        
        if not previously_glitched:
            os.makedirs(osp.join(STATIC_FOLDER, file_type, file_hash))
            new_filepath = osp.join(
                STATIC_FOLDER, file_type, file_hash, f"original.{extension}"
            )
            shutil.copy(filepath, new_filepath)
            filepath = new_filepath
            other_glitches = []
        else:
            # glitch files are postfixed with -glitch-XX.ext
            other_glitches = glob.glob(
                osp.join(STATIC_FOLDER, file_type, file_hash, "*_glitch_*")
            )
        
        current_glitch_num = len(other_glitches)
        
        glitched_fname = f"{file_hash}_glitch_{current_glitch_num}.{extension}"
        glitched_filepath = osp.join(STATIC_FOLDER, file_type, file_hash, glitched_fname)
        
        glitched_fname = osp.join(file_type, file_hash, glitched_fname)
        
        if file_type == "image":
            glitch_image(filepath, glitched_filepath, **params)
        elif file_type == "video":
            glitch_video(filepath, glitched_filepath, **params)
    else:
        glitched_fname = ""
        other_glitches = []

    return render_template(
        "glitch.html",
        allowed_extensions=ALLOWED_EXTENSIONS,
        options=options,
        parameters=params,
        glitched_fname=glitched_fname,
        other_glitches=other_glitches,
        file_type=file_type,
    )

NUM_DISPLAYED_GLITCHES = 6

@app.route("/", methods=["GET"])
def home():
    images = glob.glob(
        osp.join(STATIC_FOLDER, 'image', '*', "*_glitch_*")
    )
    if images:
        images = sample(images, min(NUM_DISPLAYED_GLITCHES, len(images)))

    videos = glob.glob(
        osp.join(STATIC_FOLDER, 'video', '*', "*_glitch_*")
    )
    if videos:
        videos = sample(videos, min(NUM_DISPLAYED_GLITCHES, len(videos)))

    return render_template("home.html",
        allowed_extensions=ALLOWED_EXTENSIONS,
        images=images,
        videos=videos,
    )


@app.route("/health_check", methods=["GET"])
def health_check():
    return jsonify({"state": "running"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
