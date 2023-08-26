import React from 'react';

const FFT = require('fft-js').fft;

class DFT extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            notes: null,
            matrix: null,
            totalDuration: null,
            cols: null,
            pitch: this.props.pitch,
            resolution: 4,

            startRow: 0,
            viewRows: 10,
        };

        console.log("DFT has loaded!");

        this.state.notes = this.props.stream.flat.notes.srcStreamElements.filter(function(item) {
            return item.isClassOrSubclass('Note');
        });

        this.state.totalDuration = Math.round(this.state.notes.at(this.state.notes.length-1).offset + this.state.notes[this.state.notes.length-1].duration.quarterLength)*this.state.resolution;

        let cols = this.state.pitch ? 256 : 24;
        let matrix = Array.from(Array(this.state.totalDuration), _ => Array(cols).fill(0));
        for (let note of this.state.notes) {
            let offset = Math.round(note.offset*this.state.resolution);
            let duration = Math.round(note.duration.quarterLength*this.state.resolution);
            let pitch = note.pitch.ps;
            let pitchClass = note.pitch.pitchClass;

            for (let i = offset; i < offset + duration; i++) {
                if (this.state.pitch){
                    if (i === offset) {matrix[i][pitch] = 1} else {matrix[i][pitch+127] = 1};
                } else {
                    if (i === offset) {matrix[i][pitchClass] = 1} else {matrix[i][pitchClass + 12] = 1};
                }
            }
        }

        this.state.matrix = this.dft_reduction(matrix);
        this.state.cols = this.state.matrix[0].length;
    }

    dft_reduction(data) {
        let dft_matrix = Array.from(Array(data.length), _ => Array(data[0].length * 2).fill(0));

        for (let i = 0; i < data.length; i++) {
            let half = data[i].length/2;

            let r_attack = data[i].slice(0, half);
            let r_release = data[i].slice(half, data[i].length);

            if (half === 12) {
                r_attack = r_attack.concat(new Array(4).fill(0));
                r_release = r_release.concat(new Array(4).fill(0));
            }
            let dft_array_attacks = FFT(r_attack);
            let dft_array_releases = FFT(r_release);

            for (let j = 0; j < half; j++) {
                dft_matrix[i][j * 4] = dft_array_attacks[j][0];
                dft_matrix[i][j * 4 + 1] = dft_array_attacks[j][1];
                dft_matrix[i][j * 4 + 2] = dft_array_releases[j][0];
                dft_matrix[i][j * 4 + 3] = dft_array_releases[j][1];
            }
        }
        return dft_matrix;
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
            this.setState({startRow: startRow}, () => {this.showDFT()});
        }
    }

    componentDidMount() {
        this.showDFT();
    }

    showDFT() {

        console.log("Showing DFT")

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
                    indexCellDiv.classList.add("indexcellDFT");
                    indexCellDiv.id = "indexcellDFT-" + j;
                    let textSpan = document.createElement("span")
                    textSpan.innerText = j;

                    indexCellDiv.appendChild(textSpan);
                    indexDiv.appendChild(indexCellDiv);
                }

                let cellDiv = document.createElement("div");
                cellDiv.classList.add("cellDFT");
                let textSpan = document.createElement("span");
                textSpan.innerText = this.state.matrix[i][j].toFixed(3);
                cellDiv.appendChild(textSpan);

                if (this.state.matrix[i][j] !== 0) cellDiv.classList.add("active");
                if (this.state.matrix[i][j] !== 0 && j > (this.state.matrix[i].length / 2)) cellDiv.classList.add("continuation");

                rowDiv.appendChild(cellDiv);
            }
            matrixDiv.appendChild(rowDiv);
        }

        if (document.getElementById("matrix")) {
            document.getElementById("dftEncoding").replaceChild(indexDiv, document.getElementById("index"));
            document.getElementById("dftEncoding").replaceChild(matrixDiv, document.getElementById("matrix"));
        } else {
            document.getElementById("dftEncoding").appendChild(indexDiv);
            document.getElementById("dftEncoding").appendChild(matrixDiv);
        }
    }

    render() {
        return (
            <div id="dftEncoding" className="DFTEncoding"/>
        );
    }
}
export default DFT;