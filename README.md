# Glitch

Python app to apply [glitch art](https://en.wikipedia.org/wiki/Glitch_art) style to images and videos.

```
docker build -t glitch .
docker run -p 5000:5000 glitch
```

and go to `localhost:5000`.

Transformations are implemented using `numpy` in `glitch/image_glitch.py`. There are samples in jupyter notebooks in `examples`
