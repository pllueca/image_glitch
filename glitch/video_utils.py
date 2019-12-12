""" reading and writing video tools """

from typing import Tuple, Optional
import subprocess
import numpy as np
import ffmpeg

NumpyArray = np.ndarray  # for typing


def start_ffmpeg_writer(out_filename: str, width: int, height: int) -> subprocess.Popen:
    """ Starts video writer process """
    args = (
        ffmpeg.input(
            "pipe:", format="rawvideo", pix_fmt="rgb24", s="{}x{}".format(width, height)
        )
        .output(out_filename, pix_fmt="yuv420p")
        .overwrite_output()
        .compile()
    )
    return subprocess.Popen(args, stdin=subprocess.PIPE)


def start_ffmpeg_reader(in_filename: str) -> subprocess.Popen:
    """ Starts video reader process """
    args = (
        ffmpeg.input(in_filename)
        .output("pipe:", format="rawvideo", pix_fmt="rgb24")
        .compile()
    )
    return subprocess.Popen(args, stdout=subprocess.PIPE)


def read_frame(
    reader_process: subprocess.Popen, width: int, height: int
) -> Optional[NumpyArray]:
    """ Reads a frame from a reader_process. The frame is asumed to be 3 channels, uint8.
  Return None if all frames have been read """
    frame_size = width * height * 3
    in_bytes = reader_process.stdout.read(frame_size)
    if len(in_bytes) == 0:
        frame = None  # end of stream
    else:
        assert len(in_bytes) == frame_size
        frame = np.frombuffer(in_bytes, np.uint8).reshape([height, width, 3])
    return frame


def get_video_size(filename: str) -> Tuple[int, int]:
    probe = ffmpeg.probe(filename)
    video_info = next(s for s in probe["streams"] if s["codec_type"] == "video")
    width = int(video_info["width"])
    height = int(video_info["height"])
    return width, height
