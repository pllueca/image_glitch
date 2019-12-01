import os
import uuid

from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeSerializer
import requests

from glitch import glitch_image

signer = URLSafeSerializer('super-secret')

UPLOAD_FOLDER = 'images'
STATIC_FOLDER = 'tmp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__, static_folder=STATIC_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = '1234asdf'


def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def file_extension(filename):
  return filename.rsplit('.', 1)[1].lower()


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
    print(request.form, request.files)
    url = request.form.get('url', '')
    file = request.files.get('file', '')
    if (file == '' or file.filename == '') and url == '':
      print('No file or url')
      return redirect(request.url)
    if (file == '' or file.filename == '') and url != '':
      print('Only one of url or file must be provided')
      return redirect(request.url)

    if 'file' in request.files:
      file = request.files['file']

      if not file or file.filename == '':
        flash('No selected file')
        return redirect(request.url)

      if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    elif url != '':
      print('downloading', url)
      filename = f'{uuid.uuid4()}.{file_extension(url)}'
      filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
      file_request = requests.get(url)
      with app.open_instance_resource(filepath, 'wb') as f:
        f.write(file_request.content)

    gid = signer.dumps(filepath)
    return redirect(url_for('glitch', gid=gid))

  else:  # Method GET
    return render_template('home.html')


if __name__ == '__main__':
  app.run()
