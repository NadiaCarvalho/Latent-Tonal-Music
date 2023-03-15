"""This module implements the Tonnetz encoder class"""

import music21
import numpy as np

from .enc_int import EncoderInterface
from .utils import calculate_augmentation


class TonnetzEncoder(EncoderInterface):
    """
    Based on
    Chuan, C.-H., and Herremans, D.,
    "Modeling Temporal Tonal Relations in Polyphonic Music
    through Deep Networks with A Novel Image-Based Representation"
    AAAI 2018, February 2-7, New Orleans, 2018.

    Attributes
    ----------

    Methods
    ----------

    """
    resolution = 4  # in how many notes we slice a quarter
    # (1 for quarters, 4 for 16ths, 8 for 32nd etc)

    TEMPLATE_ROWS = [6, 13, 8, 15, 10, 17, 12, 7, 14, 9, 16, 11,
                     10, 17, 12, 19, 14, 21, 16, 11, 18, 13, 20, 15,
                     14, 21, 16, 23, 18, 25, 20, 15, 22, 17, 24, 19,
                     18, 25, 20, 27, 22, 29, 24, 19, 26, 21, 28, 23,
                     22, 29, 24, 31, 26, 33, 28, 23, 30, 25, 32, 27,
                     26, 33, 28, 35, 30, 37, 32, 27, 34, 29, 36, 31,
                     30, 37, 32, 39, 34, 41, 36, 31, 38, 33, 40, 35,
                     34, 41, 36, 43, 38, 45, 40, 35, 42, 37, 44, 39,
                     38, 45, 40, 47, 42, 49, 44, 39, 46, 41, 48, 43,
                     42, 49, 44, 51, 46, 53, 48, 43, 50, 45, 52, 47,
                     46, 53, 48, 55, 50, 57, 52, 47, 54, 49, 56, 51,
                     50, 57, 52, 59, 54, 61, 56, 51, 58, 53, 60, 55,
                     54, 61, 56, 63, 58, 65, 60, 55, 62, 57, 64, 59,
                     58, 65, 60, 67, 62, 69, 64, 59, 66, 61, 68, 63,
                     62, 69, 64, 71, 66, 73, 68, 63, 70, 65, 72, 67,
                     66, 73, 68, 75, 70, 77, 72, 67, 74, 69, 76, 71,
                     70, 77, 72, 79, 74, 81, 76, 71, 78, 73, 80, 75,
                     74, 81, 76, 83, 78, 85, 80, 75, 82, 77, 84, 79,
                     78, 85, 80, 87, 82, 89, 84, 79, 86, 81, 88, 83,
                     82, 89, 84, 91, 86, 93, 88, 83, 90, 85, 92, 87,
                     86, 93, 88, 95, 90, 97, 92, 87, 94, 89, 96, 91,
                     90, 97, 92, 99, 94, 101, 96, 91, 98, 93, 100, 95,
                     94, 101, 96, 103, 98, 105, 100, 95, 102, 97, 104, 99,
                     98, 105, 100, 107, 102, 109, 104, 99, 106, 101, 108, 103]

    def __init__(self, data_path, data_name='', resolution=4, transposition='C Major') -> None:
        super().__init__()

        self.name = 'tonnetz'
        self.resolution = resolution
        self.transposition = transposition
        self.dataset = {
            'path': data_path,
            'name': data_name
        }

    def extract_note_to_list(self, notes_list, note, offset, continuation=False):
        """Extract a Note to the Note List"""
        try:
            # self.TEMPLATE_ROWS.index(note.pitch.midi)
            row = [i for i, n in enumerate(
                self.TEMPLATE_ROWS) if n == note.pitch.midi]
            notes_list[offset, row] = 1
            for d_0 in range(1, int(note.quarterLength*self.resolution)):
                if continuation:
                    notes_list[offset + d_0, [r +
                                              (len(self.TEMPLATE_ROWS) - 1) for r in row]] = 1
                else:
                    notes_list[offset + d_0, row] = 1
        except Exception:
            print("Note has midi pitch out of range (6-108)")

    def extract_representation_method(self, notes):
        """
        If more than one method, replace here
        """
        return self.method_1(notes)

    def method_1(self, notes, continuations=True):
        """
        - Very similar to piano roll
        - no different voices/tracks

        - sequences of x quantized durations:
            -> according to template
            -> doesn't divide into attacks and continuations (continuations=False)
            -> divides into attacks and continuations (continuations=True)
        """
        dur = int(
            (notes[-1].offset+notes[-1].quarterLength)*self.resolution)

        if continuations:
            notes_list = np.zeros(
                (dur, 2*len(self.TEMPLATE_ROWS)), dtype='int16')
        else:
            notes_list = np.zeros(
                (dur, len(self.TEMPLATE_ROWS)), dtype='int16')

        for note in notes:
            offset = int(note.offset*self.resolution)
            if isinstance(note, music21.note.Note):
                self.extract_note_to_list(
                    notes_list, note, offset, continuations)
            elif isinstance(note, music21.chord.Chord):
                for inner_note in note:
                    self.extract_note_to_list(
                        notes_list, inner_note, offset, continuations)
        return notes_list

    def decode_method(self, encoded):
        """Decode Representation"""

        min_duration = 1.0/self.resolution

        offset = 0
        output_notes = []

        for array in encoded:
            notes = np.where(array == 1)[0]

            if len(array) == 2*len(self.TEMPLATE_ROWS):
                # use attacks and continuations
                attack_notes = notes[notes < len(self.TEMPLATE_ROWS)]
                cont_notes = notes[notes >= len(self.TEMPLATE_ROWS)]
            else:
                # use only attacks
                attack_notes = notes
                cont_notes = []

            for note in attack_notes:
                m21_note = (offset, music21.note.Note(
                    self.TEMPLATE_ROWS[note], quarterLength=min_duration))

                if m21_note not in output_notes:
                    output_notes.append(m21_note)

            midi_cont_notes = set(
                self.TEMPLATE_ROWS[n - (len(self.TEMPLATE_ROWS) - 1)] for n in cont_notes)
            for note in midi_cont_notes:
                get_last_note = next(
                    (x for x in output_notes[::-1] if x[1].pitch.midi == note), [None])

                if get_last_note:
                    get_last_note[1].quarterLength += min_duration # type: ignore

            offset += min_duration

        part = music21.stream.Part()  # type: ignore
        _ = [part.insert(off, note) for off, note in output_notes]
        return part

    def to_one_hot(self, use_dict=None, n_vocab=130, encoded=None):
        """
        transform a vector(iterable) of pianoroll notes in a one-hot representation
        overriding original function, because pianoroll is already one-hot encoded
        """
        one_hot_rep = []

        if encoded is None:
            return

        if isinstance(encoded[0], np.integer):
            encoded = [encoded]

        for song in encoded:
            one_hot_rep.append(np.asarray(song))

        return one_hot_rep

    def augment_song(self, encoded, augmentation='FD'):
        """Augment song based on augmentation type"""

        new_encoded = []

        for array in encoded:
            notes = np.where(array == 1)[0]
            if len(array) == 2*len(self.TEMPLATE_ROWS):
                # use attacks and continuations
                attack_notes = notes[notes < len(self.TEMPLATE_ROWS)]
                cont_notes = notes[notes >= len(self.TEMPLATE_ROWS)]
            else:
                # use only attacks
                attack_notes = notes
                cont_notes = []

            midi_attack_notes = set(self.TEMPLATE_ROWS[n]
                                    for n in attack_notes)
            midi_cont_notes = set(
                self.TEMPLATE_ROWS[n - (len(self.TEMPLATE_ROWS) - 1)] for n in cont_notes)

            inc_augm = calculate_augmentation(augmentation)

            midi_attack_notes = [a_n + inc_augm if 6 <= a_n + inc_augm <= 108 else min(
                [6, 128], key=lambda y:abs(y - a_n)) for a_n in midi_attack_notes]
            midi_cont_notes = [c_n + inc_augm if 6 <= c_n + inc_augm <= 108 else min(
                [6, 128], key=lambda y:abs(y - c_n)) for c_n in midi_cont_notes]

            new_array = np.zeros_like(array)
            for note in midi_attack_notes:
                row = [i for i, n in enumerate(
                    self.TEMPLATE_ROWS) if n == note]
                new_array[row] = 1
            for note in midi_cont_notes:
                row = [i + (len(self.TEMPLATE_ROWS) - 1)
                       for i, n in enumerate(self.TEMPLATE_ROWS) if n == note]
                new_array[row] = 1
            new_encoded.append(new_array)

        return np.array(new_encoded)

    def get_vocab_size_and_embedding(self):
        """Get vocab size and embedding"""
        return 2*len(self.TEMPLATE_ROWS), False
