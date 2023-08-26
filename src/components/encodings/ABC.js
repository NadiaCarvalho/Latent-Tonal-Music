import React from 'react';


class ABC extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            notes: null
        };

        console.log("ABC has loaded!");
    };

    render() {
        return (
            <div id="abcEncoding" className="ABC" />
        );
    }
}
export default ABC;