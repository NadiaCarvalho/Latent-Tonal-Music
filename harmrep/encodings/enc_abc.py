"""This module implements the midi encoder class"""

import re

import music21

from .enc_int import EncoderInterface
from .utils import transpose_notes, calculate_augmentation
from .midi2abc import Music21Stream2ABC


def transpose_abc_token(token, transposition=0):
    """Transpose ABC Token"""
    pitch = Music21Stream2ABC().token_to_pitch(token)  # type: ignore
    new_pitch = (pitch[0] + transposition, music21.pitch.Pitch(pitch[1]).transpose(transposition).name)
    note = Music21Stream2ABC().note_to_key_string({'pitch': new_pitch})
    return f"{note}{token['num'] if token['num'] is not None else ''}{token['slash'] if token['slash'] is not None else ''}{token['den'] if token['den'] is not None else ''}"


class ABCEncoder(EncoderInterface):
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

        self.name = 'abc'
        self.resolution = resolution
        self.transposition = transposition
        self.dataset = {
            'path': data_path,
            'name': data_name
        }

    def extract_representation(self, path, transpose=True, divide_parts=False, expand_repeats=True, index=0):
        """Extract Representation"""
        # try:

        if isinstance(path, str):
            stream = music21.converter.parse(path)
        else:
            stream = path

        if transpose:
            stream = transpose_notes(stream, self.transposition)
        else:
            self.transposition = None

        if expand_repeats:
            stream = stream.expandRepeats()

        time_sig = stream.recurse().getElementsByClass('timeSignature')
        string_time = '4/4'
        if len(time_sig) > 0:
            string_time = time_sig[0].ratioString

        if divide_parts:
            notes = {}
            for part in stream.getElementsByClass('Part'):
                notes[part.id] = part
            return self.save_dict({p: self.extract_representation_method(nts, index=f'{index}_{p}', meter=string_time) for (p, nts) in notes.items()})

        return self.save_list(self.extract_representation_method(stream, index=str(index), meter=string_time))

        # except Exception as exc:
        # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(exc).__name__, exc)
        # self.bad_files.append(path)

    def extract_representation_method(self, stream, index="0", meter="4/4", initial_tempo=120):
        """Extract Representation Method"""
        return Music21Stream2ABC().convert(stream.chordify(addTies=False))

    def get_dictionary_of_notes(self):
        return ['\n', "'", '(', ',', '-', '/', '1', '2', '3', '4', '5', '6', '8', '9', ':', 'A', 'B', 'C', 'D', 'E', 'F', 'G', '[', ']', '^', '_', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'z', '|', ' ']

    def augment_song(self, encoded, augmentation='FD'):
        """Extract Representation"""
        transposition = calculate_augmentation(augmentation)

        starter = encoded.split('L:')[0]
        parts = encoded.split('L:')[1:]

        new_encoded = []

        for part in parts:
            part_split = part.split('%%MIDI program')
            core_split = part_split[1].split('\n')

            starter_p = '%%MIDI program'.join([part_split[0], core_split[0]])

            core_transposed = []

            for line in core_split[1:]:
                tokens = []
                j = 0
                while j < len(line):
                    m = re.match(
                        r"(?P<acc>\^|\^\^|=|_|__)?(?P<note>[a-gA-G])(?P<oct>[,']*)(?P<num>\d+)?(?P<slash>/+)?(?P<den>\d+)?", line[j:])
                    if m:
                        g = m.groupdict()
                        g['octave'] = int(g['note'].islower())
                        if g['oct'] is not None:
                            g['octave'] -= g['oct'].count(",")
                            g['octave'] += g['oct'].count("'")

                        tokens.append(transpose_abc_token(
                            g, transposition=transposition))

                        j += m.end()
                        continue
                    else:
                        tokens.append(line[j])
                        j += 1
                        continue

                core_transposed.append(''.join(tokens))

            joined_core_transposed = '\n'.join(core_transposed)
            new_encoded.append('\n'.join([starter_p, joined_core_transposed]))
        return starter + 'L:' + 'L:'.join(new_encoded)

    def decode(self, encoded):
        """Decode Representation"""
        if not isinstance(encoded, dict):
            parts = encoded.split('L:')

            starter = parts[0]
            parts = parts[1:]
            encoded = {}
            for i, p in enumerate(parts):
                encoded[f'p{i}'] = 'L:'.join([starter, p])

        stream = music21.stream.Stream()  # type: ignore
        for _, enc in encoded.items():
            part = music21.stream.Part(self.decode_method(enc)) # type: ignore
            part.makeNotation(inPlace=True)
            stream.insert(0.0, part)
        return stream

    def sample_file(self, file, file_id=0, seq_len=12):
        """
        sample a file by seq_len
        """
        if len(file) < seq_len:
            return None
        return (f'Song:{file_id}', int(len(file) - seq_len))

    def decode_method(self, encoded):
        """Extract Representation"""
        return music21.converter.parse(encoded, format='abc')

    def get_vocab_size_and_embedding(self):
        """Get Vocab Size and Embedding Necessity"""
        return len(self.get_dictionary_of_notes()), True
