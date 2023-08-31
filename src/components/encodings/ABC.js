import React from 'react';

import tone2abc from './midi2abc';


class ABC extends React.Component {

    constructor(props) {
        super(props);

        this.state = {

            tonejsstruct: null,

            processedABC_Header: null,
            processedABC: null,

            totalDuration: null,
        };

        console.log("ABC has loaded!");

        this.state.tonejsstruct = {};

        this.state.tonejsstruct['tempos'] = this.getTempos();
        this.state.tonejsstruct['timeSignatures'] = this.getTimeSignatures();
        this.state.tonejsstruct['notes'] = this.getNotes();
        this.state.tonejsstruct['totalTime'] = this.props.stream.duration.quarterLength;

        let totalABCString = tone2abc(this.state.tonejsstruct);
        this.state.processedABC_Header = totalABCString.split('\n').slice(0, 7).join('\n');
        this.state.processedABC = totalABCString.split('\n').slice(7).join('\n');
    };

    getNotes() {
        let notes = this.props.stream.flat.notes.srcStreamElements.filter(function (item) {
            return item.isClassOrSubclass('Note');
        });

        if (notes.length === 0) {
            return [];
        } else {
            let processNotes = notes.map(function (item) {
                return {
                    "endTime": item.offset + item.duration.quarterLength,
                    "pitch": item.pitch.midi,
                    "startTime": item.offset,
                    "velocity": 100,
                    "tie": item.tie,
                    "instrument": 0,
                    "isDrum": false,
                    "program": 0,
                };
            });
            return processNotes;
        }
    }

    getTempos() {
        let tempos = this.props.stream.flat.notes.srcStreamElements.filter(function (item) {
            return item.isClassOrSubclass('MetronomeMark');
        });

        if (tempos.length === 0) {
            tempos = [{
                "qpm": 120,
                "time": 0
            }];
        } else {
            tempos = tempos.map(function (item) {
                return {
                    "qpm": item.number,
                    "time": item.offset
                };
            });
        }
        return tempos;
    }

    getTimeSignatures() {
        let timeSignatures = this.props.stream.flat.notes.srcStreamElements.filter(function (item) {
            return item.isClassOrSubclass('TimeSignature');
        });

        if (timeSignatures.length === 0) {
            timeSignatures = [{
                "time": 0,
                "numerator": 4,
                "denominator": 4,
            }];
        } else {
            timeSignatures = timeSignatures.map(function (item) {
                return {
                    "ticks": item.offset,
                    "numerator": item.numerator,
                    "denominator": item.denominator,
                };
            });
        }
        return timeSignatures;
    }

    componentDidUpdate() {

    }

    componentDidMount() {
        this.showABC();
    }

    showABC() {
        let headerDIV = document.createElement("div");
        headerDIV.id = "abcHeader";

        let abcDIV = document.createElement("div");
        abcDIV.id = "abcString";

        headerDIV.innerText = this.state.processedABC_Header;
        abcDIV.innerText = this.state.processedABC;

        if (document.getElementById("abcString")) {
            document.getElementById("abcEncoding").replaceChild(headerDIV, document.getElementById("abcHeader"));
            document.getElementById("abcEncoding").replaceChild(abcDIV, document.getElementById("abcString"));
        } else {
            document.getElementById("abcEncoding").appendChild(headerDIV);
            document.getElementById("abcEncoding").appendChild(abcDIV);
        }
    }

    render() {
        return (
            <div id="abcEncoding" className="ABC" />
        );
    }
}
export default ABC;