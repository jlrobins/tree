import React, { PureComponent } from 'react';

import {EditFactoryElem, FactoriesElem} from './Components'

import './App.css';

import io from 'socket.io-client';

class App extends PureComponent {

  constructor(props) {
    super(props);

    this.state = {
      // Do I have a thought-to-be-happy websocket connection?
      connected: false,

      // Show create factory formlet?
      creating_factory: false,

      // websocket-level connection issue?
      connection_error: null,

      // factoryy create/edit error message?
      serverside_error: null,

      // List of current factories.
      // Each factory as in:
      //    {name: 'Foo', min_value: 12, max_value: 44,
      //            count_numbers: 3, numbers: [24, 33, 17]}

      factories: []
    }

    this.setupWebSocket();

  }

  /*
    Create websocket connection back to home base
    and wire up socket message event handlers.

    These events will come in response to our
    own actions or through actions of others.
  */
  setupWebSocket() {
    const socket = io.connect({transports: ['websocket']});
    this.socket = socket;

    /*
      Websocket lifecycle handlers first ...
    */

    socket.on('connect', () => {
      this.setState({connected: true});
    });

    socket.on('reconnect_attempt', () => {
      // Perhaps directly connecting via websocket failed.
      // Fallback to trying polling first.
      socket.io.opts.transports = ['polling', 'websocket'];
      this.setState({connected: false})
    });

    socket.on('connect_error', (er) => {
      this.setState({connected: false, connection_error: er})
    });

    socket.on('error', (er) => {
      this.setState({connection_error: er})
    });

    /*
    socket.on('ping', () => {
      console.log('pinging ... ');
    });

    socket.on('pong', (latency) => {
      console.log('pong latency: ' + latency);
    });
    */

    socket.on('disconnect', () => {
        this.setState({connected: false});
    });

    /*
      Business-use messages here down
    */
    socket.on('serverside-error', (er) => {
      // Something unhappy on the websocket server side.
      // (possibly server-side unhappy with a value we submitted)
      this.setState({serverside_error: er.message})
    });

    socket.on('factories', (data) => {
      // Announcement of initial factory list
      // (sent in response to connecting)
      this.setState({factories: data.factories})
    });

    socket.on('new_factory', (data) => {
      // Someone, possibly me, created a factory.
      const factories = [...this.state.factories];
      factories.push(data.factory);
      this.setState({factories: factories});
    })

    socket.on('factory_deleted', (data) => {
      // Someone, possibly me, deleted a factory.
      const dead_id = data.id;
      const remaining_factories = this.state.factories.filter(f => f.id !== dead_id);
      this.setState({factories: remaining_factories});
    })

    socket.on('factory_updated', (data) => {
      // Someone, possibly me, updated a factory.
      const factories = [...this.state.factories]; // shallow copy
      const updated_factory = data.factory;
      const idx = factories.findIndex(f => f.id === updated_factory.id);
      if (idx !== -1)
      {
        // found it in our list: wholesale replace it.
        factories[idx] = updated_factory;
      }
      this.setState({factories: factories});
    })
  }

  /* UI executed methods: deleteFactory(), saveNewFactory(), saveEditedFactory()
      message the socket and possible adjust state immediately.
  */
  deleteFactory(f_id)
  {
    this.socket.emit('delete_factory', {id: f_id});
    // server will reply back with a 'factory_deleted' event, see above.
  }

  saveNewFactory(f)
  {
    this.socket.emit('create_factory', f);
    this.setState({creating_factory: false});
    // server will reply back with a 'new_factory' event, see above.
  }

  saveEditedFactory(f)
  {
    this.socket.emit('edit_factory', f);
    // server will reply back with a 'factory_updated' event, see above.
  }

  /*
    Draw the app.
  */
  render() {

    let con_error_msg = null;
    if (this.state.connection_error)
      con_error_msg = '' + this.state.connection_error;

    if (! this.state.connected)
    {
      // Short circuit if not connected yet.
      return <h1>Connecting {con_error_msg}...</h1>;
    }


    // Either create factory form or a button to open said form ...
    let create_button = null, creation_form = null ;
    if(this.state.creating_factory)
    {
      const blank_factory = {name: '', min_value: 1, max_value: 1000, number_count: 15};
      creation_form = (<h3><EditFactoryElem
                        factory={blank_factory}
                        doCancel={() => this.setState({creating_factory: false})}
                        doSave={(f) => this.saveNewFactory(f)}
                        saveLabel="Create"
                      /></h3>);
    } else {
      // show button instead.
      create_button =
        <button onClick={() => this.setState({creating_factory: true})}>Add</button>;
    }

    // Display any server-side complaint about prior form values next ...
    let serverside_error_elem = null;
    if(this.state.serverside_error)
    {
      serverside_error_elem = (
        <h2 className="Error">
          {this.state.serverside_error}
          <button onClick={() => this.setState({serverside_error: null})}>(clear)</button>
        </h2>);
    }

    // Overall structure, ending with the list of current factories
    // (which itself offers individual-factory-edit capability but needs
    // to call back into us to notify the central server)
    return (
      <div className="App">
        <h1>Root {create_button}</h1>
        {serverside_error_elem}
        {creation_form}
        <FactoriesElem factories={this.state.factories}
            deletor={(id) => this.deleteFactory(id)}
            editor={(f) => this.saveEditedFactory(f)}/>
      </div>
    );
  }
}


export default App;
