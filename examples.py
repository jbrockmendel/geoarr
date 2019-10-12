import geopandas

from shapely.geometry import MultiPolygon, Polygon
import shapely



def get_south_africa():
	df = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres')) 
	df = df.set_index("name")
	sa = df.loc["South Africa"]
	return sa.geometry


def get_hawaii():
	# TODO: Add this file to the repo instead of hard-coding Desktop,
	#  but only after you track down attribution for where you got it from.

	fname = "gz_2010_us_040_00_5m.json"
	path = "/Users/bmendel/Desktop/" + fname

	country = geopandas.read_file(path)
	state = country.iloc[11]
	assert state.NAME == "Hawaii"

	obj = state.geometry
	return obj
