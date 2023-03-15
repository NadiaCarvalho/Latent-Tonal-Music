"""This module implements the dft128 encoder class"""

import itertools

import music21
import numpy as np

from .enc_int import EncoderInterface
from .utils import calculate_augmentation, dft_inversion, dft_reduction, dft_rotation

class DFT128Encoder(EncoderInterface):
    """

    Attributes
    ----------

    Methods
    ----------

    Note: Use Only first part of DFT
        Check to see if
    """
    resolution = 4  # in how many notes we slice a quarter
    # (1 for quarters, 4 for 16ths, 8 for 32nd etc)
    use_symetric = True

    def __init__(self, data_path, data_name='', resolution=4, transposition='C Major') -> None:
        super().__init__()

        self.name = 'dft128'
        self.resolution = resolution
        self.transposition = transposition
        self.dataset = {
            'path': data_path,
            'name': data_name
        }

        try:
            self.angles = np.load('harmrep/encodings/dft128_angles.npy')
        except:
            self.extract_angles()

    def extract_note_to_list(self, notes_list, note, offset, quarter_length=None):
        """Extract a Note to the Note List"""
        notes_list[offset, note.pitch.midi] = 1

        if quarter_length is None:
            quarter_length = note.quarterLength

        for d_0 in range(1, int(quarter_length*self.resolution)):
            notes_list[offset + d_0, note.pitch.midi + 127] = 1

    def extract_representation_method(self, notes):
        """
        If more than one method, replace here
        """
        return self.method_1(notes)

    def method_1(self, notes):
        """Extract Representation"""
        dur = int(
            (notes[-1].offset+notes[-1].quarterLength)*self.resolution)

        # 128 - ataques
        # 128 - continuações

        pitch_class_vectors = np.zeros((dur, 256), dtype='int16')
        for note in notes:
            offset = int(note.offset*self.resolution)
            if isinstance(note, music21.note.Note):
                self.extract_note_to_list(pitch_class_vectors, note, offset)
            elif isinstance(note, music21.chord.Chord):
                for inner_note in note:
                    self.extract_note_to_list(
                        pitch_class_vectors, inner_note, offset, note.quarterLength)

        # dft 1ºs 128 (retiro 1ºs 64) + dfts 2ºs 128 (retiro 1ºs 64)
        if self.use_symetric:
            dft_attack = [dft_reduction(step[0:128])[0][:][0:65*2]
                          for step in pitch_class_vectors]
            dft_continuations = [dft_reduction(
                step[128:])[0][:][0:65*2] for step in pitch_class_vectors]
        else:
            dft_attack = [dft_reduction(step[0:128])[0]
                          for step in pitch_class_vectors]
            dft_continuations = [dft_reduction(
                step[128:])[0] for step in pitch_class_vectors]

        dft_total = dft_attack
        _ = [d.extend(dft_continuations[i])  # type: ignore
             for i, d in enumerate(dft_total)]
        return dft_total

    def decode_method(self, encoded):
        """Decode Representation"""
        output_notes = []
        offset = 0

        min_duration = 1.0/self.resolution

        for array in encoded:

            atack_arr = array[0:int(len(array)/2)]
            cont_arr = array[int(len(array)/2):]

            if self.use_symetric:
                array_in_tuples = list(zip(atack_arr[::2], atack_arr[1::2]))
                sym_tuples = [(a[0], -1.0*a[1])
                              for a in list(reversed(array_in_tuples[1:-1]))]
                sym_ar = list(itertools.chain.from_iterable(sym_tuples))
                atack_arr = np.concatenate((atack_arr, sym_ar))

                array_in_tuples_c = list(zip(cont_arr[::2], cont_arr[1::2]))
                sym_tuples_c = [(a[0], -1.0*a[1])
                                for a in list(reversed(array_in_tuples_c[1:-1]))]
                sym_ar_c = list(itertools.chain.from_iterable(sym_tuples_c))
                cont_arr = np.concatenate((cont_arr, sym_ar_c))

            i_dft_attack = dft_inversion(atack_arr)
            i_dft_cont = dft_inversion(cont_arr)
            i_dft = np.concatenate((i_dft_attack, i_dft_cont))

            notes = np.where(i_dft > 0)[0]

            # print(i_dft)

            attack_notes = notes[notes < 128]
            for note in attack_notes:
                m21_note = (offset, music21.note.Note(
                    note, quarterLength=min_duration))
                output_notes.append(m21_note)

            cont_notes = notes[notes > 127]
            for note in cont_notes:
                get_last_note = next(
                    (x for x in output_notes[::-1] if x[1].pitch.midi == note - 127), None)
                if get_last_note:
                    # print('GLN', get_last_note)
                    # type: ignore
                    get_last_note[1].quarterLength += min_duration

            offset += min_duration

        part = music21.stream.Stream()  # type: ignore
        _ = [part.insert(off, note) for off, note in output_notes]
        part.flattenUnnecessaryVoices(inPlace=True, force=True)
        return part

    def get_vocab_size_and_embedding(self):
        """Get Vocab Size and Embedding"""
        return 260, False

    def augment_song(self, encoded, augmentation='FD'):
        """Augment Song based on augmentation type"""

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

    def extract_angles(self):
        """Extract Angles"""
        pianobase = np.zeros(128, dtype=np.int32)
        pianobase[1] = 1

        dft_red = dft_reduction(pianobase, return_complex=True)[0]
        self.angles = [np.arctan2(cpl.imag, cpl.real)
                       for cpl in dft_red]  # type: ignore

        with open('harmrep/encodings/dft128_angles.npy', 'wb') as f:
            np.save(f, np.array(self.angles))
