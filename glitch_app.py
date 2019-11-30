import os
import uuid
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeSerializer
from glitch import glitch_image

signer = URLSafeSerializer('super-secret')

UPLOAD_FOLDER = 'images'
STATIC_FOLDER = 'tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__, static_folder=STATIC_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['STATIC_FOLDER'] = STATIC_FOLDER



def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/glitch/<string:gid>', methods=['GET'])
def glitch(gid):
  filepath = signer.loads(gid)
  glitched_fname = f'{uuid.uuid4()}.png'
  glitched_filepath = os.path.join(STATIC_FOLDER, glitched_fname)
  glitch_image(filepath, glitched_filepath)
  return render_template("glitch.html", image_fname=glitched_fname)


@app.route('/', methods=['GET', 'POST'])
def home():
  if request.method == 'POST':
    # check if the post request has the file part
    if 'file' not in request.files:
      flash('No file part')
      return redirect(request.url)
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
      flash('No selected file')
      return redirect(request.url)

    if file and allowed_file(file.filename):
      filename = secure_filename(file.filename)
      filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
      file.save(filepath)
      gid = signer.dumps(filepath)
      return redirect(url_for('glitch', gid=gid))
  return render_template('home.html')


if __name__ == '__main__':
  app.run()
