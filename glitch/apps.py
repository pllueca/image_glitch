import imageio
import numpy as np

from .image_glitch import move_random_blocks, move_channels_random, salt_and_pepper
from .video_utils import (
    get_video_size,
    start_ffmpeg_reader,
    start_ffmpeg_writer,
    read_frame,
)


def glitch_image(input_path: str, output_path: str) -> None:
    """ swaps some random blocks, random moves channels and adds salt and pepper noise to the image
    """
    image = imageio.imread(input_path)

    image = move_random_blocks(
        image, max_blocksize=(150, 400), num_blocks=3, per_channel=True
    )

    image = move_random_blocks(
        image, max_blocksize=(200, 50), num_blocks=5, per_channel=True
    )

    image = move_channels_random(image, -10, 10)

    image = salt_and_pepper(image, 0.6, 0.02)

    imageio.imwrite(output_path, image)


def glitch_video(input_path: str, output_path: str) -> None:
    """ glitches a video. 
    a collection of glitches are applied to chunks of the video. Each glitch have a random duration
    betwee 1 and 15 consecutive frames. Avalaible glitches are:
    * move channels in random direction
    * move channels in constant direction
    * swap random blocks of the video, same blocks every time
    * swap random blocks of the video, random blocks every time
    * salt and pepper noise
    """
    width, height = get_video_size(input_path)
    reader = start_ffmpeg_reader(input_path)
    writer = start_ffmpeg_writer(output_path, width, height)
    # each glitch (effect) happens during some frames
    min_effect_length = 1
    max_effect_length = 15
    remaining_frames_effect = 0
    while True:
        if frame_idx % 100 == 0:
            print(f"frame {frame_idx}")

        frame = read_frame(reader, width, height)
        if frame is None:
            # no more frames
            break
        if not remaining_frames_effect:
            remaining_frames_effect = np.random.randint(
                min_effect_length, max_effect_length
            )
            current_effect_frame = 1
            # roll for next effect: noise and block swapping
            roll = np.random.randint(0, 7)
            if frame_idx < 5:
                roll = 4
            #         roll = 0

            # 0 -> move channels progresively
            if roll in [0, 5]:
                channel_directions = np.random.randint(-3, 3, (3, 2))
                remaining_frames_effect = 20

            # 1 -> "vibrate channels"
            if roll in [1]:
                remaining_frames_effect = 5
            # 2 -> swap blocks static
            if roll in [2]:
                num_blocks = np.random.randint(1, 4)
                block_sizes = np.random.randint(100, 600, (num_blocks, 2))
                block_channels = np.random.randint(0, 3, (num_blocks,))
                block_xs, block_ys = [], []
                for b in range(num_blocks):
                    block_xs.append(
                        np.random.randint(0, height - block_sizes[b, 0], (2,))
                    )
                    block_ys.append(
                        np.random.randint(0, width - block_sizes[b, 1], (2,))
                    )
                block_xs = np.asarray(block_xs)
                block_ys = np.asarray(block_ys)

            # 3 -> swap blocks random
            # 5 -> channels and blocks
            # 4+ -> nothing

            roll_noise = np.random.randint(0, 3)
            # if 0 or 1 noise
        else:
            remaining_frames_effect -= 1
            current_effect_frame += 1
        frame_orig = frame
        frame = frame.copy()

        if roll in [0, 5]:
            for c in range(3):
                dx, dy = channel_directions[c] * current_effect_frame
                frame = move_channel(frame, c, dx, dy)

        if roll in [1]:
            frame = move_channels_random(frame, -15, 15)

        if roll in [3, 5]:
            num_blocks = np.random.randint(1, 5)
            block_sizes = np.random.randint(50, 400, (num_blocks, 2))
            block_channels = np.random.randint(0, 3, (num_blocks,))
            block_xs, block_ys = [], []
            for b in range(num_blocks):
                block_xs.append(np.random.randint(0, height - block_sizes[b, 0], (2,)))
                block_ys.append(np.random.randint(0, width - block_sizes[b, 1], (2,)))
            block_xs = np.asarray(block_xs)
            block_ys = np.asarray(block_ys)

        if roll in [2, 3, 5]:
            for b in range(num_blocks):
                origin_x, dst_x = block_xs[b]
                origin_y, dst_y = block_ys[b]
                swap_block(
                    frame_orig,
                    frame,
                    origin_x,
                    origin_y,
                    dst_x,
                    dst_y,
                    block_sizes[b][0],
                    block_sizes[b][1],
                    block_channels[b],
                )

        if roll_noise in [0, 1]:
            frame = salt_and_pepper(frame, 0.5, 0.02)

        writer.stdin.write(frame.astype(np.uint8).tobytes())
        frame_idx += 1

    # cleanup
    reader.wait()
    writer.stdin.close()
    writer.wait()
