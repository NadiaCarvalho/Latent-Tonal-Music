"""This module implements the dft12 encoder class"""

import itertools

import music21
import numpy as np

from .enc_int import EncoderInterface
from .utils import calculate_augmentation, dft_reduction, dft_inversion, dft_rotation
from ..model_train.utils import denormalize


class DFT12Encoder(EncoderInterface):
    """

    Attributes
    ----------

    Methods
    ----------

    """
    resolution = 4  # in how many notes we slice a quarter
    # (1 for quarters, 4 for 16ths, 8 for 32nd etc)
    use_symetric = True

    def __init__(self, data_path, data_name='', resolution=4, transposition='C Major') -> None:
        super().__init__()

        self.name = 'dft12'
        self.resolution = resolution
        self.transposition = transposition
        self.dataset = {
            'path': data_path,
            'name': data_name
        }

        try:
            self.angles = np.load('harmrep/encodings/dft12_angles.npy')
        except:
            self.extract_angles()

    def extract_note_to_list(self, notes_list, note, offset, quarter_length=None, continuation=False):
        """Extract a Note to the Note List"""
        notes_list[offset, note.pitch.pitchClass] = 1

        if quarter_length is None:
            quarter_length = note.quarterLength

        for d_0 in range(1, int(quarter_length*self.resolution)):
            if continuation:
                notes_list[offset + d_0, note.pitch.pitchClass + 12] = 1
            else:
                notes_list[offset + d_0, note.pitch.pitchClass] = 1

    def extract_representation_method(self, notes):
        """
        If more than one method, replace here
        """
        return self.method_1(notes)

    def method_1(self, notes, continuation=True):
        """Extract Representation"""
        dur = int(
            (notes[-1].offset+notes[-1].quarterLength)*self.resolution)

        pitch_class_vectors = np.zeros(
            (dur, 24 if continuation else 12), dtype='int16')

        for note in notes:
            offset = int(note.offset*self.resolution)
            if isinstance(note, music21.note.Note):
                self.extract_note_to_list(
                    pitch_class_vectors, note, offset, continuation=continuation)
            elif isinstance(note, music21.chord.Chord):
                for inner_note in note:
                    self.extract_note_to_list(
                        pitch_class_vectors, inner_note, offset, note.quarterLength, continuation=continuation)

        dft_attack = [dft_reduction(step[0:12])[0] for step in pitch_class_vectors]
        dft_continuations = [dft_reduction(step[12:])[0] for step in pitch_class_vectors]

        dft_total = dft_attack
        _ = [d.extend(dft_continuations[i])  # type: ignore
             for i, d in enumerate(dft_total)]
        return dft_total

    def decode_method(self, encoded, denormalization=False):
        """Decode Representation"""
        output_notes = []
        offset = 0

        min_duration = 1.0/self.resolution

        for array in encoded:

            print(array)
            print()

            if denormalization:
                array = denormalize(array / 100.0, -6.0, 6.0)
                print(array)
                print()

            half_array = int(len(array)//2)

            array[0] = np.abs(np.round(array[0])).astype('float64')
            array[1] = 0.0
            if array[0] == 0.0:
                array[2:half_array] = 0.0

            i_dft_attack = dft_inversion(array[0:int(len(array)/2)])

            array[half_array] = np.abs(np.round(array[half_array])).astype('float64')
            array[half_array+1] = 0.0
            if array[half_array] == 0.0:
                array[half_array+2:] = 0.0

            i_dft_cont = dft_inversion(array[half_array:])

            print(array)
            print()

            i_dft = np.concatenate((i_dft_attack, i_dft_cont))
            notes = np.where(i_dft != 0)[0]

            print(i_dft)
            print(notes)

            attack_notes = notes[notes < 12]
            for note in attack_notes:
                m21_note = (offset, music21.note.Note(
                    pitchClass=note, quarterLength=min_duration))
                output_notes.append(m21_note)

            cont_notes = notes[notes > 11]
            for note in cont_notes:
                get_last_note = next(
                    (x for x in output_notes[::-1] if x[1].pitch.pitchClass == note - 12), [None])
                if get_last_note and get_last_note[0] is not None:
                    get_last_note[1].quarterLength += min_duration # type: ignore

            offset += min_duration

        print(len(output_notes))

        part = music21.stream.Part() # type: ignore
        _ = [part.insert(off, note) for off, note in output_notes]
        return part

    def augment_song(self, encoded, augmentation='FD'):
        """Augment Song according to augmentation type"""

        inc_augm = np.int64(calculate_augmentation(augmentation))
        half_vector = np.int64(len(encoded[1])/2)

        rec_angles = self.angles[1:int(half_vector/2)]

        # Precalculating the sine and cosine values
        sine_values = np.array(np.tile(np.sin(inc_augm * rec_angles), (encoded.shape[0], 1)), dtype=np.float64)
        cosi_values = np.array(np.tile(np.cos(inc_augm * rec_angles), (encoded.shape[0], 1)), dtype=np.float64)

        # Using Numpy's vectorized operations
        new_encoded_attacks = dft_rotation(np.asarray(
            encoded[:, 0:half_vector], dtype=np.float64), cosi_values, sine_values)
        new_encoded_continuations = dft_rotation(np.asarray(
            encoded[:, half_vector:], dtype=np.float64), cosi_values, sine_values)

        # TODO: Check if possible to optimize anymore
        return np.array(np.concatenate((new_encoded_attacks, new_encoded_continuations), axis=1), dtype=np.float64)

    def get_vocab_size_and_embedding(self):
        """Get the vocab size and embedding size"""
        return 48, False # Check if its 24 or 22

    def extract_angles(self):
        """Extract Angles"""
        pianobase = np.zeros(12, dtype=np.int32)
        pianobase[1] = 1

        dft_red = dft_reduction(pianobase, return_complex=True)[0]
        self.angles = [np.arctan2(cpl.imag, cpl.real)
                       for cpl in dft_red]  # type: ignore

        with open('harmrep/encodings/dft12_angles.npy', 'wb') as f:
            np.save(f, np.array(self.angles))
