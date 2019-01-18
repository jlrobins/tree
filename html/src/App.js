import React, { PureComponent } from 'react';

import {EditFactoryElem, FactoriesElem} from './Components'

import './App.css';

import io from 'socket.io-client';

class App extends PureComponent {

  constructor(props) {
    super(props);

    this.state = {
      connected: false,
      creating_factory: false,
      online_count: 0,
      connection_error: null,
      serverside_error: null,
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
      Websocket lifecycle handlers first
    */
    socket.on('reconnect_attempt', () => {
      socket.io.opts.transports = ['polling', 'websocket'];
      this.setState({connected: false})
    });

    socket.on('connect_error', (er) => {
      this.setState({connected: false, connection_error: er})
    });

    socket.on('error', (er) => {
      this.setState({connection_error: er})
    });

    socket.on('ping', () => {
      console.log('pinging ... ');
    });

    socket.on('pong', (latency) => {
      console.log('pong latency: ' + latency);
    });

    socket.on('connect', () => {
      this.setState({connected: true});
    });

      socket.on('disconnect', () => {
        this.setState({connected: false});
    });

    /*
      Business-use messages here down
    */
    socket.on('serverside-error', (er) => {
      this.setState({serverside_error: er.message})
    });

    socket.on('online_count', (data) => {
      this.setState({online_count: data.online_count})
    })

    socket.on('factories', (data) => {
      // Announcement of initial factory list
      this.setState({factories: data.factories})
    });

    socket.on('new_factory', (data) => {
      // broadcasted newly created factory, even if came from me
      const factories = [...this.state.factories];
      factories.push(data.factory);
      this.setState({factories: factories});
    })

    socket.on('factory_deleted', (data) => {
      // someone, including me, deleted a factory
      const dead_id = data.id;
      const remaining_factories = this.state.factories.filter(f => f.id !== dead_id);
      this.setState({factories: remaining_factories});
    })

    socket.on('factory_updated', (data) => {
      // someone, including me, updated a factory
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
      message the socket and possible adjust state immediately
  */
  deleteFactory(f_id)
  {
    this.socket.emit('delete_factory', {id: f_id});
  }

  saveNewFactory(f)
  {
    this.socket.emit('create_factory', f);
    this.setState({creating_factory: false});
  }

  saveEditedFactory(f)
  {
    this.socket.emit('edit_factory', f);
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
      return <h1>Connecting {con_error_msg}...</h1>
    }


    let creation_elem;
    if(this.state.creating_factory)
    {
      const blank_factory = {name: '', min_value: 1, max_value: 1000};
      creation_elem = (<EditFactoryElem
                        factory={blank_factory}
                        doCancel={() => this.setState({creating_factory: false})}
                        doSave={(f) => this.saveNewFactory(f)}
                        saveLabel="Create"
                      />);
    } else {
      // show button instead.
      creation_elem =
        <button onClick={() => this.setState({creating_factory: true})}>Create Factory</button>;
    }

    let serverside_error_elem = null;
    if(this.state.serverside_error)
    {
      serverside_error_elem = (
        <h2 class="Error">
          {this.state.serverside_error}
          <button onClick={() => this.setState({serverside_error: null})}>(clear)</button>
        </h2>);
    }

    return (
      <div className="App">
        <h1>Factory Channel: {this.state.online_count} Online</h1>
        {serverside_error_elem}
        <h3>{creation_elem}</h3>
        <FactoriesElem factories={this.state.factories}
            deletor={(id) => this.deleteFactory(id)}
            editor={(f) => this.saveEditedFactory(f)}/>
      </div>
    );
  }
}

export default App;
