import React from 'react';

const TEMPLATE_ROWS = [6, 13, 8, 15, 10, 17, 12, 7, 14, 9, 16, 11,
    10, 17, 12, 19, 14, 21, 16, 11, 18, 13, 20, 15,
    14, 21, 16, 23, 18, 25, 20, 15, 22, 17, 24, 19,
    18, 25, 20, 27, 22, 29, 24, 19, 26, 21, 28, 23,
    22, 29, 24, 31, 26, 33, 28, 23, 30, 25, 32, 27,
    26, 33, 28, 35, 30, 37, 32, 27, 34, 29, 36, 31,
    30, 37, 32, 39, 34, 41, 36, 31, 38, 33, 40, 35,
    34, 41, 36, 43, 38, 45, 40, 35, 42, 37, 44, 39,
    38, 45, 40, 47, 42, 49, 44, 39, 46, 41, 48, 43,
    42, 49, 44, 51, 46, 53, 48, 43, 50, 45, 52, 47,
    46, 53, 48, 55, 50, 57, 52, 47, 54, 49, 56, 51,
    50, 57, 52, 59, 54, 61, 56, 51, 58, 53, 60, 55,
    54, 61, 56, 63, 58, 65, 60, 55, 62, 57, 64, 59,
    58, 65, 60, 67, 62, 69, 64, 59, 66, 61, 68, 63,
    62, 69, 64, 71, 66, 73, 68, 63, 70, 65, 72, 67,
    66, 73, 68, 75, 70, 77, 72, 67, 74, 69, 76, 71,
    70, 77, 72, 79, 74, 81, 76, 71, 78, 73, 80, 75,
    74, 81, 76, 83, 78, 85, 80, 75, 82, 77, 84, 79,
    78, 85, 80, 87, 82, 89, 84, 79, 86, 81, 88, 83,
    82, 89, 84, 91, 86, 93, 88, 83, 90, 85, 92, 87,
    86, 93, 88, 95, 90, 97, 92, 87, 94, 89, 96, 91,
    90, 97, 92, 99, 94, 101, 96, 91, 98, 93, 100, 95,
    94, 101, 96, 103, 98, 105, 100, 95, 102, 97, 104, 99,
    98, 105, 100, 107, 102, 109, 104, 99, 106, 101, 108, 103];

class Tonnetz extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            notes: null,
            matrix: null,
            totalDuration: null,
            cols: null,
            resolution: 4,

            startRow: 0,
            viewRows: 10,
        };

        console.log("Tonnetz has loaded!");

        this.state.notes = this.props.stream.flat.notes.srcStreamElements.filter(function(item) {
            return item.isClassOrSubclass('Note');
        });

        this.state.totalDuration = Math.round(this.state.notes.at(this.state.notes.length-1).offset + this.state.notes[this.state.notes.length-1].duration.quarterLength)*this.state.resolution;
        this.state.cols = 2 * TEMPLATE_ROWS.length;

        this.state.matrix = Array.from(Array(this.state.totalDuration), _ => Array(this.state.cols).fill(0));
        for (let note of this.state.notes) {
            let offset = Math.round(note.offset*this.state.resolution);
            let duration = Math.round(note.duration.quarterLength*this.state.resolution);
            let pitch = note.pitch.ps;
            let template_rows_pitch = TEMPLATE_ROWS.reduce(function(a, e, i) {
                if (e === pitch)
                    a.push(i);
                return a;
            }, []);
            let template_rows_continuations = template_rows_pitch.map(x => x + TEMPLATE_ROWS.length)

            for (let i = offset; i < offset + duration; i++) {
                if (i === offset) {
                    for (let j = 0; j < template_rows_pitch.length; j++) {
                        this.state.matrix[i][template_rows_pitch[j]] = 1
                    }
                } else {
                    for (let j = 0; j < template_rows_continuations.length; j++) {
                        this.state.matrix[i][template_rows_continuations[j]] = 1
                    }
                };
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
            this.setState({startRow: startRow}, () => {this.showTonnetz()});
        }
    }

    componentDidMount() {
        this.showTonnetz();
    }

    showTonnetz() {

        console.log("Showing Tonnetz");

        let indexDiv = document.createElement("div");
        indexDiv.id = "index";

        let tonnetzIndicator = document.createElement("div");
        tonnetzIndicator.id = "tonnetzIndicator";

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


                    let tonnetzIndicatorCellDiv = document.createElement("div");
                    tonnetzIndicatorCellDiv.classList.add("tonnetzIndicatorCell");
                    tonnetzIndicatorCellDiv.id = "tonnetzIndicatorCell-" + j;
                    let textSpan2 = document.createElement("span");
                    textSpan2.innerText = TEMPLATE_ROWS[j % TEMPLATE_ROWS.length];

                    tonnetzIndicatorCellDiv.appendChild(textSpan2);
                    tonnetzIndicator.appendChild(tonnetzIndicatorCellDiv);
                }

                let cellDiv = document.createElement("div");
                cellDiv.classList.add("cell");
                cellDiv.innerText = this.state.matrix[i][j];

                if (this.state.matrix[i][j] === 1) cellDiv.classList.add("active");
                if (this.state.matrix[i][j] === 1 && j >= TEMPLATE_ROWS.length) cellDiv.classList.add("continuation");

                rowDiv.appendChild(cellDiv);
            }
            matrixDiv.appendChild(rowDiv);
        }

        if (document.getElementById("matrix")) {
            document.getElementById("tonnetzEncoding").replaceChild(indexDiv, document.getElementById("index"));
            document.getElementById("tonnetzEncoding").replaceChild(tonnetzIndicator, document.getElementById("tonnetzIndicator"));
            document.getElementById("tonnetzEncoding").replaceChild(matrixDiv, document.getElementById("matrix"));
        } else {
            document.getElementById("tonnetzEncoding").appendChild(indexDiv);
            document.getElementById("tonnetzEncoding").appendChild(tonnetzIndicator);
            document.getElementById("tonnetzEncoding").appendChild(matrixDiv);
        }

    }

    render() {
        return (
            <div id="tonnetzEncoding" className="Tonnetz" />
        );
    }
}
export default Tonnetz;