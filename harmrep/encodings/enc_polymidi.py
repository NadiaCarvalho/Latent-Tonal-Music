"""This module implements a second midi encoder class"""

import music21
import numpy as np

from .enc_int import EncoderInterface
from .utils_polymidi import (Event, SplitNote, _event_seq2snote_seq,
                             _make_time_shift_events, _snote2events,
                             transform_notes)

from .utils import calculate_augmentation


class PolyMidiEncoder(EncoderInterface):
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

        self.name = 'polymidi'
        self.resolution = resolution
        self.transposition = transposition
        self.dataset = {
            'path': data_path,
            'name': data_name
        }

    def extract_representation_method(self, notes):
        """
        If more than one method, replace here
        """
        return self.method_1(notes)

    def method_1(self, notes):
        """
        Extract Complex Polyphonic Representation based on MIDI (Music transformer)
        vocabulary has 388 symbols
        * 0–127 Note-on event
        * 128–256 Note-off event
        * 256–288 Velocity event
        * 288–388 Time-shift event
        """
        note_seq = []

        for note in notes:
            if isinstance(note, music21.note.Note):
                note_on = SplitNote('note_on', note.offset,
                                    note.pitch.ps, note.volume.velocity)
                note_off = SplitNote(
                    'note_off', note.offset+note.duration.quarterLength, note.pitch.ps, None)
                note_seq += [note_on, note_off]

            if isinstance(note, music21.chord.Chord):
                for pitch in note.pitches:
                    note_on = SplitNote(
                        'note_on', note.offset, pitch.ps, note.volume.velocity)
                    note_off = SplitNote(
                        'note_off', note.offset+note.duration.quarterLength, pitch.ps, None)
                    note_seq += [note_on, note_off]

        note_seq.sort(key=lambda note: note.time)

        cur_time = 0
        cur_vel = 0

        events = []
        for snote in note_seq:
            events += _make_time_shift_events(prev_time=cur_time,
                                              post_time=snote.time)
            events += _snote2events(snote=snote, prev_vel=cur_vel)

            cur_time = snote.time
            cur_vel = snote.velocity

        return [e.to_int() for e in events]

    def decode_method(self, encoded):
        """Decode Representation"""
        output_notes = []

        event_sequence = [Event.from_int(idx) for idx in encoded]

        note_on_dict = {}

        snote_seq = _event_seq2snote_seq(event_sequence)
        for snote in snote_seq:
            if snote.type == 'note_on':
                note_on_dict[snote.value] = snote
            elif snote.type == 'note_off':
                try:
                    on_note = note_on_dict[snote.value]
                    off = snote
                    if off.time - on_note.time == 0:
                        continue

                    m21_note = music21.note.Note(
                        pitch=snote.value,
                        offset=on_note.time,
                        duration=music21.duration.Duration(
                            off.time - on_note.time),
                        volume=music21.volume.Volume(
                            velocity=on_note.velocity))

                    output_notes.append((on_note.time, m21_note))
                except Exception as exc:
                    print(f'info removed pitch: {snote.value} --- {exc}')

        output_notes.sort(key=lambda x: x[0])
        output_notes_dict = {}
        for note in output_notes:
            key = f'{note[0]}_{note[1].duration.quarterLength}'
            if key not in output_notes_dict:
                output_notes_dict[key] = []
            output_notes_dict[key].append(note[1])

        output_notes_chords = []
        for k, value in output_notes_dict.items():
            offset = float(k.split('_')[0])
            if len(value) == 1:
                value[0].offset = offset
                output_notes_chords.append(value[0])
            else:
                new_chord = music21.chord.Chord(value)
                new_chord.offset = offset
                output_notes_chords.append(new_chord)
        return music21.stream.Part(output_notes_chords)  # type: ignore

    def augment_song(self, encoded, augmentation='FD'):
        """Augment song based on augmentation type"""
        augm_inc = calculate_augmentation(augmentation)
        if encoded.ndim == 1:
            return np.array([transform_notes(note, inc=augm_inc) for note in encoded])
        return np.roll(encoded, augm_inc, axis=1)

    def get_vocab_size_and_embedding(self):
        """Return the size of the vocabulary and the embedding size"""
        return 390, True
