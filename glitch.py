import subprocess

import imageio
import numpy as np
import ffmpeg


def move_channel(arr, channel, deltax, deltay):
  """ move the given channel in the direction (deltax, deltay) """
  w, h, c = arr.shape
  if channel >= c:
    raise ValueError(f'image only have {c} channels')

  if deltax < 0 and deltay < 0:
    arr[:w + deltax, :h + deltay, channel] = arr[-deltax:, -deltay:, channel]
  elif deltax > 0 and deltay > 0:
    arr[deltax:, deltay:, channel] = arr[:-deltax, :-deltay, channel]
  elif deltax > 0 and deltay < 0:
    arr[deltax:, :h + deltay, channel] = arr[:-deltax, -deltay:, channel]
  elif deltax < 0 and deltay > 0:
    arr[:w + deltax, deltay:, channel] = arr[-deltax:, :-deltay, channel]
  else:
    arr[..., channel] = arr[..., channel]
  return arr


def move_channels_random(arr, min_delta=-50, max_delta=50):
  """ move each channel a random amount between -val and val"""
  res = arr.copy()
  for channel in range(arr.shape[-1]):
    deltax, deltay = np.random.randint(min_delta, max_delta, (2,))
    res = move_channel(res, channel, deltax, deltay)
  return res


def move_blocks(arr, blocksize=(5, 5), num_blocks=5, per_channel=False):
  """ swap `num_blocks` of size `blocksize` in arr """
  res = arr.copy()
  w, h, n_channels = arr.shape
  block_size_x, block_size_y = blocksize
  for _ in range(num_blocks):
    if per_channel:
      channel = np.random.randint(0, n_channels)
    else:
      channel = ...
    block_orig_x = np.random.randint(0, w - block_size_x)
    block_orig_y = np.random.randint(0, h - block_size_y)

    block_dest_x = np.random.randint(0, w - block_size_x)
    block_dest_y = np.random.randint(0, h - block_size_y)

    res[block_dest_x:block_dest_x + block_size_x, block_dest_y:block_dest_y +
        block_size_y, channel] = arr[block_orig_x:block_orig_x +
                                     block_size_x, block_orig_y:block_orig_y +
                                     block_size_y, channel]
    res[block_orig_x:block_orig_x + block_size_x, block_orig_y:block_orig_y +
        block_size_y, channel] = arr[block_dest_x:block_dest_x +
                                     block_size_x, block_dest_y:block_dest_y +
                                     block_size_y, channel]
  return res


def flip_block(arr, blocksize, per_channel):
  res = arr.copy()
  w, h, n_channels = arr.shape
  block_size_x, block_size_y = blocksize

  block_x = np.random.randint(0, w - block_size_x)
  block_y = np.random.randint(0, h - block_size_y)

  if per_channel:
    # each channel have 50% prob of flipping
    for c in range(n_channels):
      if np.random.randint(0, 1):
        flipped_block = arr[block_x:block_x + block_size_x, block_y:block_y + block_size_y, c]
        flipped_block = flipped_block[::-1, ::-1]
        res[block_x:block_x + block_size_x, block_y:block_y + block_size_y, c] = flipped_block
  else:
    flipped_block = arr[block_x:block_x + block_size_x, block_y:block_y + block_size_y, ...]
    flipped_block = flipped_block[::-1, ::-1]
    res[block_x:block_x + block_size_x, block_y:block_y + block_size_y] = flipped_block
  return res


def salt_and_pepper(arr, intensity=.6, noise_frac=.02):
  """ replaces random pixels with 255,255,255 or 0,0,0
    intensity from 0 to 10"""
  if not 0 <= intensity <= 1.0:
    raise ValueError('intensity must be between 0 and 10!')
  w, h, _ = arr.shape

  # 2 of eac noise_frac pix is noisy
  prob_noise = int(1 / noise_frac)
  noise_mask = np.random.randint(0, prob_noise, (w, h))
  noise_rgb = arr.copy()
  noise_rgb[np.where(noise_mask == 0)] = 0, 0, 0
  noise_rgb[np.where(noise_mask == 1)] = 255, 255, 255

  return (arr.copy() * intensity + noise_rgb * (1 - intensity)).astype(np.uint8)


def glitch_image(image_path, dest_path):
  im = imageio.imread(image_path)
  width, height, channels = im.shape
  if channels == 4:
    alpha_band = im[..., 3]
    im = im[..., :3]

  for _ in range(2):
    blocksize_x = np.random.randint(min(width, height) * .1, max(width, height) * .3)
    blocksize_y = 3 * blocksize_x
    im = move_blocks(im, blocksize=(blocksize_x, blocksize_y), num_blocks=2, per_channel=True)

  for _ in range(2):
    blocksize_x = np.random.randint(min(width, height) * .3, max(width, height) * .5)
    blocksize_y = int(0.8 * blocksize_x)
    im = move_blocks(im, blocksize=(blocksize_x, blocksize_y), num_blocks=1, per_channel=True)

  im = move_channels_random(im, -5, 5)
  im = salt_and_pepper(im, 0.5, .02)

  # restore alpha
  if channels == 4:
    alpha_band = np.expand_dims(alpha_band, axis=-1)
    im = np.concatenate((im, alpha_band), axis=-1)
  imageio.imwrite(dest_path, im)


def start_ffmpeg_writer(out_filename, width, height):
  args = (
      ffmpeg.input('pipe:', format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(width, height))
      .output(out_filename, pix_fmt='yuv420p')
      .overwrite_output()
      .compile()
  )
  return subprocess.Popen(args, stdin=subprocess.PIPE)

def make_glitch_video_slow_channel_move(src_image, num_frames, output_fpath):
  im = imageio.imread(src_image)
  w, h, _ = im.shape
  p = start_ffmpeg_writer(output_fpath, h, w)
  for i in range(num_frames):
    for c in range(3):
      dx = np.random.randint(-5,5)
      dy = np.random.randint(-5,5)
      im = move_channel(im, c, dx, dy)
    p.stdin.write(im.astype(np.uint8).tobytes())
  p.stdin.close()
  p.wait() 
