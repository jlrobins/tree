import psycopg2, psycopg2.extras

def connection(conn_string):
	con = psycopg2.connect(conn_string, cursor_factory=psycopg2.extras.NamedTupleCursor)
	con.autocommit=False
	con.isolation_level = 'SERIALIZABLE'

	return con

def query_single_column(con, stmt, params=None):
	cur = con.cursor()
	cur.execute(stmt, params)

	colvalues = [ r[0] for r in cur.fetchall() ]

	cur.close()

	return colvalues


def query_single_value(con, stmt, params=None):
	cur = con.cursor()
	cur.execute(stmt, params)

	assert cur.rowcount < 2
	if cur.rowcount == 1: # allow either 0 or 1 rows.
		r = cur.fetchone()[0]
	else:
		r = None

	cur.close()

	return r

def query_single_row(con, stmt, params=None):
	cur = con.cursor()
	cur.execute(stmt, params)

	assert cur.rowcount < 2 # allow either 0 or 1 rows.
	r = cur.fetchone()

	cur.close()

	return r

def query(con, stmt, params=None):
	cur = con.cursor()
	cur.execute(stmt, params)

	rows = cur.fetchall()

	cur.close()

	return rows

def query_json_strings(con, stmt, params=None):
	results = query_single_column(con, stmt, params=params)
	if results:
		assert type(results[0]) is str

		# assemble into a big string smelling like a json array.
		buf = ['[']
		buf.extend(',\n '.join(results))
		buf.append(']')

		return ''.join(buf)
	else:
		return '[]' # smell like empty json array.

query_single = query_single_row

def execute(con, stmt, params=None):
	cur = con.cursor()
	cur.execute(stmt, params)
	retval = cur.rowcount
	cur.close()
	return retval


def insert_builder(con, tableName, rowDict, excludeKeys=None,
                   return_columns=None):
	cursor = con.cursor()
	nameList = sorted(rowDict.keys())
	colClause = []
	valueClause = []

	ccw = colClause.append
	vcw = valueClause.append

	if excludeKeys==None:
		excludeKeys=()

	for colName in nameList:
		if colName not in excludeKeys:
			val = rowDict[colName]
			# Don't need to add insert null records
			if val is not None:
				ccw(colName)

				if not isinstance(val, LiteralValue):
					vcw('%%(%s)s' % colName)
				else:
					# Want to embed literal expression, like 'now()' or so forth.
					vcw(val)


	# Remove trailing ','
	colClause = ', '.join(colClause)
	valueClause = ', '.join(valueClause)

	if colClause:
		query = 'insert into %s (%s) values (%s)' % (tableName, colClause, valueClause)
	else:
		query = 'insert into %s default values' % (tableName,)

	if return_columns:
		if not isinstance(return_columns, str):
			return_columns = ", ". join(return_columns)
		query += ' returning ' + return_columns

	# Doit!
	try:
		#logging.info("query=%r rowDict=%r"%(query, rowDict))
		cursor.execute(query, rowDict)
		if return_columns:
			return cursor.fetchone()
		return cursor.rowcount
	except psycopg2.ProgrammingError as e:
		e.query = cursor.query
		raise

def get_pct_s_string(values):
	pcts = ['%s'] * len(values)
	return ', '.join(pcts)

def bulk_insert_builder2(con, tableName, rowDictList, colList=None, excludeKeys=None, addToEveryRow=None, return_column=None):
	"""
		Bulk-insert the rows in rowDictList using "insert into ... values (), (), ... ()" .
		Please please please use this instead of embedding insert_builder inside of loops
		for inserting rows into the same table.

		Returns either the count of inserted rows [ default ], or, if return_column specifies the name of a column to return [ 'id' ],
		then will be a list of that column value, parallel to the rows in rowDictList.
	"""

	if not rowDictList:
		# Nothing to insert!
		return

	if colList is not None:
		colList = sorted(colList)	# new list -- don't rearrange passed-in one under callers nose
	else:
		colList = sorted(rowDictList[0].keys())

	if excludeKeys is not None:
		colList = [k for k in colList if k not in excludeKeys]

	tableColList = colList

	if addToEveryRow:
		extraKeys = addToEveryRow.keys()
		every_row_values = addToEveryRow.values()
		extra_row_pct_s_s = get_pct_s_string(every_row_values)


		# Build new tableColList with these extra columns appended...
		# clone it -- don't append to colList, cause colList is used to probe into regular row maps.
		tableColList = list(tableColList)
		for k in extraKeys:
			tableColList.append(k)

	row_pct_s = get_pct_s_string(colList)
	if addToEveryRow:
		row_pct_s += ', %s' % extra_row_pct_s_s
	row_pct_s.replace(' ', '') # In vast bulk uploads, these spaces might weight a lot [ 42 * 10K rows = 410,000 bytes in spaces ]

	row_pct_s = '(%s)' % row_pct_s

	if return_column:
		return_results = []

	rc = 0
	cursor = con.cursor()
	# Only send at most 1000 rows of data over the wire. (Used to)
	for chunk in [rowDictList,]:
		statement_buf = ['insert into %s (%s) values ' % (tableName, ', '.join(tableColList)) ]
		statement_data = []
		value_rows_buf = []
		didOne = len(chunk) > 0

		for row in chunk:
			value_rows_buf.append(row_pct_s)
			statement_data.extend(row.get(k, None) for k in colList)

			if addToEveryRow:
				statement_data.extend(every_row_values)

		# Was at least one row, so do it.
		if didOne:
			values_clause = ',\n'.join(value_rows_buf)
			statement_buf.append(values_clause)

			if return_column:
				statement_buf.append('returning %s' % return_column)

			statement = '\n'.join(statement_buf)

			cursor.execute(statement, statement_data)
			rc += cursor.rowcount

			if return_column:
				return_results.extend(res[0] for res in cursor.fetchall())

	if return_column:
		return return_results
	else:
		# Just the rowcount
		return rc



class LiteralValue(str):
	def getquoted(self):
		return self

	def __conform__(self, proto):
		if proto == psycopg2.extensions.ISQLQuote:
			return self
