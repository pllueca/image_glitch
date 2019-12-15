""" Image glitchig functions """

from typing import Optional, Tuple
import numpy as np

NumpyArray = np.ndarray  # for typing


def move_channel(arr: NumpyArray, channel: int, deltax: int, deltay: int) -> NumpyArray:
    """ move the given channel in the direction (deltax, deltay) """
    w, h, c = arr.shape
    if channel >= c:
        raise ValueError(f"image only have {c} channels")

    if deltax < 0 and deltay < 0:
        arr[: w + deltax, : h + deltay, channel] = arr[-deltax:, -deltay:, channel]
    elif deltax > 0 and deltay > 0:
        arr[deltax:, deltay:, channel] = arr[:-deltax, :-deltay, channel]
    elif deltax > 0 and deltay < 0:
        arr[deltax:, : h + deltay, channel] = arr[:-deltax, -deltay:, channel]
    elif deltax < 0 and deltay > 0:
        arr[: w + deltax, deltay:, channel] = arr[-deltax:, :-deltay, channel]
    else:
        arr[..., channel] = arr[..., channel]
    return arr


def move_channels_random(
    arr: NumpyArray, min_delta: int = -50, max_delta: int = 50
) -> NumpyArray:
    """ move each channel a random amount between -val and val"""
    res = arr.copy()
    for channel in range(arr.shape[-1]):
        deltax, deltay = np.random.randint(min_delta, max_delta, (2,))
        res = move_channel(res, channel, deltax, deltay)
    return res


def swap_block(
    origin_arr: NumpyArray,
    dst_arr: NumpyArray,
    origin_block_x: int,
    origin_block_y: int,
    dst_block_x: int,
    dst_block_y: int,
    block_width: int,
    block_height: int,
    channel: Optional[int] = None,
) -> NumpyArray:
    """ swap the contents of the blocks. If channel is None, swap all the channels """
    channel = channel or ...
    dst_arr[
        origin_block_x : origin_block_x + block_width,
        origin_block_y : origin_block_y + block_height,
        channel,
    ] = origin_arr[
        dst_block_x : dst_block_x + block_width,
        dst_block_y : dst_block_y + block_height,
        channel,
    ]

    dst_arr[
        dst_block_x : dst_block_x + block_width,
        dst_block_y : dst_block_y + block_height,
        channel,
    ] = origin_arr[
        origin_block_x : origin_block_x + block_width,
        origin_block_y : origin_block_y + block_height,
        channel,
    ]

    return dst_arr


def move_random_blocks(
    arr: NumpyArray,
    max_blocksize: Tuple[int, int] = (5, 5),
    num_blocks: int = 5,
    per_channel: bool = False,
) -> NumpyArray:
    """ swap `num_blocks` of size `blocksize` in arr """
    res = arr.copy()
    w, h, n_channels = arr.shape

    max_block_size_x, max_block_size_y = max_blocksize

    # Prevent block size being bigger than the image itself
    max_block_size_x = min(w, max_block_size_x)
    max_block_size_y = min(h, max_block_size_y)

    for _ in range(num_blocks):
        block_size_x = np.random.randint(1, max_block_size_x)
        block_size_y = np.random.randint(1, max_block_size_y)

        block_origin_x = np.random.randint(0, w - block_size_x)
        block_origin_y = np.random.randint(0, h - block_size_y)

        block_dest_x = np.random.randint(0, w - block_size_x)
        block_dest_y = np.random.randint(0, h - block_size_y)

        if per_channel:
            channel = np.random.randint(0, n_channels)
        else:
            channel = None

        res = swap_block(
            arr,
            res,
            block_origin_x,
            block_origin_y,
            block_dest_x,
            block_dest_y,
            block_size_x,
            block_size_y,
            channel,
        )
    return res

def scanlines(
    arr: NumpyArray,
    intensity: float = 0.5,
    band_size: int = 5,
    band_spacing: int = 15,
    noisy: bool = False,
    per_channel: bool = False,
) -> NumpyArray:
    """ swap `num_blocks` of size `blocksize` in arr """
    res = arr.copy()
    h, w, n_channels = arr.shape
    
    # Prevent block size being bigger than the image itself
    for i in range(int(h / band_spacing)):
        band_size_x = w
        band_size_y = band_size

        band_start_x = 0
        band_start_y = band_spacing * i + np.random.randint(0, 2)

        band_end_x = band_size_x
        band_end_y = band_start_y + band_size

        if band_end_y >= h:
            break

        if per_channel:
            channel = np.random.randint(0, n_channels)
        else:
            channel = None

        channel = channel or ...

        if noisy:
            res[
                band_start_y : band_end_y,
                band_start_x : band_end_x,
                ...,
            ] = np.multiply(arr[
                    band_start_y : band_end_y,
                    band_start_x : band_end_x,
                    ...,
                ],
                np.random.randint(0, 256, (band_size_y, band_size_x, n_channels), np.uint8))
        else:
            intensity_factor = 1 - ((band_start_y % 10) / 40 * intensity)
            res[
                band_start_y : band_end_y,
                band_start_x : band_end_x,
                ...,
            ] = intensity_factor * arr[
                band_start_y : band_end_y,
                band_start_x : band_end_x,
                ...,
            ]

    res = res * (1 - np.random.random() / 5)

    return res


def flip_block(
    arr: NumpyArray, blocksize: Tuple[int, int], per_channel: bool
) -> NumpyArray:
    """ Flips vertically and horizontally the content of a random block of `blocksize` size.
  if `per_channel` a random block is flipped in each channel """
    res = arr.copy()
    w, h, n_channels = arr.shape
    block_size_x, block_size_y = blocksize

    block_x = np.random.randint(0, w - block_size_x)
    block_y = np.random.randint(0, h - block_size_y)

    if per_channel:
        # each channel have 50% prob of flipping
        for c in range(n_channels):
            if np.random.randint(0, 1):
                flipped_block = arr[
                    block_x : block_x + block_size_x,
                    block_y : block_y + block_size_y,
                    c,
                ]
                flipped_block = flipped_block[::-1, ::-1]
                res[
                    block_x : block_x + block_size_x,
                    block_y : block_y + block_size_y,
                    c,
                ] = flipped_block
    else:
        flipped_block = arr[
            block_x : block_x + block_size_x, block_y : block_y + block_size_y, ...
        ]
        flipped_block = flipped_block[::-1, ::-1]
        res[
            block_x : block_x + block_size_x, block_y : block_y + block_size_y
        ] = flipped_block
    return res


def salt_and_pepper(
    arr: NumpyArray, intensity: float = 1.0, noise_frac: float = 0.02
) -> NumpyArray:
    """ replaces random pixels with 255,255,255 or 0,0,0
    noise fraction is the fracion of pixels with noise applied"""
    if not 0 <= intensity <= 1.0:
        raise ValueError("intensity must be between 0 and 1.0!")
    if not 0 <= noise_frac <= 1.0:
        raise ValueError("noise_frac must be between 0 and 1.0!")
    w, h, c = arr.shape

    noise_mask = np.random.random((w, h))
    noise_mask[noise_mask < noise_frac] = 0
    noise_mask[noise_mask >= noise_frac] = 1

    # idx of the pixels that will be replaced with noise
    noise_idxs = np.where(noise_mask == 1)

    noise_rgb = np.random.randint(0, 256, (w, h), np.uint8)
    noise_rgb[noise_rgb > 128] = 255
    noise_rgb[noise_rgb <= 128] = 0
    noise_rgb = np.dstack([noise_rgb,] * c)  # make it accually rgb(a)
    if c == 4:
        # keep original alpha
        noise_rgb[..., -1] = arr[..., -1]

    arr = arr.copy()
    if intensity == 1.0:
        arr[noise_idxs] = noise_rgb[noise_idxs]
    else:
        arr[noise_idxs] = noise_rgb[noise_idxs] * intensity + arr[noise_idxs] * (
            1 - intensity
        )
    return arr
