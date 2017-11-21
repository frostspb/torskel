import React, {PropTypes} from 'react';

class App extends React.Component {
    state = {
        drawerActive: false,
        drawerPinned: false,
        sidebarPinned: false
    };
    render() {

        return  (<div className='container'>
            <h1>App</h1>

                {}
            {this.props.children}
            </div>)
    }
}

export default App;
