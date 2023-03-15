"""This module implements the midi encoder class"""

import music21
import numpy as np

from .enc_int import EncoderInterface
from .utils import calculate_augmentation


class PianoRollEncoder(EncoderInterface):
    """

    Attributes
    ----------

    Methods
    ----------

    """
    resolution = 4  # in how many notes we slice a quarter
    # (1 for quarters, 4 for 16ths, 8 for 32nd etc)

    def __init__(self, data_path, data_name='', resolution=4, transposition='C Major') -> None:
        super().__init__()

        self.name = 'pianoroll'
        self.resolution = resolution
        self.transposition = transposition
        self.dataset = {
            'path': data_path,
            'name': data_name
        }
        self.continuations = True

    def extract_note_to_list(self, notes_list, note, offset):
        """Extract a Note to the Note List"""
        notes_list[offset, note.pitch.midi] = 1

        for d_0 in range(1, int(note.quarterLength*self.resolution)):
            if self.continuations:
                notes_list[offset + d_0, note.pitch.midi + 127] = 1
            else:
                notes_list[offset + d_0, note.pitch.midi] = 1

    def extract_representation_method(self, notes):
        """
        If more than one method, replace here
        """
        return self.method_1(notes)

    def method_1(self, notes):
        """
        - no different voices/tracks

        - sequences of x quantized durations:
            -> 0-127 (attacks); 128-255 (note continuations):
                * 0 : not playing
                * 1 : playing
        """
        dur = int(
            (notes[-1].offset+notes[-1].quarterLength)*self.resolution)
        notes_list = np.zeros((dur, 256 if self.continuations else 128), dtype='int16')

        for note in notes:
            offset = int(note.offset*self.resolution)
            if isinstance(note, music21.note.Note):
                self.extract_note_to_list(notes_list, note, offset)
            elif isinstance(note, music21.chord.Chord):
                for inner_note in note:
                    self.extract_note_to_list(notes_list, inner_note, offset)

        return notes_list

    def decode_method(self, encoded):
        """Decode Representation"""

        min_duration = 1.0/self.resolution

        output_notes = []
        offset = 0

        for array in encoded:
            notes = np.where(array == 1)[0]

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
                    get_last_note[1].quarterLength += min_duration

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
        """Augment a song with a given transformation"""

        inc_augm = calculate_augmentation(augmentation)
        # maintain in the same register type
        return np.roll(encoded, inc_augm, axis=1)

    def get_vocab_size_and_embedding(self):
        """Return the size of the vocabulary and the embedding size"""
        return 256 if self.continuations else 128, True
