import React from 'react';

class PianorRoll extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            notes: null,
            matrix: null,
            totalDuration: null,
            cols: null,
            continuations: this.props.continuations,
            resolution: 4,

            startRow: 0,
            viewRows: 10,
        };

        console.log("Pianoroll has loaded!");

        this.state.notes = this.props.stream.flat.notes.srcStreamElements.filter(function(item) {
            return item.isClassOrSubclass('Note');
        });

        this.state.totalDuration = Math.round(this.state.notes.at(this.state.notes.length-1).offset + this.state.notes[this.state.notes.length-1].duration.quarterLength)*this.state.resolution;

        this.state.cols = this.state.continuations ? 256 : 128;
        this.state.matrix = Array.from(Array(this.state.totalDuration), _ => Array(this.state.cols).fill(0));

        for (let note of this.state.notes) {
            let offset = Math.round(note.offset*this.state.resolution);
            let duration = Math.round(note.duration.quarterLength*this.state.resolution);
            let pitch = note.pitch.ps;

            for (let i = offset; i < offset + duration; i++) {
                if (i === offset || this.state.continuations === false) {
                    this.state.matrix[i][pitch] = 1;
                } else {
                    this.state.matrix[i][pitch+127] = 1;
                }
            }
        }
    }

    componentDidUpdate() {
        let startRow = Math.round(this.props.playposition * this.state.totalDuration);
        let stRow = startRow % this.state.resolution;
        if (stRow !== 0) {
            startRow = startRow - stRow;
        }
        if (startRow + this.state.viewRows > this.state.totalDuration) {
            startRow = this.state.totalDuration - this.state.viewRows;
        }

        if (startRow !== this.state.startRow) {
            this.setState({startRow: startRow}, () => {this.showPianoroll()});
        }
    }

    componentDidMount() {
        this.showPianoroll();
    }

    showPianoroll() {

        console.log("Showing pianoroll")

        let indexDiv = document.createElement("div");
        indexDiv.id = "index";

        let matrixDiv = document.createElement("div");
        matrixDiv.id = "matrix";

        for (let i = this.state.startRow; i < this.state.startRow + this.state.viewRows; i++) {

            let rowDiv = document.createElement("div");
            rowDiv.classList.add("row");

            for (let j = 0; j < this.state.cols; j++) {

                if (i === this.state.startRow) {
                    let indexCellDiv = document.createElement("div");
                    indexCellDiv.classList.add("indexcell");
                    indexCellDiv.id = "indexcell-" + j;
                    let textSpan = document.createElement("span")
                    textSpan.innerText = j;

                    indexCellDiv.appendChild(textSpan);
                    indexDiv.appendChild(indexCellDiv);
                }

                let cellDiv = document.createElement("div");
                cellDiv.classList.add("cell");
                cellDiv.innerText = this.state.matrix[i][j];

                if (this.state.matrix[i][j] === 1) cellDiv.classList.add("active");
                if (this.state.continuations === true && j > 127) cellDiv.classList.add("continuation");

                rowDiv.appendChild(cellDiv);
            }
            matrixDiv.appendChild(rowDiv);
        }

        if (document.getElementById("matrix")) {
            document.getElementById("pianorollEncoding").replaceChild(indexDiv, document.getElementById("index"));
            document.getElementById("pianorollEncoding").replaceChild(matrixDiv, document.getElementById("matrix"));
        } else {
            document.getElementById("pianorollEncoding").appendChild(indexDiv);
            document.getElementById("pianorollEncoding").appendChild(matrixDiv);
        }
    }

    render() {
        return (
            <div id="pianorollEncoding" className="Pianoroll">
            </div>
        );
    }
}
export default PianorRoll;