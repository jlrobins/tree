from jlr import sql

import random

def random_in_range(low: int, high: int):
	rng = high - low
	assert rng > 0

	return int(random.random() * rng) + low

def all_factories(con):
	results = sql.query(con,
		'''
		select f.id, f.name, f.min_value, f.max_value, f.numbers
			from factory f
			order by id
		'''
	)

	return results

MAX_CHILDREN=15
def create_factory(con, name:str, min_value:int, max_value:int):
	numbers = [ random_in_range(min_value, max_value)
						for _ in range(0, random_in_range(1, MAX_CHILDREN)) ]
	factory_id = sql.query_single_value(con, '''
		insert into factory (name, min_value, max_value, numbers)
		values (%s, %s, %s, %s)
		returning id
	''', (name, min_value, max_value, numbers))

	return {
		'id': factory_id,
		'name': name,
		'min_value': min_value,
		'max_value': max_value,
		'numbers': numbers
	}

def delete_factory(con, f_id:int):
	sql.execute(con, 'delete from factory where id = %s', (f_id,))
