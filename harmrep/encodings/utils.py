"""This module implements the encoder interface class"""

import numba
import itertools
import os

import music21
import numpy as np


def dft_reduction(data, normalize=False, return_complex=False):
    """GET DFT"""
    dft = np.fft.fft(data)

    if normalize:
        # GET ENERGY
        energy = dft[0].real
        # REDUCE AND NORMALIZE DFT
        reduced_dft = dft[1: int(len(dft) / 2.0) + 1]
        norm_dft = [df / energy for df in reduced_dft]
        # GET MAGNITUDE
        mag = [abs(CP) for CP in norm_dft]
    else:
        norm_dft = dft
        energy = dft[0].real
        mag = [abs(CP) for CP in norm_dft]

    if return_complex:
        return norm_dft, energy, mag

    real_dft = []
    for complex_coefficient in norm_dft:
        real_dft.append(complex_coefficient.real)
        real_dft.append(complex_coefficient.imag)

    # RETURN
    return real_dft, energy, mag


def dft_inversion(data, denormalize=False, energy=None, mag=None):
    """GET Original"""
    in_dft = np.array([complex(real, data[1::2][i])
                      for i, real in enumerate(data[::2])], dtype='complex_')
    if denormalize:
        print(f'{energy}:{mag}')
    return np.asarray([np.round(f.real, decimals=2) for f in np.fft.ifft(in_dft)], dtype='int16')


# , fastmath=True, parallel=True)
@numba.njit('(float64[:,:])(float64[:,:], float64[:,:], float64[:,:])')
def dft_rotation(old_array, cos_values, sin_values):
    """Perform DFT Rotation"""

    new_array = np.zeros_like(old_array, dtype=np.float64)

    new_array[:, :1] = old_array[:, :1]
    new_array[:, 2::2] = np.multiply(
        old_array[:, 2::2], cos_values) - np.multiply(old_array[:, 3::2], sin_values)
    new_array[:, 3::2] = np.multiply(
        old_array[:, 2::2], sin_values) + np.multiply(old_array[:, 3::2], cos_values)

    return new_array


def note_length_event(quarter_length, resolution=4, maxlen=10):
    """divide note length event by resolution"""
    quantize = 1/resolution
    if quarter_length < 0:
        print('oops')
        return 0
    if quarter_length <= quantize:
        return 256
    if quantize < quarter_length <= maxlen:
        return 255+np.ceil(quarter_length/quantize)
    if quarter_length > 10:
        return 255+np.ceil(maxlen/quantize)+1
    return 256


def transpose_notes(stream, obj_transposition):
    """transpose notes of stream to new key"""
    key = stream.analyze('key')
    new_key = music21.key.Key(obj_transposition.split(' ')[0])

    if key != new_key:

        interval = music21.interval.Interval(0)
        if key.mode == new_key.mode:
            interval = music21.interval.Interval(key.tonic, new_key.tonic)
        else:
            interval = music21.interval.Interval(
                key.relative.tonic, new_key.tonic)
        stream.transpose(interval, inPlace=True)

    return stream


def get_part_voice(note):
    """get part and voice of a note, if existent"""
    hierarchy = note.containerHierarchy()

    part = next((v for v in hierarchy if isinstance(
        v, music21.stream.Part)), None)  # type: ignore
    part_id = None if part is None else part.id
    part_name = None if part is None else part.partName

    voice = next((v for v in hierarchy if isinstance(
        v, music21.stream.Voice)), None)  # type: ignore
    voice_id = None if voice is None else voice.id

    return part_id, part_name, voice_id


def increment_filename(path):
    """increment filename number if a file with same name exists"""
    path, _ = os.path.splitext(path)

    number = 1
    yield path + _
    for number in itertools.count(start=1, step=1):
        yield f'{path}-{number}'


def calculate_augmentation(augmentation):
    """calculate augmentation in semitones"""
    inc_augm = 0
    if augmentation == 'OU':
        inc_augm = 12
    elif augmentation == 'OD':
        inc_augm = -12
    elif 'FU' in augmentation:
        if 'FU' == augmentation:
            augmentation = 'FU1'
        to_aug = int(augmentation[2:])
        inc_augm = 7*to_aug - 12*(to_aug-1)
    elif 'FD' in augmentation:
        if 'FD' == augmentation:
            augmentation = 'FD1'
        to_aug = int(augmentation[2:])
        inc_augm = -7*to_aug + 12*(to_aug-1)
    elif 'UP' in augmentation:
        to_aug = int(augmentation[2:])
        inc_augm = to_aug
    elif 'DW' in augmentation:
        to_aug = int(augmentation[2:])
        inc_augm = -to_aug
    return inc_augm
