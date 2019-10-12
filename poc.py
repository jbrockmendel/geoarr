import re

import numpy as np
import shapely


def nested_floats_to_shapely(nested):
	raise NotImplementedError


def shapely_to_nested_floats(obj):
	"""
	Extract the underlying nested float64 data from a shapely object.

	Notes
	-----
	This is hacked together.  Someone who understands shapely can likely
	put together something more robust.
	"""
	try:
		obj.ctypes
	except NotImplementedError:
		# hasattr check returns True but access raises
		out = np.asarray(obj)
		for i, sub in enumerate(out):
			out[i] = shapely_to_nested_floats(sub)

	else:
		out = np.asarray(obj.ctypes)
		assert out.dtype == "f8", out.dtype

	return out


def flatten_floats(nested):
	"""
	Convert a nested sequence of floats to a flat sequence.

	nested is as produced by `shapely_to_nested_floats`.  flat output
	is in the format expected by `unpack_item`.
	"""
	# TODO: Could avoid lots of copies by pre-allocating.

	if nested.dtype == "f8":
		return nested

	if not len(nested):
		return np.array([], dtype=np.float64)

	flats = [flatten_floats(x) for x in nested]
	flats2 = [np.r_[np.inf, x, -np.inf] for x in flats]
	out = np.r_[tuple(flats2)]
	assert out.dtype == np.float64, out.dtype
	return out

	flat = nested[0]
	for entry in nested:
		flat = np.r_[flat, flatten_floats(entry)]

	return flat


def unpack_item(item):
	"""
	Unpack a float64 array into a nested coordinate object similar to shapely.

	Parameters
	----------
	item : ndarray[float64]

	Notes
	-----
	*very* not-optimized
	"""
	assert isinstance(item, np.ndarray) and item.dtype == np.float64

	# np.nan represents separation between items, so should not be present
	#  within an item.
	assert not np.isnan(item).any()

	# We should be working with coordinate pairs.
	assert len(item) % 2 == 0

	# For the proof of concept, we are going to let python do the parsing
	#  for us.  This is very non-performant.
	sitem = item.astype(str)

	# +np.inf and -np.inf represent increment and decrement to the degree of
	#  nesting, respectively.  In python we represent this as a nested tuple.
	sitem[np.isposinf(item)] = "("
	sitem[np.isneginf(item)] = ")"

	raw = ",".join(sitem)
	lrep = raw.replace("(,", "(").replace("(", ",(").lstrip(",")
	rep = lrep.replace(")", "),").rstrip(",")
	rep = re.sub(',+', ',', rep)  # FIXME: kludge

	nested = eval(rep)
	return cast_nested(nested)


def cast_nested(nested):
	"""
	Cast nested tuples containing floats to nested ndarrays.
	"""
	try:
		res = np.asarray(nested, dtype=np.float64)
	except ValueError:
		# nested, cant do it
		pass
	else:
		if res.ndim == 1:
			# Otherwise we might have a rectangular  array by mistake,
			#  though in that case we could use res instead of tossing it here
			return res

	out = np.empty(len(nested), dtype=object)
	for i, sub in enumerate(nested):
		out[i] = cast_nested(sub)
		# TODO: will this be right with exclusions?

	return out


flat_to_nested = unpack_item  # alias


def pack_item(item):
	"""
	Convert a shapely object into an ndarray[float64].

	Parameters
	----------
	item: shapely.??

	Returns
	-------
	ndarray[float64]
	"""
	raise NotImplementedError


class ShapelyArray:
	def __init__(self, data):
		assert isinstance(data, np.ndarray) and data.dtype == np.float64
		self._data = data

		# To support higher dimensions, we will need a more sophisticated
		#  implementation of _breaks
		assert data.ndim == 1
		breaks = np.isnan(data).nonzero()[0]
		breaks = np.r_[0, breaks]
		self._breaks = breaks

	def __getitem__(self, key):
		if not isinstance(key, int):
			raise NotImplementedError(type(key))
		if key < 0:
			raise NotImplementedError(key)

		start = self._breaks[key]
		stop = self._breaks[key+1]
		flat = self._data[start:stop]
		nested = unpack_item(flat)
		return nested_floats_to_shapely(item)


def roundtrip_check(obj):
	# shapely obj
	nested = shapely_to_nested_floats(obj)
	flat = flatten_floats(nested)
	unpacked = unpack_item(flat)

	assert_nested_equal(nested, unpacked)


def assert_nested_equal(left, right):
	assert left.shape == right.shape
	assert left.dtype == right.dtype

	if left.dtype == object:
		for i in range(len(left)):
			left2 = left[i]
			right2 = right[i]

			# in out case of nested floats, these should both be ndarrays
			assert_nested_equal(left2, right2)

	else:
		np.testing.assert_equal(left, right)
