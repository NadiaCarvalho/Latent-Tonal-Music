import React from 'react';

const RANGE_NOTE_ON = 128;
const RANGE_NOTE_OFF = 128
//const RANGE_VEL = 32;
const RANGE_TIME_SHIFT = 100;

const START_IDX = {
    'note_on': 0,
    'note_off': RANGE_NOTE_ON,
    'time_shift': RANGE_NOTE_ON + RANGE_NOTE_OFF,
    'velocity': RANGE_NOTE_ON + RANGE_NOTE_OFF + RANGE_TIME_SHIFT
}

class MIDILike extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            notes: null,
            processedNotes: null,
            processedEvents: null,
            totalDuration: null,
            startNote: 0,
        };

        console.log("MIDILike has loaded!");

        this.state.notes = this.props.stream.flat.notes.srcStreamElements.filter(function (item) {
            return item.isClassOrSubclass('Note');
        });

        this.state.processedNotes = [];

        for (let note of this.state.notes) {
            let note_on = {
                type: "note_on",
                value: note.pitch.ps,
                velocity: note.volume.velocity,
                time: note.offset,
            };
            let note_off = {
                type: "note_off",
                value: note.pitch.ps,
                velocity: note.volume.velocity,
                time: note.offset + note.duration.quarterLength,
            };
            this.state.processedNotes.push(note_on)
            this.state.processedNotes.push(note_off);
        };

        this.state.processedNotes.sort(function (a, b) {
            return a.time - b.time;
        });

        let cur_time = 0;
        let cur_vel = 0;
        this.state.processedEvents = [];

        for (let note of this.state.processedNotes) {
            // Make time shift events
            let time_interval = Math.round((note.time - cur_time) * 100);

            while (time_interval >= RANGE_TIME_SHIFT) {
                this.state.processedEvents.push({
                    type: "time_shift",
                    value: RANGE_TIME_SHIFT - 1,
                    time: cur_time,
                });
                time_interval -= RANGE_TIME_SHIFT;
            }
            if (time_interval !== 0) {
                this.state.processedEvents.push({
                    type: "time_shift",
                    value: time_interval - 1,
                    time: cur_time,
                });
            }

            // Make note events
            if (!isNaN(note.velocity)) {
                let modified_vel = Math.floor(note.velocity / 4);
                if (cur_vel !== modified_vel) {
                    this.state.processedEvents.push({
                        type: "velocity",
                        value: modified_vel,
                        time: cur_time,
                    });
                }
            }

            this.state.processedEvents.push({
                type: note.type,
                value: note.value,
                time: cur_time,
            });

            cur_time = note.time;
            cur_vel = note.velocity;
        };

        this.state.processedEvents.forEach(element => {
            element.to_int = START_IDX[element.type] + element.value;
            element.active = false;
        });

        this.state.totalDuration = this.state.processedEvents[this.state.processedEvents.length - 1].time;
    }

    componentDidUpdate() {
        let startNote_time = Math.round(this.props.playposition * this.state.totalDuration);
        this.state.processedEvents.forEach((element, index) => {
            let cellDiv = document.getElementById("midiINT-" + index);

            // TODO: May need to change to account for notes in time_shift
            if (element.time === startNote_time) {
                cellDiv.classList.add("active");
            } else {
                cellDiv.classList.remove("active");
            }

        });
    }

    componentDidMount() {
        this.showMIDILike();
    }

    showMIDILike() {

        let midiDIV = document.createElement("div");
        midiDIV.id = "midiINTs";

        for (let note in this.state.processedEvents) {
            let cellDiv = document.createElement("div");
            cellDiv.id = "midiINT-" + note;
            cellDiv.classList.add("cellMIDILike");

            let textSpan = document.createElement("span");
            textSpan.innerText = this.state.processedEvents[note].to_int;

            cellDiv.appendChild(textSpan);
            midiDIV.appendChild(cellDiv);
        }

        if (document.getElementById("midiINTs")) {
            document.getElementById("midilikeEncoding").replaceChild(midiDIV, document.getElementById("midiINTs"));
        } else {
            document.getElementById("midilikeEncoding").appendChild(midiDIV);
        }
    }


    render() {
        return (
            <div id="midilikeEncoding" className="MIDILike" />
        );
    }
}
export default MIDILike;