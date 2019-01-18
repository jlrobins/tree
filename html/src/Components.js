import React, { PureComponent } from 'react';

import NumericInput from 'react-numeric-input';

import { Range } from 'rc-slider';
import 'rc-slider/assets/index.css';

class EditFactoryElem extends PureComponent
{
  constructor(props)
  {
    super(props);

    this.saver = props.saver;

    // Shallow clone the factory for modification purposes (PureComponent).
    this.state = {...props.factory}
    this.state.changed = false;
    this.state.happy = EditFactoryElem.isHappy(this.state);

    // fwd reference to widget so we can set focus in componentDidMount()
    this._name_input = React.createRef();;
  }

  static isHappy(state)
  {
    // Only allow saves if name, min, max values are sane.
    return (state.name.length > 0 && state.name.length < 256
      && state.number_count > 0 && state.number_count <= 15
      && state.min_value > 0 && state.min_value < state.max_value
      && state.max_value <= 1000)
  }

  componentDidUpdate(prevProps, prevState)
  {
    // Auto-deduce our save button happiness
    const newHappy = EditFactoryElem.isHappy(this.state);

    if(prevState.happy !== newHappy)
      this.setState({happy: newHappy});
  }

  componentDidMount()
  {
    this._name_input.current.focus();
  }

  setName(value)
  {
    this.setState({name: value, changed: true});
  }

  setMinValue(value)
  {
    this.setState({min_value: value, changed: true})
  }

  setMaxValue(value)
  {
    this.setState({max_value: value, changed: true})
  }

  setNumberCount(value)
  {
    this.setState({number_count: value, changed: true})
  }

  render() {
    const f = this.state;

    let deleteElement = null;

    if(this.props.doDelete)
    {
      deleteElement = <button onClick={() => this.props.doDelete()}>Delete</button>
    }

    const save_disabled = !f.happy || !f.changed;

    return (
      <div className="EditFactory">
        <ul>
          <li>Name: <input type="text" value={f.name}
                  onChange={(ev) => this.setName(ev.target.value)}
                  ref={this._name_input}/></li>

          <li>Number Count: <NumericInput value={f.number_count} min={1} max={15} onChange={(val) => this.setNumberCount(val)}/></li>

          <li>Minimum Value: <NumericInput value={f.min_value} min={1} max={1000} onChange={(val) => this.setMinValue(val)}/></li>
          <li>Maximum Value: <NumericInput value={f.max_value} min={1} max={1000} onChange={(val) => this.setMaxValue(val)}/></li>

          <li>
              <button onClick={() => this.props.doSave(f)} disabled={save_disabled}>{this.props.saveLabel}</button>
              {deleteElement}
              <button onClick={() => this.props.doCancel()}>Cancel</button>
          </li>
        </ul>
      </div>
    )
  }
}


class FactoryElem extends PureComponent
{

  constructor(props)
  {
    super(props);

    this.state = {
      editing: false
    }
  }

  doEdit(f)
  {

    // upcall to main app to do the saving.
    this.props.editor(f);

    // no longer editing.
    this.setState({editing: false});
  }

  render()
  {

    const f = this.props.factory;
    const deletor = this.props.deletor;

    // Notes:
    //  https://reactjs.org/docs/lists-and-keys.html
    //  index key is ok if no resorting happening.

    const numbersElement = f.numbers.map((n, idx) => <li key={idx}>{n}</li> );
    let editElement;

    if(this.state.editing)
    {
      editElement = <EditFactoryElem
                        factory={f}
                        doDelete={() => deletor(f.id)}
                        doCancel={() => this.setState({editing: false})}
                        doSave={(f) => this.doEdit(f)}
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
      <li key={f.id}><FactoryElem factory={f} deletor={props.deletor} editor={props.editor} /></li>
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

export {EditFactoryElem, FactoryElem, FactoriesElem};
