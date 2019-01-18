\set ON_ERROR_STOP

begin;

	create table factory
	(
		id serial primary key,

		name text not null
			-- No want whitespace padded or non-empty names
			check(trim(name) = name and length(name) > 0),

		-- Min and max integer values allowed for numbers.
		-- Min is inclusive, max exclusive.

		-- An int4range is overkill for this min/max storage.
		-- (kinda exotic, only place would be testing containment
		-- would be within the numbers check constraint, no
		-- need for gist indexing / fast querying against)

		min_value int not null
			check (min_value > 0),

		max_value int not null
			check (max_value > min_value
				and max_value < 10000),

		-- Requirements for 'children' do not require any manipulation
		-- or independent querying, so an array will suffice.
		--
		-- Arrays are not exotic.
		--
		numbers int[] not null
			check (
				-- One dimensional array please
				array_ndims(numbers) = 1
				-- nonempty but at most fifteen.
				and array_length(numbers, 1) > 0
				and array_length(numbers, 1) <= 15
				-- honoring lower value inclusive constraint
				and min_value <= all(numbers)
				-- and also upper bound exclusive constraint
				and max_value > all(numbers)
				-- and no nulls within.
				and array_position(numbers, null) is null
			)

	);

	/* A bigger project would grow have some metadata table(s)
	*  describing schemas / individual tables and who should have
	*  whatever least privileges. But we've got just one table and one
	*  non-superuser role here, so ...
	*/

	-- Start by removing the permissive permissions
	-- on schema public.
	REVOKE ALL ON schema public FROM public;

	create user webspace;

	grant connect on database tree_db to webspace;
	grant usage on schema public to webspace; -- allow reading this schema
	grant select, insert, update, delete on factory to webspace; -- manip this table
	grant select, update  on factory_id_seq to webspace; -- and sequence.

	-- "alter role webspace password ..." set out-of-source-control.

commit;
