import React from 'react';
import './MultiSwitch.css';

class MultiSwitch extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            active: 0,
        };
        console.log(props);
    }

    handleClick(index) {
        this.setState({
            active: index,
        });
    }

    render() {
        return (
            <div className="switch">
                {
                    this.props.options.map((child, index) =>
                        <button key={index.toString()}>
                            {child}
                        </button>
                    )
                }
            </div>
        );
    }
}

export default MultiSwitch;

// {React.Children.map(children, (child, index) => {
//     return React.cloneElement(child, {
//         active: index === active,
//         onClick: () => this.handleClick(index),
//     });
// })}