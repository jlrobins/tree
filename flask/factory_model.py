import random

from jlr import sql


def all_factories(con):
    ###
    # Fetch and return all factories as namedtuples. Also
    # project the inferred number_count property
    ###
    return sql.query(con, '''
                     select id, name, min_value, max_value,
                            array_length(numbers, 1) as number_count,
                            f.numbers
                        from factory f
                        order by id
                     ''')


def create_factory(con, name: str, min_value: int,
                   max_value: int, number_count: int):

    ###
    # Create and return a factory given the params.
    # caller will have already inspected params and given polite
    # error message, otherwise database will.
    ###
    numbers = generate_numbers(min_value, max_value, number_count)

    rowDict = {'name': name, 'min_value': min_value,
               'max_value': max_value, 'numbers': numbers}

    factory_id = sql.insert(con, 'factory', rowDict, return_columns=('id',))[0]

    rowDict['id'] = factory_id
    # We infer but project. See also all_factories() ...
    rowDict['number_count'] = len(numbers)

    return rowDict


def update_factory(con, factory_id: int, new_name: str,
                   new_min_value: int, new_max_value: int,
                   new_number_count: int):

    ###
    # Update factory named by this id with these values.
    # We will preserve the factory's numbers array if we're only
    # changing the factory name here. Otherwise regenerate.
    #
    # Here we have implemented server-side random children generation
    # so as to give *somthing* of business-logic interest to this
    # python server-side middleware instead of just being a boring
    # websocket <-> database conduit.
    #
    # Returns the updated factory as a dict.
    ###

    #
    # Yes, using a ORM would now be useful. All fun and games until
    # update time if wanting to do selective column updating.
    # Even given sql.update().
    #

    # Hatey any leading or trailing whitespace.
    new_name = new_name.strip()

    # holds pairs of column names and new values
    update_columns_values = []
    return_values = {'id': factory_id, 'min_value': new_min_value,
                     'max_value': new_max_value, 'name': new_name,
                     'number_count': new_number_count}

    old_factory = sql.query_single_row(con, '''
            select name, min_value, max_value,
                numbers from factory where id = %s''', (factory_id,))

    if not old_factory:
        raise Exception('Could not find factory with id %s' % factory_id)

    old_min_max_count = (old_factory.min_value, old_factory.max_value,
                         len(old_factory.numbers))

    if old_min_max_count != (new_min_value, new_max_value, new_number_count):
        # Regenerate number array since requirements have changed.
        numbers = generate_numbers(new_min_value,
                                   new_max_value, new_number_count)
        update_columns_values.append(('numbers', numbers))
        update_columns_values.append(('min_value', new_min_value))
        update_columns_values.append(('max_value', new_max_value))
        return_values['numbers'] = numbers
    else:
        # no need to regenerate numbers: low, high, count are the same.
        return_values['numbers'] = old_factory.numbers

    if old_factory.name != new_name:
        update_columns_values.append(('name', new_name))

    if not update_columns_values:
        raise Exception('Nothing to change!')

    update_count = sql.update(con,
                              'factory',  # table name
                              [('id = %s', factory_id)],  # where clause parts
                              # pairs of column to new values
                              update_columns_values
                              )

    if not update_count:
        raise Exception('Update did not find row to update.'
                        ' Deleted out from underneath?')

    return
    return_values


def delete_factory(con, f_id: int):
    sql.execute(con, 'delete from factory where id = %s', (f_id,))

###
# Module internals
###


def generate_numbers(min_value, max_value, number_count):
    return [random_in_range(min_value, max_value)
            for _ in range(0, number_count)]


def random_in_range(low: int, high: int):
    random_span = high - low
    assert random_span > 0

    return int(random.random() * random_span) + low
