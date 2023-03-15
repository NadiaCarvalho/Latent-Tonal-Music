import copy
import math
from decimal import Decimal

import music21 as m21


class KeyLength:
    def __init__(self, numerator, denominator, factor, error):
        self.numerator = numerator
        self.denominator = denominator
        self.factor = factor
        self.error = error

    def calculate(self):
        """Calculate Key Length"""
        if self.numerator == 0:
            return None, None
        if self.denominator == 1:
            if self.numerator == 1:
                return "", ""
            return "", str(int(self.numerator))
        if self.factor == 0:
            if self.numerator == 1:
                return "", str(int(self.denominator))
            return "", f"{int(self.numerator)}/{int(self.denominator)}"
        if self.factor == 1:
            return f"{int(self.denominator)}/{int(self.numerator)}", ""
        if self.factor > 0:
            return f"({int(self.denominator)}:{int(self.numerator)}", f"/{int(self.factor)}"
        return f"({int(self.denominator)}:{int(self.numerator)}", f"{int(-self.factor)}"

    def __str__(self) -> str:
        return 'numerator: {}, denominator: {}, factor: {}, error: {}'.format(self.numerator, self.denominator, self.factor, self.error)

class Music21Stream2ABC:

    """This class implements the conversion from a music21 stream to ABC"""

    def __init__(self):
        pass

    def convert(self, stream, options={}):
        """Convert MIDI to ABC"""

        time_signatures = list(set([(ts.offset, ts.numerator, ts.denominator) for ts in stream.recurse(
        ).getElementsByClass('TimeSignature')]))

        tempos = [{'time': ts.offset, 'qpm': ts.number}
                      for ts in set(stream.recurse().getElementsByClass('MetronomeMark'))]
        if len(tempos) == 0:
            tempos = [{'time': 0.0, 'qpm': 120}]

        notes = sorted(stream.recurse().notes, key=lambda note: note.activeSite.offset + note.offset)

        abcString = f"X:{options.get('index', '1')}\n"
        if 'title' in options:
            abcString += f"T:{options['title']}\n"
        if 'composer' in options:
            abcString += f"C:{options['composer']}\n"
        if 'meter' in options:
            abcString += f"M:{options['meter']}\n"

        total_time = self.cleanup_time(notes, tempos)
        split_tempos = self.split_tempos(notes, tempos, total_time)

        self.section = 0
        self.section_end = 0
        self.tuplet_num = 0
        self.tuplet_count = 0

        used_midis = []
        instruments = list(stream.recurse().getElementsByClass('Instrument'))
        if len(instruments) == 0:
            instruments = list(stream.recurse().getElementsByClass('Part'))

        for (notes, tempo) in split_tempos:
            abcString += f"Q:{tempo['qpm']}\n"
            instrument_notes = self.split_instruments(notes, instruments)
            for (notes_i, instrumentID) in instrument_notes:
                self.section = 0
                temp_abc, used_midis = self.segment_to_string(
                    stream, notes_i, instrumentID, tempo, copy.deepcopy(time_signatures), options.get('key', 'Cmaj'), used_midis)
                abcString += temp_abc
        return abcString

    def cleanup_time(self, notes, tempos):
        """Cleanup Time"""
        min = notes[0].activeSite.offset + notes[0].offset
        for note in notes:
            note.offset = note.activeSite.offset + note.offset
            if min > 0:
                note.offset -= min

        if min > 0:
            for tempo in tempos:
                tempo['time'] -= min

        return notes[-1].offset + notes[-1].quarterLength

    def cleanup_tempos(self, tempos, total_time):
        """Cleanup Tempos"""
        result = []
        if len(tempos) > 0:
            for i, tempo in enumerate(tempos[:-1]):
                result.append(
                    {'time': tempo['time'], 'qpm': tempo['qpm'], 'timeTo': tempos[i+1]['time']})
        result.append(
            {'time': tempos[-1]['time'], 'qpm': tempos[-1]['qpm'], 'timeTo': total_time})
        return result

    def split_tempos(self, notes, tempos, total_time):
        """Split Tempos"""
        cleaned_tempos = self.cleanup_tempos(tempos, total_time)
        if len(cleaned_tempos) == 1:
            return [[notes, cleaned_tempos[0]]]
        return [[[n for n in notes if n.offset >= tempo['time'] and n.offset < tempo['timeTo']], tempo] for tempo in cleaned_tempos]

    def split_instruments(self, notes, instruments):
        """Split Instruments"""
        if len(instruments) == 0:
            return [(notes, m21.instrument.Instrument('Piano'))]
        elif isinstance(instruments[0], m21.instrument.Instrument):
            return [([n for n in notes if n.getInstrument() == instrument], instrument) for instrument in instruments]
        else:
            return [([n for n in notes if instrument in n.containerHierarchy()], instrument) for instrument in instruments]

    def segment_to_string(self, stream, notes, instrumentID, tempo, time_signatures, key, used_midis=[]):
        """Segment to String"""
        if len(notes) == 0:
            return ""

        time_signature = time_signatures.pop()

        beat = float(time_signature[1])/float(time_signature[2])
        unit_length = 2 if beat < 0.75 else 4
        unit_time = tempo['qpm'] * unit_length
        section_length = 240 / (tempo['qpm'] * beat)

        abc_string, used_midis = self.set_instrument_header(
            notes, instrumentID, unit_length, time_signature, key, used_midis)

        self.section = 1
        self.section_end = tempo['time'] + self.section * section_length
        time_signature = time_signatures.pop() if len(time_signatures) > 0 else None

        chords = sorted(self.get_chord(notes), key=lambda x: x[0]['start'])
        for i, chord in enumerate(chords):
            next_chord = chords[i+1] if i < len(chords)-1 else None

            if i == 0 and chord[0]['start'] != tempo['time']:
                abc_string += self.duration_to_rest_strings(
                    tempo['time'], chord[0]['start'], tempo, unit_time, section_length)

            if round(self.section_end, 13) < round(chord[0]['end'], 13):
                abc_string += self.chord_to_tie_string(
                    chord, next_chord, unit_time, section_length, tempo)
            else:
                abc_string += self.chord_to_string(
                    chord, next_chord, unit_time)

            if next_chord is not None:
                abc_string += self.duration_to_rest_strings(
                    chord[0]['end'], next_chord[0]['start'], tempo, unit_time, section_length)
            else:
                abc_string += self.duration_to_rest_strings(
                    chord[0]['end'], tempo['timeTo'], tempo, unit_time, section_length)
                if not abc_string.endswith('\n'):
                    abc_string += '\n'

        return abc_string, used_midis

    def get_chord(self, notes):
        """Get Chord"""
        grouped_notes = {}
        for note in notes:
            note_offset = note.offset

            if note_offset not in grouped_notes:
                grouped_notes[note_offset] = {}

            note_end = note_offset + note.quarterLength
            if note_end not in grouped_notes[note_offset]:
                grouped_notes[note_offset][note_end] = []
            grouped_notes[note_offset][note_end].append(
                (note.tie.type if note.tie is not None else "None", [(n.midi, n.name) for n in note.pitches]))

        new_start_time = None

        result = []
        for start_time in grouped_notes:
            for end_time in grouped_notes[start_time]:

                result_s_e = []
                for note in grouped_notes[start_time][end_time]:
                    if note[0] == 'start':
                        new_start_time = start_time
                        continue

                    for n in note[1]:
                        parsed_n = {'start': new_start_time if (note[0] == 'stop' and new_start_time is not None) else start_time,
                                    'end': end_time,
                                    'pitch': n,
                                    'tie': True if note[0] == 'stop' else False}
                        if parsed_n not in result_s_e:
                            result_s_e.append(parsed_n)

                if len(result_s_e) > 0:
                    result.append(result_s_e)
        return result

    def token_to_pitch(self, token):
        """Key String to Pitch"""
        na = { '^': '#', '_': '-', '^^': '##', '__': '--' }
        new_acc = na[token['acc']] if token['acc'] is not None else ''
        note = f"{token['note']}{new_acc}"
        pitch = m21.pitch.Pitch(f"{note}{4+int(token['octave'])}")
        return (pitch.midi, note)

    def note_to_key_string(self, note):
        """Note to Key String"""
        baseline = note['pitch'][0] - 60
        height = math.floor(baseline / 12)

        name = note['pitch'][1].replace('#', '^').replace('-', '_')[::-1]

        if math.floor(baseline / 12) >= 1:
            key_string = name.lower()
            key_string += "'" * int(height - 1)
        else:
            key_string = name
            key_string += "," * int(abs(height))

        return key_string

    def fix_illegal_duration(self, chord, next_chord, unit_time, key_length, duration):
        """Fix Illegal Duration"""
        if key_length.error == 0:
            return None

        abc_string = ""
        if key_length.numerator / key_length.denominator > 1:
            new_duration = 60 * key_length.numerator / key_length.denominator / unit_time

            o_st = chord[0]['start']
            o_end = chord[0]['end']

            n_st = new_duration + chord[0]['start']
            for n in chord:
                n['start'] = n_st

            abc2 = self.chord_to_string(chord, next_chord, unit_time)
            for n in chord:
                n['start'] = o_st
                n['end'] = n_st
                if abc2 == "":
                    n['tie'] = "None"
                else:
                    n['tie'] = "start"

            abc1 = self.chord_to_string(chord, None, unit_time)
            for n in chord:
                n['end'] = o_end
            duration = round(duration, 6)
            print(
                f'illegal duration is rounded {duration}, {key_length.error}, {abc_string}')
            return abc1 + abc2
        elif next_chord is not None:
            diff = key_length.error / unit_time
            for n in next_chord:
                if chord[0]['end'] == next_chord[0]['start']:
                    n['start'] -= diff
                n['end'] -= diff
            abc_string += self.chord_to_string(chord, next_chord, unit_time)
            duration = round(duration, 6)
            print(
                f'illegal duration is rounded {duration}, {key_length.error}, {abc_string}')
            return abc_string

        return None

    def note_to_string(self, chord, next_chord, unit_time):
        """Note to String"""
        note = chord[0]
        key_string = self.note_to_key_string(note)

        duration = (note['end'] - note['start']) * unit_time
        key_length = self.approximate_key_length(duration)

        if key_length.numerator == 0:
            return ""

        abc = self.fix_illegal_duration(
            chord, next_chord, unit_time, key_length, duration)
        if abc is not None:
            return abc

        len1, len2 = key_length.calculate()
        tie = "-" if chord[0]['tie'] else ""
        tuplet_string = self.get_tuplet_string(len1, key_length)
        return tuplet_string + key_string + str(len2) + tie

    def chord_to_string(self, chord, next_chord, unit_time):
        """Chord to String"""
        if len(chord) == 1:
            return self.note_to_string(chord, next_chord, unit_time)

        ties_map = ["-" if n['tie'] else "" for n in chord]
        str_map = ''.join([self.note_to_key_string(n) + ties_map[i] for i, n in enumerate(chord)])

        n = chord[0]
        duration = (n['end'] - n['start']) * unit_time
        key_length = self.approximate_key_length(duration)
        if key_length.numerator == 0:
            return ""

        abc = self.fix_illegal_duration(
            chord, next_chord, unit_time, key_length, duration)
        if abc is not None:
            return abc

        len1, len2 = key_length.calculate()
        tuplet_string = self.get_tuplet_string(len1, key_length)
        return tuplet_string + "[" + str_map + "]" + str(len2)

    def chord_to_tie_string(self, chord, next_chord, unit_time, section_length, tempo):
        """Chord to Tie String"""
        abc_string = ""
        end_time = chord[0]['end']

        for n in chord:
            n['end'] = self.section_end

        if round(self.section_end, 13) == round(end_time, 13):
            # Chord is not tied
            for n in chord:
                n['tie'] = False

            abc_string += self.chord_to_string(chord, next_chord, unit_time)
            abc_string += "|"
            if self.section % 4 == 0:
                abc_string += "\n"
            self.section += 1
            self.section_end = tempo['time'] + self.section * section_length
            return abc_string
        else:
            # Chord is tied
            for n in chord:
                n['tie'] = True

            abc_string += self.chord_to_string(chord, next_chord, unit_time)

            abc_string += "|"
            count = math.floor(
                (end_time - chord[0]['start']) / section_length)
            if self.section % 4 == 0:
                abc_string += "\n"
            for _ in range(1, count):
                next_section = self.section + 1
                next_section_end = tempo['time'] + next_section * section_length
                for n in chord:
                    n['start'] = self.section_end
                    n['end'] = next_section_end

                if round(next_section_end, 13) == round(end_time, 13):
                    for n in chord:
                        n['tie'] = False

                    abc_string += self.chord_to_string(
                        chord, next_chord, unit_time)
                    abc_string += "|"
                    if self.section % 4 == 0:
                        abc_string += "\n"
                    self.section = next_section
                    self.section_end = next_section_end
                    return abc_string
                else:
                    for n in chord:
                        n['tie'] = True

                    abc_string += self.chord_to_string(
                        chord, next_chord, unit_time)
                    abc_string += "|"
                    if self.section % 4 == 0:
                        abc_string += "\n"
                    self.section = next_section
                    self.section_end = next_section_end

            for n in chord:
                n['tie'] = False
                n['start'] = self.section_end
                n['end'] = end_time

            abc_string += self.chord_to_string(chord, next_chord, unit_time)
            self.section += 1
            self.section_end = tempo['time'] + self.section * section_length
            return abc_string

    def split_rest_duration(self, duration):
        """Split Rest Duration"""
        base = 60
        duration = round(duration * 6) / 6
        if duration <= base:
            return [duration]

        result = []
        while duration > base:
            n = 2
            while duration / n > base:
                n *= 2
            if duration / n == base:
                result.append(duration)
                return result
            else:
                rest = n * 30
                result.append(rest)
                duration -= rest

        result.append(duration)
        return result

    def approximate_key_length(self, duration):
        base = 60
        duration = round(duration * 6) / 6
        if duration == base:
            return KeyLength(1, 1, 0, 0)
        if duration <= 0:
            print(f"duration is negative: {duration}")
            return KeyLength(0, 0, 0, duration)
        if duration * 8 < base:
            # abc.js does not support duration less than z/8.
            print(f"duration (less than z/8) is ignored: {duration}")
            return KeyLength(0, 0, 0, duration)

        n = 2
        if duration > base:
            # normal note
            while duration / n > base:
                n *= 2
            if duration / n == base:
                return KeyLength(n, 1, 0, 0)
            # dotted note
            n /= 2
            nearestDiff = duration / n - base
            nearestNumerator = n
            nearestDenominator = 1
            for p in [2, 4, 8, 16]:
                q = 2 * p - 1
                k = n * q / p
                diff = round(duration / k, 6) - base
                if diff == 0:
                    if k == round(k):
                        return KeyLength(k, 1, 0, 0)
                    return KeyLength(n * q, p, 0, 0)
                elif 0 < diff < nearestDiff:
                    nearestDiff = diff
                    nearestNumerator = n * q
                    nearestDenominator = p
            # tuplet
            # - prime numbers only (consider speed)
            # - max denominator is 9 (limitation of abc.js)
            n *= 2
            for i in [3, 5, 7]:
                for j in range(1, i):
                    if math.isclose(duration / n * i / j, base):
                        return KeyLength(j, i, -n, 0)
            diff = duration - base * nearestNumerator / nearestDenominator
            return KeyLength(nearestNumerator, nearestDenominator, 0, diff)
        else:
            # normal note
            while duration * n < base:
                n *= 2
            if math.isclose(duration * n, base):
                return KeyLength(1, n, 0, 0)
            # dotted note
            nearestDiff = duration * n - base
            nearestNumerator = 1
            nearestDenominator = n
            for p in [2, 4, 8, 16]:
                q = 2 * p - 1
                k = q / (n * p)
                diff = abs(round(duration / k, 6) - base)
                if math.isclose(diff, 0):
                    if k == round(k):
                        return KeyLength(k, 1, 0, 0)
                    else:
                        return KeyLength(q, n * p, 0, 0)
                elif diff < nearestDiff:
                    nearestDiff = diff
                    nearestNumerator = q
                    nearestDenominator = n * p
            # tuplet
            # - prime numbers only (consider speed)
            # - max denominator is 9 (limitation of abc.js)
            for i in [3, 5, 7]:
                for j in range(1, i):
                    n_copy = n
                    while n_copy >= 1:
                        if duration * n_copy * i / j == base:
                            return KeyLength(j, i, n_copy, 0)
                        n_copy /= 2

            diff = duration - base * nearestNumerator / nearestDenominator
            return KeyLength(nearestNumerator, nearestDenominator, 0, diff)

    def get_tuplet_string(self, len1, keyLength):
        """Get Tuplet String"""
        if self.tuplet_count == 0 and keyLength.factor != 0:
            self.tuplet_num = keyLength.denominator
            self.tuplet_count += 1
            return str(len1)
        if self.tuplet_count < self.tuplet_num:
            self.tuplet_count += 1
            if self.tuplet_count == self.tuplet_num:
                self.tuplet_count = 0
                self.tuplet_num = 0
            return ""
        return ""

    def duration_to_rest_string(self, start_time, end_time, unit_time):
        """Duration to Rest String"""
        if start_time < end_time:
            duration = (end_time - start_time) * unit_time
            abc = ""
            for d in self.split_rest_duration(duration):
                keyLength = self.approximate_key_length(d)
                len1, len2 = keyLength.calculate()
                if len2 is None:
                    continue
                tupletString = self.get_tuplet_string(len1, keyLength)
                abc += tupletString + "z" + len2
            return abc
        else:
            return ""

    def duration_to_rest_strings(self, start_time, end_time, tempo, unit_time, section_length):
        """Duration to Rest Strings"""
        abc_string = ""

        if round(self.section_end, 13) <= round(end_time, 13):
            prev_section_end = self.section_end
            if round(start_time, 13) < round(self.section_end, 13):
                abc_string += self.duration_to_rest_string(
                    start_time, self.section_end, unit_time)
                abc_string += "|"
                if self.section % 4 == 0:
                    abc_string += "\n"
                self.section += 1
                self.section_end = tempo['time'] + self.section * section_length

                for _ in range(math.floor(
                    (end_time - prev_section_end) / section_length)):
                    abc_string += self.duration_to_rest_string(
                        prev_section_end, self.section_end, unit_time)
                    abc_string += "|"

                    if self.section % 4 == 0:
                        abc_string += "\n"

                    self.section += 1
                    prev_section_end = self.section_end
                    self.section_end = tempo['time'] + self.section * section_length

                abc_string += self.duration_to_rest_string(
                    prev_section_end, end_time, unit_time)

            else:
                if round(self.section_end, 13) == round(start_time, 13):
                    abc_string += "|"

                    if self.section % 4 == 0:
                        abc_string += "\n"

                    self.section += 1
                    self.section_end = tempo['time'] + self.section * section_length

                if round(end_time, 13) < round(self.section_end, 13):
                    abc_string += self.duration_to_rest_string(
                        start_time, end_time, unit_time)
                else:
                    abc_string += self.duration_to_rest_string(
                        start_time, self.section_end, unit_time)
                    abc_string += "|"

                    if self.section % 4 == 0:
                        abc_string += "\n"

                    self.section += 1
                    prev_section_end = self.section_end
                    self.section_end = self.section * section_length

                    for _ in range(math.floor(
                        (end_time - prev_section_end) / section_length)):
                        abc_string += self.duration_to_rest_string(
                            prev_section_end, self.section_end, unit_time)
                        abc_string += "|"

                        if self.section % 4 == 0:
                            abc_string += "\n"

                        self.section += 1
                        prev_section_end = self.section_end
                        self.section_end = tempo['time'] + self.section * section_length

                    abc_string += self.duration_to_rest_string(
                        prev_section_end, end_time, unit_time)

        elif round(start_time, 13) < round(end_time, 13):
            abc_string += self.duration_to_rest_string(
                start_time, end_time, unit_time)

        return abc_string

    def set_instrument_header(self, notes, instrumentID, unit_length, time_signature, key, used_midis=[]):
        """Set Instrument Header"""
        header_string = f"L:1/{4 * unit_length}\n"
        header_string += f"M:{time_signature[1]}/{time_signature[2]}\n"
        header_string += f"K:{key} clef={self.guess_clef(notes)}\n"

        instrument = notes[0].getInstrument()
        if instrument is None:
            instrument = m21.instrument.Instrument()

        instrumentID = instrument.partId
        program = instrument.autoAssignMidiChannel(used_midis)
        used_midis.append(program)

        header_string += f"V:{instrumentID}\n"
        header_string += f"%%MIDI program {program}\n"

        return header_string, used_midis

    def guess_clef(self, notes):
        """Guess Clef"""
        pitches_nf = [[n1.midi for n1 in n.pitches]
                      for n in notes if n is not None]
        pitches = [ptch for sublist in pitches_nf for ptch in sublist]
        if sum(pitches) / len(pitches) > 64:
            return "G2"
        return "F4"
