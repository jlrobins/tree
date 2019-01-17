import psycopg2, psycopg2.extras, psycopg2.extensions
import time, threading
from functools import wraps

from flask import g

class ManagedConnection():
	def __init__(self, params, cursor_factory, timeout_secs=30):
		self.params = params
		self.cursor_factory = cursor_factory
		self.timeout_secs = timeout_secs
		self.con = None
		self.busy = False
		self.last_used = None
		self.commit_after_complete = True


	def start_closing_thread(self):
		def close_when_idle():
			while True:
				time.sleep(self.timeout_secs)
				if not self.busy and self.con and time.time() > self.last_used + self.timeout_secs:
					self.close()

		threading.Thread(target=close_when_idle).start()

	def close(self):
		if self.con:
			self.con.close()
			self.con = None

		self.busy = False


	def begin_transaction(self):
		if not self.con:
			self.con = self.__connection()

		if self.busy:
			# Wacky!
			self.con.rollback()

		self.busy = True
		self.last_used = time.time()

		return self.con


	def set_rollback_only(self):
		self.commit_after_complete = False

	def complete_transaction(self):
		if self.con:
			if self.commit_after_complete:
				self.con.commit()
			else:
				self.con.rollback()
				self.commit_after_complete = True # clear it for next request.

		self.busy = False



	def with_transaction(self, func,):
		""" Decorator to use around web dispatched functions, useful for socketio """

		@wraps(func)
		def doit(*args):
			con = self.begin_transaction()
			try:
				func(con, *args)
			except Exception as e:
				self.set_rollback_only()
				raise e
			finally:
				self.complete_transaction()

		return doit

	def __connection(self):
		return psycopg2.connect(self.params, cursor_factory=self.cursor_factory)

mc = None


def configure(params, use_dict_cursor=False, timeout_secs=30):
	global mc

	cursor_factory = psycopg2.extras.RealDictCursor if use_dict_cursor else psycopg2.extras.NamedTupleCursor
	mc = ManagedConnection(params, timeout_secs=timeout_secs, cursor_factory=cursor_factory)



def flask_connection():
	global mc

	if '_con' not in g:
		g._con = mc.begin_transaction()

	return g._con

def register_composite_types():
	con = mc.begin_transaction()

	typeconverters = [ o for o in psycopg2.__dict__.values() if type(o) is type(psycopg2.STRING) ]
	oid_to_typeconverter = {}
	for tc in typeconverters:
		for oid in tc.values:
			oid_to_typeconverter[oid] = tc

	cur = con.cursor()
	cur.execute('''
			select
				pt.type_to_register,
				pgt.typcategory,
				pgt.typarray,
				pgt.typbasetype,
				pgt_base.typname
			from psycopg_types pt
				join pg_catalog.pg_type pgt
					left join pg_catalog.pg_type pgt_base
						on (pgt.typbasetype = pgt_base.oid and pgt.typcategory='S')
			on pt.type_to_register = pgt.oid;
		''')

	for c in cur.fetchall():
		if c.typcategory == 'C':
			# Composite type
			psycopg2.extras.register_composite(c.type_to_register, con, globally=True)
		else:
			assert c.typcategory == 'S', 'Do not understand type category %s' % c.typcategory
			base_type_adaptor = oid_to_typeconverter.get(c.typbasetype)
			if not base_type_adaptor:
				raise Exception('Do not know a type adaptor for %s when trying to handle array type for domain %s'
						% (c.typname, c.type_to_register))

			psycopg2.extensions.register_type(
				psycopg2.extensions.new_array_type(
					(c.typarray,), c.type_to_register + '[]', base_type_adaptor))

	cur.close()

	mc.complete_transaction()

def configure_flask(flask_app, params, idle_timeout_secs=30):
	global mc

	configure(params, timeout_secs=idle_timeout_secs)

	flask_app.before_first_request(mc.start_closing_thread)

	flask_app.before_first_request(register_composite_types)

	def begin_and_assign_tx():
		g.con = mc.begin_transaction()

	flask_app.before_request(begin_and_assign_tx)

	def finish_transaction(response):
		g.pop('con', None)
		mc.complete_transaction()

		return response

	flask_app.teardown_request(finish_transaction)

	@flask_app.errorhandler(500)
	def error_500(error):
		mc.set_rollback_only()
		raise error


def configure_flask_socketio(params, register_types=True, use_dict_cursor=False, idle_timeout_secs=30):
	global mc

	configure(params, timeout_secs=idle_timeout_secs, use_dict_cursor=use_dict_cursor)

	mc.start_closing_thread()

	if register_types:
		register_composite_types()

	return mc
