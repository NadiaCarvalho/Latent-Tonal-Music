"""This module import parts of the
Midi Neural Processor (https://github.com/jason9693/midi-neural-processor)
"""

RANGE_NOTE_ON = 128
RANGE_NOTE_OFF = 128
RANGE_VEL = 32
RANGE_TIME_SHIFT = 100

START_IDX = {
    'note_on': 0,
    'note_off': RANGE_NOTE_ON,
    'time_shift': RANGE_NOTE_ON + RANGE_NOTE_OFF,
    'velocity': RANGE_NOTE_ON + RANGE_NOTE_OFF + RANGE_TIME_SHIFT
}


class SplitNote:
    """SplitNote is a note that is split into note_on and note_off events"""

    def __init__(self, type_of_note, time, value, velocity):
        # type_of_note: ["note_on", "note_off"]
        self.type = type_of_note
        self.time = time
        self.velocity = velocity
        self.value = value

    def __repr__(self):
        """Representation of the SplitNote"""
        return f'<[SNote] time: {self.time} type: {self.type}, value: {self.value}, velocity: {self.velocity}>'


class Event:
    """Event is a note_on, note_off, time_shift or velocity event"""

    def __init__(self, event_type, value):
        # type_of_event: ["note_on", "note_off", "time_shift", "velocity"]
        self.type = event_type
        self.value = value

    def __repr__(self):
        """Representation of the Event"""
        return f'<Event type: {self.type}, value: {self.value}>'

    def to_int(self):
        """Conversion to integer"""
        return START_IDX[self.type] + self.value

    @staticmethod
    def from_int(int_value):
        """Conversion from integer"""
        info = Event._type_check(int_value)
        return Event(info['type'], info['value'])

    @staticmethod
    def _type_check(int_value):
        """Check type of Event"""
        range_note_on = range(0, RANGE_NOTE_ON)
        range_note_off = range(RANGE_NOTE_ON, RANGE_NOTE_ON+RANGE_NOTE_OFF)
        range_time_shift = range(
            RANGE_NOTE_ON+RANGE_NOTE_OFF, RANGE_NOTE_ON+RANGE_NOTE_OFF+RANGE_TIME_SHIFT)

        valid_value = int_value

        if int_value in range_note_on:
            return {'type': 'note_on', 'value': valid_value}
        if int_value in range_note_off:
            valid_value -= RANGE_NOTE_ON
            return {'type': 'note_off', 'value': valid_value}
        if int_value in range_time_shift:
            valid_value -= (RANGE_NOTE_ON + RANGE_NOTE_OFF)
            return {'type': 'time_shift', 'value': valid_value}
        valid_value -= (RANGE_NOTE_ON + RANGE_NOTE_OFF + RANGE_TIME_SHIFT)
        return {'type': 'velocity', 'value': valid_value}


def _make_time_shift_events(prev_time, post_time):
    """Make time shift events"""
    time_interval = int(round((post_time - prev_time) * 100))
    results = []
    while time_interval >= RANGE_TIME_SHIFT:
        results.append(Event(event_type='time_shift',
                       value=RANGE_TIME_SHIFT-1))
        time_interval -= RANGE_TIME_SHIFT
    if time_interval == 0:
        return results
    return results + [Event(event_type='time_shift', value=time_interval-1)]


def _snote2events(snote: SplitNote, prev_vel: int):
    """note to event"""
    result = []
    if snote.velocity is not None:
        modified_velocity = snote.velocity // 4
        if prev_vel != modified_velocity:
            result.append(Event(event_type='velocity',
                          value=modified_velocity))
    result.append(Event(event_type=snote.type, value=snote.value))
    return result


def _event_seq2snote_seq(event_sequence):
    timeline = 0
    velocity = 0
    snote_seq = []

    for event in event_sequence:
        if event.type == 'time_shift':
            timeline += ((event.value+1) / 100)
        if event.type == 'velocity':
            velocity = event.value * 4
        else:
            snote = SplitNote(event.type, timeline, event.value, velocity)
            snote_seq.append(snote)
    return snote_seq


def transform_notes(note, inc=12):
    """Transform notes to a new range for augmentations"""
    if 0 < note < 128:
        note += inc
        if note > 127:
            note = 127 - note
    elif 128 < note < 256:
        note += inc
        if note > 255:
            note = 255 - note
    return int(note)
