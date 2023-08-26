import React from 'react';
import './EncodingViewer.css';

import MultiSwitch from './MultiSwitch';

import PianorRoll from './encodings/PianoRoll';
import DFT from './encodings/DFT';
import Tonnetz from './encodings/Tonnetz';
import MIDILike from './encodings/MIDILike';
import ABC from './encodings/ABC';

const verovio = require('verovio');

const JZZ = require('jzz');
require('jzz-midi-smf')(JZZ);
require("jzz-synth-tiny")(JZZ);
JZZ.synth.Tiny.register("Web Audio");
require('jzz-midi-gm')(JZZ);

class EncodingViewer extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            tk: null,
            meiXML: "",
            encoding: "pianoroll",
            currentPage: 1,
            file: null,
            player: null,
            out: null,
            stream: null,
            position: 0,
        }

        this.encodings = {
            pianoroll: "Piano roll",
            pianoroll_cont: "Piano roll (ct.)",
            pitchdft: "Pitch DFT",
            pitchclassdft: "Pitch Class DFT",
            abc: "ABC",
            tonnetz: "Tonnetz",
            midi: "MIDI",
        }

        verovio.module.onRuntimeInitialized = async _ => {
            this.state.tk = new verovio.toolkit();
            console.log("Verovio has loaded!");
        };

        JZZ.requestMIDIAccess({
            sysex: true,
        }).then(
            (access) => {
                //console.log("Access to MIDI", access);
                // console.log(
                //     JZZ({
                //         engine: ["webmidi"],
                //         sysex: true,
                //     }).info()
                // );
                this.state.out = JZZ({
                    engine: ["webmidi"],
                    sysex: true,
                })
                    .or("Cannot start MIDI engine!")
                    .openMidiOut(0)
                    .or("Cannot open MIDI Out!")
                    .and(function () {
                        //console.log("MIDI-Out:", this.name());
                    });
            },
            (error) => console.log("error", error)
        );
        JZZ.close();

        this.playMIDIHandler = this.playMIDIHandler.bind(this);
        this.stopMIDIHandler = this.stopMIDIHandler.bind(this);
        this.pauseMIDIHandler = this.pauseMIDIHandler.bind(this);
        this.continueMIDIHandler = this.continueMIDIHandler.bind(this);

        this.changeEncoding = this.changeEncoding.bind(this);
    }

    componentDidUpdate = () => {
        //console.log("componentDidUpdate");
        verovio.module.onRuntimeInitialized = async _ => {
            this.setState(() => ({ tk: new verovio.toolkit() }),
                () => { console.log("Verovio has loaded!"); });
        };
    }

    setPlaying() {
        this.interval = setInterval(() => {
            this.midiHightlightingHandler(this.state.player.positionMS(), this.state.player.positionMS() / this.state.player.durationMS());
        }, 120);
    }
    removePlaying() {
        if (this.interval) {
            clearInterval(this.interval);
        }
    }

    playMIDIHandler = () => {
        // Get the MIDI file from the Verovio toolkit
        let base64midi = this.state.tk.renderToMIDI();

        // Add the data URL prefixes describing the content (MIDIJS)
        // let midiString = 'data:audio/midi;base64,' + base64midi;

        this.setState(() => ({ player: new JZZ.MIDI.SMF(JZZ.lib.fromBase64(base64midi)).player() }),
            () => {
                this.state.player.connect(this.state.out);
                // eslint-disable-next-line react/no-direct-mutation-state
                this.state.player.onEnd = () => {
                    this.stopMIDIHandler();
                };
                this.setPlaying();
                this.state.player.play();

                document.getElementById("pauseMIDI").removeAttribute("disabled");

                document.getElementById("playMIDI").innerText = "Stop";
                document.getElementById("playMIDI").addEventListener("click", this.stopMIDIHandler);
                document.getElementById("playMIDI").removeEventListener("click", this.playMIDIHandler);
            });
    }
    stopMIDIHandler = () => {
        this.removePlaying();
        this.state.player.stop();

        let playingNotes = document.querySelectorAll('g.note.playing');
        for (let playingNote of playingNotes) playingNote.classList.remove("playing");

        this.setState(() => ({ currentPage: 1, position: 0 }),
            () => {
                document.getElementById("notation").innerHTML = this.state.tk.renderToSVG(this.state.currentPage);
                document.getElementById("playMIDI").innerText = "Play";
                document.getElementById("playMIDI").addEventListener("click", this.playMIDIHandler);
                document.getElementById("playMIDI").removeEventListener("click", this.stopMIDIHandler);
                document.getElementById("pauseMIDI").setAttribute("disabled", true);
            });
    }
    pauseMIDIHandler = () => {
        this.removePlaying();
        this.state.player.pause();

        document.getElementById("pauseMIDI").innerText = "Continue";
        document.getElementById("pauseMIDI").addEventListener("click", this.continueMIDIHandler);
        document.getElementById("pauseMIDI").removeEventListener("click", this.pauseMIDIHandler);
    }
    continueMIDIHandler = () => {
        this.setPlaying();
        this.state.player.resume();

        document.getElementById("pauseMIDI").innerText = "Pause";
        document.getElementById("pauseMIDI").addEventListener("click", this.pauseMIDIHandler);
        document.getElementById("pauseMIDI").removeEventListener("click", this.continueMIDIHandler);
    }

    midiHightlightingHandler = (positionMS, position) => {
        // Remove the attribute 'playing' of all notes previously playing
        let playingNotes = document.querySelectorAll('g.note.playing');
        for (let playingNote of playingNotes) playingNote.classList.remove("playing");

        // Get elements at a time in milliseconds (time from the player is in seconds)
        let currentElements = this.state.tk.getElementsAtTime(positionMS);

        if (currentElements.page === 0) return;

        if (currentElements.page !== this.state.currentPage) {
            this.setState(() => ({ currentPage: currentElements.page }),
                () => {
                    document.getElementById("notation").innerHTML = this.state.tk.renderToSVG(this.state.currentPage);
                });
        }

        // Get all notes playing and set the class
        for (let note of currentElements.notes) {
            let noteElement = document.getElementById(note);
            if (noteElement) noteElement.classList.add("playing");
        }
        this.setState(() => ({ position: position }));
    }

    uploadFile = (e) => {
        if (e.target.files[0] === undefined) return;
        this.setState(() => ({ file: e.target.files[0] }), () => {
            console.log(e.target.files[0])
            if (e.target.files[0].name.endsWith(".midi")) {
                this.showMIDIFile();
            } else if (e.target.files[0].name.endsWith(".musicxml")) {
                this.showXMLFile();
            } else {
                alert("File type not supported! Please upload a .midi or .musicxml file.");
            }
        });
    }

    showXMLFile = () => {

        let reader = new FileReader();
        reader.readAsText(this.state.file);
        reader.onload = () => {
            this.setState(() => ({ meiXML: reader.result }), () => {

                try {
                    let svg = this.state.tk.renderData(this.state.meiXML, {
                        pageHeight: 500,
                        pageWidth: 2000,
                        scale: 25,
                        adjustPageHeight: 1,
                        //border: 0,
                        font: "Leipzig",
                    });
                    document.getElementById("notation").innerHTML = svg;
                    document.getElementById("playMIDI").removeAttribute("disabled");
                    document.getElementById("playMIDI").addEventListener("click", this.playMIDIHandler);
                    document.getElementById("pauseMIDI").addEventListener("click", this.pauseMIDIHandler);

                    this.setState(() => ({ stream: window.music21.converter.parse(this.state.meiXML) }));
                } catch (e) {
                    console.log(e);
                }

            });
        };
        reader.onerror = function () {
            console.log(reader.error);
        };
    }

    showMIDIFile = () => {
        alert("MIDI files are not supported yet!");
    }

    changeEncoding = (e) => {
        this.setState(
            () => ({ encoding: Object.keys(this.encodings)[e] }),
        );
    }

    render() {
        return (
            <div className="EncodingViewer">
                <div className="PlayButtons">
                    <input type="file" onChange={this.uploadFile} accept={[".musicxml", ".midi"]} />
                    <button id="playMIDI" disabled>Play</button>
                    <button id="pauseMIDI" disabled>Pause</button>
                </div>
                <br />
                <MultiSwitch
                    texts={Object.values(this.encodings)}
                    selectedSwitch={0}
                    onToggleCallback={this.changeEncoding}
                />
                <div id="notation"></div>
                <div id="encoding">
                    {/*<div >{this.encodings[this.state.encoding]}</div>*/}
                    <div id="encodingContent">
                        {this.state.encoding === "pianoroll" && this.state.stream !== null && <PianorRoll stream={this.state.stream} continuations={false} playposition={this.state.position} />}
                        {this.state.encoding === "pianoroll_cont" && this.state.stream !== null && <PianorRoll stream={this.state.stream} continuations={true} playposition={this.state.position} />}
                        {this.state.encoding === "pitchdft" && this.state.stream !== null && <DFT stream={this.state.stream} pitch={true} playposition={this.state.position} />}
                        {this.state.encoding === "pitchclassdft" && this.state.stream !== null && <DFT stream={this.state.stream} pitch={false} playposition={this.state.position} />}
                        {this.state.encoding === "abc" && this.state.stream !== null && <ABC stream={this.state.stream} playposition={this.state.position} />}
                        {this.state.encoding === "tonnetz" && this.state.stream !== null && <Tonnetz stream={this.state.stream} playposition={this.state.position} />}
                        {this.state.encoding === "midi" && this.state.stream !== null && <MIDILike stream={this.state.stream} playposition={this.state.position} />}
                    </div>
                </div>
            </div>);
    };
};
export default EncodingViewer;