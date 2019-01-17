begin;

	create table factory
	(
		id serial primary key,

		name text not null unique
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


	insert into factory (name, min_value, max_value, numbers)
		values ('London', 1, 100, '{1,99,3,4,4}');

	insert into factory (name, min_value, max_value, numbers)
		values ('Eagle', 1, 1000, '{94, 546, 345, 756, 992, 45, 1, 765}');


	select to_json(f.*)::text
		from factory f
		order by id;


commit;
