import imageio
import numpy as np

from .image_glitch import move_random_blocks, move_channels_random, salt_and_pepper
from .video_utils import (
    get_video_size,
    start_ffmpeg_reader,
    start_ffmpeg_writer,
    read_frame,
)


def glitch_image(input_path, output_path):
    image = imageio.imread(input_path)

    image = move_random_blocks(image, max_blocksize=(150, 400), num_blocks=3, per_channel=True)

    image = move_random_blocks(image, max_blocksize=(200, 50), num_blocks=5, per_channel=True)

    image = move_channels_random(image, -10, 10)

    image = salt_and_pepper(image, 0.6, 0.02)

    imageio.imwrite(output_path, image)


def glitch_video(input_path, output_path):
    width, height = get_video_size(input_path)
    reader = start_ffmpeg_reader(input_path)
    writer = start_ffmpeg_writer(output_path, width, height)
    while True:
        frame = read_frame(reader, width, height)
        if frame is None:
            # no more frames
            break

        # process frame
        roll = np.random.randint(0, 6)
        # 0 -> move channels
        # 1 -> swap blocks
        # 2 -> both
        # 3+ -> nothing

        roll_noise = np.random.randint(0, 4)
        # if 0 or 1 noise

        frame = frame.copy()
        if roll in [0, 2]:
            frame = move_channels_random(frame, -15, 15)
        if roll in [1, 2]:
            blocksize_x = np.random.randint(
                min(width, height) * 0.1, max(width, height) * 0.5
            )
            blocksize_y = np.random.randint(
                min(width, height) * 0.1, max(width, height) * 0.5
            )
            frame = move_random_blocks(
                frame,
                max_blocksize=(blocksize_x, blocksize_y),
                num_blocks=3,
                per_channel=True,
            )

        if roll_noise in [0, 1]:
            frame = salt_and_pepper(frame, 0.5, 0.02)

        writer.stdin.write(frame.astype(np.uint8).tobytes())

    # cleanup
    reader.wait()
    writer.stdin.close()
    writer.wait()
