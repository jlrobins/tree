import React, { Component, PureComponent } from 'react';

import NumericInput from 'react-numeric-input';


import './App.css';

import io from 'socket.io-client';





class EditFactoryElem extends PureComponent
{
  constructor(props)
  {
    super(props);

    this.saver = props.saver;

    // Shallow clone the factory for modification purposes.
    this.state = {...props.factory}
    this.state.happy = EditFactoryElem.isHappy(this.state);;
  }

  static isHappy(state)
  {
    return (state.name.length > 0 && state.name.length < 256
      && state.min_value > 0 && state.min_value < state.max_value
      && state.max_value <= 1000)
  }

  componentDidUpdate(prevProps, prevState)
  {

    const newHappy = EditFactoryElem.isHappy(this.state);

    if(prevState.happy !== newHappy)
      this.setState({happy: newHappy});

  }

  setName(value)
  {
    this.setState({name: value});
  }

  setMinValue(value)
  {
    this.setState({min_value: value})
  }

  setMaxValue(value)
  {
    this.setState({max_value: value})
  }

  doSave()
  {
    // upcall to the saver function we're created with
    // to inform superior context of new values

    this.saver(this.state);

  }

  render() {
    const f = this.state;

    let deleteElement = null;

    if(this.props.doDelete)
    {
      deleteElement = <button onClick={() => this.props.doDelete()}>Delete</button>
    }

    const save_disabled = !f.happy;

    if(this.state.happy)
    {

    }
    return (
      <div className="EditFactory">
        <ul>
          <li>Name: <input type="text" value={f.name} onChange={(ev) => this.setName(ev.target.value)}/></li>
          <li>Minimum Value: <NumericInput value={f.min_value} min={1} max={1000} onChange={(val) => this.setMinValue(val)}/></li>
          <li>Maximum Value: <NumericInput value={f.max_value} min={1} max={1000} onChange={(val) => this.setMaxValue(val)}/></li>
          <li>
              <button onClick={() => this.doSave()} disabled={save_disabled}>{this.props.saveLabel}</button>
              {deleteElement}
              <button onClick={() => this.props.doCancel()}>Cancel</button>
          </li>
        </ul>
      </div>
    )
  }
}


/*
<EditFactoryElem
                        factory={blank_factory}
                        doCancel={() => this.setState({creating_factory: false})}
                        saver={(f) => this.saveNewFactory(f)} />
                        */
class FactoryElem extends PureComponent
{

  constructor(props)
  {
    super(props);

    this.state = {
      editing: false
    }
  }
  render()
  {

    const f = this.props.factory;
    const deletor = this.props.deletor;

    // push support into EditFactoryElem if f has a ...
    // <button onClick={() => deletor(f.id)}>Delete</button>
    /*
    Notes
    // https://reactjs.org/docs/lists-and-keys.html
    // index key is ok if no resorting happening.
    */
    const numbersElement = f.numbers.map((n, idx) => <li key={idx}>{n}</li> );
    let editElement;

    if(this.state.editing)
    {
      editElement = <EditFactoryElem
                        factory={f}
                        doDelete={() => deletor(f.id)}
                        doCancel={() => this.setState({editing: false})}
                        saver={(f) => console.log('implement edit save!')}
                        saveLabel="Update"/>
    } else {
      editElement = <button onClick={() => this.setState({editing: true})}>Edit</button>
    }
    return (
      <span>
        {f.name} ({f.min_value} -> {f.max_value})
        {editElement}
        <ul className="factory-list">
          {numbersElement}
        </ul>
      </span>
    );
  }

}

const FactoriesElem = (props) => {

  if(props.factories.length)
  {
    const f_list = props.factories.map(f =>
      <li key={f.id}><FactoryElem factory={f} deletor={props.deletor}/></li>
    );

    return (
      <ul className="factory-list">
        {f_list}
      </ul>
    );
  } else {
    return null;
  }
}


class App extends PureComponent {

  constructor(props) {
    super(props);

    this.state = {
      connected: false,
      creating_factory: false,
      factories: [] // of Factory
    }

    this.setupWebSocket();

  }

  setupWebSocket() {
    const socket = io.connect();

    this.socket = socket;

    socket.on('connect', (resp) => {
        this.setState({connected: true});
    });

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

    socket.on('disconnect', () => {
        this.setState({connected: false});
    });
  }

  deleteFactory(f_id)
  {
    this.socket.emit('delete_factory', {id: f_id});
  }

  saveNewFactory(f)
  {


    this.socket.emit('create_factory', f);

    this.setState({creating_factory: false});
  }


  render() {

    if (! this.state.connected)
    {
      return <h1>Connecting ...</h1>
    }


    let creation_elem;
    if(this.state.creating_factory)
    {
      const blank_factory = {name: '', min_value: 1, max_value: 1000};
      creation_elem = (<EditFactoryElem
                        factory={blank_factory}
                        doCancel={() => this.setState({creating_factory: false})}
                        saver={(f) => this.saveNewFactory(f)}
                        saveLabel="Create"
                      />);
    } else {
      // show button instead.
      creation_elem =
        <button onClick={() => this.setState({creating_factory: true})}>Create Factory</button>;
    }
    return (
      <div className="App">
        <h1>Factory Channel!</h1>
        <h3>{creation_elem}</h3>
        <FactoriesElem factories={this.state.factories} deletor={(id) => this.deleteFactory(id)}/>
      </div>
    );
  }
}

export default App;
