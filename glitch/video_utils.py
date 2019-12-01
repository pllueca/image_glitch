import subprocess
import numpy as np
import ffmpeg


def start_ffmpeg_writer(out_filename, width, height):
  args = (
      ffmpeg.input('pipe:', format='rawvideo', pix_fmt='rgb24',
                   s='{}x{}'.format(width,
                                    height)).output(out_filename,
                                                    pix_fmt='yuv420p').overwrite_output().compile())
  return subprocess.Popen(args, stdin=subprocess.PIPE)


def start_ffmpeg_reader(in_filename):
  args = (ffmpeg.input(in_filename).output('pipe:', format='rawvideo', pix_fmt='rgb24').compile())
  return subprocess.Popen(args, stdout=subprocess.PIPE)


def read_frame(reader_process, width, height):
  frame_size = width * height * 3
  in_bytes = reader_process.stdout.read(frame_size)
  if len(in_bytes) == 0:
    frame = None  # end of stream
  else:
    assert len(in_bytes) == frame_size
    frame = (np.frombuffer(in_bytes, np.uint8).reshape([height, width, 3]))
  return frame


def get_video_size(filename):
  probe = ffmpeg.probe(filename)
  video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
  width = int(video_info['width'])
  height = int(video_info['height'])
  return width, height
