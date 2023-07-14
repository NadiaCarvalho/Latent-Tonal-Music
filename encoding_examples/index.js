let tk;
let meiXML = '';
let encoding = 'pianoroll';

document.addEventListener("DOMContentLoaded", (event) => {
    verovio.module.onRuntimeInitialized = async _ => {
        tk = new verovio.toolkit();
        console.log("Verovio has loaded!");
    };
});

// The current page, which will change when playing through the piece
let currentPage = 1;

/**
 The handler to start/stop playing the file
**/
const playMIDIHandler = function () {
    // Get the MIDI file from the Verovio toolkit
    let base64midi = tk.renderToMIDI();
    // Add the data URL prefixes describing the content
    let midiString = 'data:audio/midi;base64,' + base64midi;
    // Pass it to play to MIDIjs
    MIDIjs.play(midiString);

    document.getElementById("pauseMIDI").removeAttribute("disabled");

    document.getElementById("playMIDI").innerText = "Stop";
    document.getElementById("playMIDI").addEventListener("click", stopMIDIHandler);
    document.getElementById("playMIDI").removeEventListener("click", playMIDIHandler);
}
const stopMIDIHandler = function () {
    MIDIjs.stop();

    let playingNotes = document.querySelectorAll('g.note.playing');
    for (let playingNote of playingNotes) playingNote.classList.remove("playing");

    currentPage = 1;
    document.getElementById("notation").innerHTML = tk.renderToSVG(currentPage);

    document.getElementById("playMIDI").innerText = "Play";
    document.getElementById("playMIDI").addEventListener("click", playMIDIHandler);
    document.getElementById("playMIDI").removeEventListener("click", stopMIDIHandler);

    document.getElementById("pauseMIDI").setAttribute("disabled", true);
}

/**
 The handlers to pause/continue playing the file
**/
const pauseMIDIHandler = function () {
    MIDIjs.pause();

    document.getElementById("pauseMIDI").innerText = "Continue";
    document.getElementById("pauseMIDI").addEventListener("click", continueMIDIHandler);
    document.getElementById("pauseMIDI").removeEventListener("click", pauseMIDIHandler);
}
const continueMIDIHandler = function () {
    MIDIjs.resume();

    document.getElementById("pauseMIDI").innerText = "Pause";
    document.getElementById("pauseMIDI").addEventListener("click", pauseMIDIHandler);
    document.getElementById("pauseMIDI").removeEventListener("click", continueMIDIHandler);
}

/**
 * The handler to highlight the notes while playing the file
 **/
const midiHightlightingHandler = function (event) {
    // Remove the attribute 'playing' of all notes previously playing
    let playingNotes = document.querySelectorAll('g.note.playing');
    for (let playingNote of playingNotes) playingNote.classList.remove("playing");

    // Get elements at a time in milliseconds (time from the player is in seconds)
    let currentElements = tk.getElementsAtTime(event.time * 1000);

    if (currentElements.page == 0) return;

    if (currentElements.page != currentPage) {
        currentPage = currentElements.page;
        document.getElementById("notation").innerHTML = tk.renderToSVG(currentPage);
    }

    // Get all notes playing and set the class
    for (note of currentElements.notes) {
        let noteElement = document.getElementById(note);
        if (noteElement) noteElement.classList.add("playing");
    }
}

/**
    Wire up the buttons to actually work.
*/
document.getElementById("playMIDI").addEventListener("click", playMIDIHandler);
document.getElementById("pauseMIDI").addEventListener("click", pauseMIDIHandler);
/**
 Set the function as message callback
*/
MIDIjs.player_callback = midiHightlightingHandler;

function showFile(input) {

    let file = input.files[0];
    let reader = new FileReader();
    reader.readAsText(file);
    reader.onload = function () {

        meiXML = reader.result;
        let svg = tk.renderData(meiXML, {
            pageHeight: 500,
            pageWidth: 2000,
            scale: 25,
            adjustPageHeight: 1,
            border: 0,
            font: "Leipzig",
        });
        document.getElementById("notation").innerHTML = svg;
        document.getElementById("playMIDI").removeAttribute("disabled");

        showEncoding(meiXML, encoding);
    };

    reader.onerror = function () {
        console.log(reader.error);
    };
};

function showEncoding(input, encoding) {

    switch (encoding) {
        case 'pianoroll':
            showPianoroll(input);
            break;
        default:
            break;
    }
}

function showPianoroll(input, continuations = false, resolution = 4) {
    stream = music21.converter.parse(input);
    notes = stream.flat.notes.srcStreamElements.filter(function(item) {
        return item.isClassOrSubclass('Note');
    });

    let totalDuration = Math.round(notes.at(notes.length-1).offset + notes[notes.length-1].duration.quarterLength)*resolution;

    let rows = continuations ? 256 : 128;
    let matrix = Array.from(Array(totalDuration), _ => Array(rows).fill(0));

    for (let note of notes) {
        let offset = Math.round(note.offset*resolution);
        let duration = Math.round(note.duration.quarterLength*resolution);
        let pitch = note.pitch.ps;
        for (let i = offset; i < offset + duration; i++) {
            matrix[i][pitch] = 1;
        }
    }

    let matrixDiv = document.createElement("div");
    for (let i = 0; i < totalDuration; i++) {
        let rowDiv = document.createElement("div");
        rowDiv.classList.add("row");
        for (let j = 0; j < rows; j++) {
            let cellDiv = document.createElement("div");
            cellDiv.classList.add("cell");
            //cellDiv.innerText = matrix[i][j];
            if (matrix[i][j] == 1) cellDiv.classList.add("active");
            rowDiv.appendChild(cellDiv);
        }
        matrixDiv.appendChild(rowDiv);
    }

    document.getElementById("encoding").appendChild(matrixDiv);
}

function changeEncoding(encoding) {
    showEncoding(meiXML, encoding);
}

