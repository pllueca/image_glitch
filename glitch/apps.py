import imageio
import numpy as np
from random import choice

from .image_glitch import (
    move_random_blocks,
    move_channels_random,
    salt_and_pepper,
    swap_block,
    move_channel,
)
from .video_utils import (
    get_video_size,
    start_ffmpeg_reader,
    start_ffmpeg_writer,
    read_frame,
)

ASPECT_RATIOS = [
    [1, 1],
    [1, 4],
    [4, 1]
]

def glitch_image(input_path: str, output_path: str,
            float = 0.5, block_size: float = 0.5, block_count: int = 15,
            noise_intensity: float = 0.5, noise_amount: float = 0.5,
            channels_movement: float = 0.5) -> None:
    """ swaps some random blocks, random moves channels and adds salt and pepper noise to the image
    """
    image = imageio.imread(input_path)

    if block_count and block_size:
        size  = int(min(image.shape[0], image.shape[1]) / 2 * block_size)

        blocks_moved = 0

        while blocks_moved < block_count:
            remaining_blocks = block_count - blocks_moved
            
            # Move blocks with given aspect ratio
            num_blocks    = np.random.randint(1, remaining_blocks) if remaining_blocks > 1 else 1

            blocks_moved += num_blocks

            aspect = choice(ASPECT_RATIOS)
            max_blocksize = [x * size for x in aspect]
            image = move_random_blocks(
                image,
                max_blocksize=max_blocksize,
                num_blocks=num_blocks,
                per_channel=True
            )
    
    if channels_movement:
        delta = int(channels_movement * 20)
        image = move_channels_random(image, -delta, delta)

    if noise_amount and noise_intensity:
        image = salt_and_pepper(image, noise_intensity, 1 - noise_amount)

    imageio.imwrite(output_path, image)


def glitch_video(input_path: str, output_path: str,
            min_effect_length: int = 1, max_effect_length: int = 15,
            noise_intensity: float = 0.5, noise_amount: float = 0.5,
            block_size: float = 0.5, block_count: int = 15,
            channels_movement: float = 0.5) -> None:
    """ glitches a video. 
    Different types of glitches are applied to chunks of the video. Each glitch
    has a random duration between `min_effect_length` and `max_effect_length`
    consecutive frames. Avalaible glitches are:
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
    remaining_frames_effect = 0
    frame_idx = 0
    
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
                effect = configure_effect(width, height,
                    min_blocks     = 1,
                    max_blocks     = block_count,
                    min_block_size = int(block_size * 200),
                    max_block_size = int(block_size * 1200)
                )

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
            delta = channels_movement * 15
            frame = move_channels_random(frame, -delta, delta)

        if roll in [3, 5]:
            effect = configure_effect(width, height,
                min_blocks =      1,
                max_blocks =      block_count,
                min_block_size =  int(block_size   * 100),
                max_block_size =  int(block_size   * 800)
            )

        if roll in [2, 3, 5]:
            for b in range(effect['num_blocks']):
                origin_x, dst_x = effect['block_xs'][b]
                origin_y, dst_y = effect['block_ys'][b]
                swap_block(
                    frame_orig,
                    frame,
                    origin_x,
                    origin_y,
                    dst_x,
                    dst_y,
                    effect['block_sizes'][b][0],
                    effect['block_sizes'][b][1],
                    effect['block_channels'][b],
                )

        if roll_noise in [0, 1]:
            frame = salt_and_pepper(frame, noise_intensity, 1 - noise_amount)

        writer.stdin.write(frame.astype(np.uint8).tobytes())
        frame_idx += 1

    # cleanup
    reader.wait()
    writer.stdin.close()
    writer.wait()


def configure_effect(width: int, height: int, min_blocks=1, max_blocks=4,
                    min_block_size=1, max_block_size=None) -> dict:
    
    max_size   = max_block_size or min(height, width)
    num_blocks = np.random.randint(min_blocks, max_blocks)
    
    block_sizes = np.random.randint(
        max(1, min_block_size),
        min(max_size, max_block_size),
        (num_blocks, 2))
    
    block_channels = np.random.randint(0, 3, (num_blocks,))

    block_xs, block_ys = [], []

    for b in range(num_blocks):
        block_xs.append(
            np.random.randint(0, height - block_sizes[b][0], (2,))
        )
        block_ys.append(
            np.random.randint(0, width  - block_sizes[b][1], (2,))
        )

    return {
        'num_blocks':     num_blocks,
        'block_xs':       np.asarray(block_xs),
        'block_ys':       np.asarray(block_ys),
        'block_sizes':    block_sizes,
        'block_channels': block_channels
    }