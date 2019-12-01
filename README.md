# Glitch
Python app to apply [glitch art](https://en.wikipedia.org/wiki/Glitch_art) style to images and videos.
to run the app run:

```
pip install -r requirements
FLASK_APP=glitch_app.py flask run
```

and go to `localhost:5000`.

Transformations are implemented using `numpy` in `glitch/image_glitch.py`. There are samples in jupyter notebooks in `examples`
