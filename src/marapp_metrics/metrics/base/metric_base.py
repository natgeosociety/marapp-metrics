import ee
import geojson
import geopandas as gpd
import math
import pandas as pd
from collections.abc import Iterable
from shapely import wkt

from ...helpers.config import Config
from ...helpers.earthengine import map_function, initialize_google_ee
from ...helpers.logging import get_logger

logger = get_logger("base-metric")


class MetricPackageException(Exception):
    pass


class MetricComputeException(Exception):
    pass


class MetricBase:
    slug = NotImplemented

    def __init__(self, **kwargs):
        """
        :param kwargs:
        :keyword grid: Bool
        :keyword simplify: Bool
        :keyword simplify_tolerance: Level to which shape is simplified
        :keyword area_threshold: Size at which polygons are broken into grids
        :keyword grid_size_degrees: Grid size in arc degrees
        :keyword chunk_size: Analyse in blocks
        :keyword config_filepath: Yaml config file
        """
        # Initialize Earth Engine, using the authentication credentials.
        initialize_google_ee()

        self.grid = kwargs.get("grid", False)
        self.simplify = kwargs.get("simplify", False)
        self.simplify_tolerance = 0.00001
        self.area_threshold = kwargs.get("area_threshold", 1e6)
        self.grid_size_degrees = kwargs.get("grid_size_degrees", 1)
        self.precision = kwargs.get("precision", 5)
        self._scale = kwargs.get("scale", 300)
        self._best_effort = kwargs.get("best_effort", False)
        self.max_pixels = kwargs.get("max_pixels", 1e18)
        self.chunk_size = kwargs.get("chunk_size", 500)
        self.use_exceeds_limit = kwargs.get("use_exceeds_limit", False)

        if self.simplify:
            self.simplify_tolerance = 0.001
            self.precision = 4

        if self._best_effort:
            self.max_pixels = 1e7

        filepath = kwargs.get("config_filepath", "earthengine.yaml")
        self._config = Config(filepath)

    def measure(self, gdf, area_km2=None):
        """
        Packages GeoDataFrame as an EarthEngine FeatureCollection object and executes
        zonal statistics against all geometries.
        :param area_km2:
        :param gdf: GeoDataFrame
        :return: Metric object
        """
        if self._exceeds_limit(area_km2):
            raise MetricComputeException(
                f"Could not compute metric for geometry. Area exceeds limit: {area_km2}km2"
            )

    def _package_metric(self, raw_data):
        raise NotImplementedError

    def _exceeds_limit(
        self,
        area_km2=None,
        rules=(
            (("tree-loss", "protected-areas",), 3.0e9),
            (("modis-fire", "modis-evi"), 1.1e7),
        ),
    ):
        if area_km2 is not None and self.use_exceeds_limit:
            slug = self.slug
            pixels = area_km2 * 1e6 / self._scale ** 2
            for slugs, threshold in rules:
                if slug in slugs and pixels > threshold:
                    return True
        return False

    def _intersect(self, feats_list, reducers, scale):
        n = self.chunk_size
        chunked_feat_cols = [
            ee.FeatureCollection(feats_list[i : i + n])
            for i in range(0, len(feats_list), n)
        ]

        data = []
        for i, feats in enumerate(chunked_feat_cols):
            logger.info(f"Analysing chunk {i+1}")
            for k, v in reducers.items():
                im = v["image"]
                reducer = v["reducer"]
                band = v.get("band", False)
                if band:
                    band = k

                feats = feats.map(
                    map_function(
                        image=im,
                        scale=scale,
                        reducers={k: reducer},
                        keep_geom=True,
                        band=band,
                        best_effort=self._best_effort,
                        max_pixels=self.max_pixels,
                    )
                )

            # Drop unnecessary geom after intersect
            feats_no_geom = feats.map(lambda e: e.setGeometry(None))
            data += [f["properties"] for f in feats_no_geom.getInfo()["features"]]

        return data

    def _simplify_polygon(self, gdf):
        """
        Simplifies geometries in a GeoDataFrame and reduces precision of coordinates.
        Returns the simplified GeoDataFrame.
        """
        simple_gdf = gdf.copy()
        simple_gdf["geometry"] = gdf.geometry.simplify(
            tolerance=self.simplify_tolerance, preserve_topology=True
        ).buffer(0)

        for i in range(0, len(simple_gdf)):
            geom = simple_gdf.iloc[i].geometry
            g = wkt.dumps(geom, rounding_precision=4)
            simple_gdf.at[i, "geometry"] = wkt.loads(g)

        return simple_gdf

    def _breakdown_shape(self, gdf):
        """
        Breaks down MultiPolygons in GeoDataFrame into additional Polygon rows
        and returns a GeoDataFrame object.
        :param param gdf: GeoDataFrame
        :return: featureCollection
        """
        new_gdf = gpd.GeoDataFrame()

        for i in range(0, len(gdf)):
            row = gdf.iloc[i]

            if isinstance(row.geometry, Iterable):
                polygons = list(row.geometry)
            else:
                polygons = [row.geometry]

            for poly in polygons:
                tmp_gdf = gpd.GeoDataFrame({"geometry": [poly]}, geometry="geometry")
                new_gdf = gpd.GeoDataFrame(
                    pd.concat([new_gdf, tmp_gdf], ignore_index=True)
                )

        new_gdf.crs = "EPSG:4326"
        polys_gdf = new_gdf.copy()

        # Simplify so shapes are small enough to meet GEE's payload size.
        # Tolerance = 0.00001 is very close to original quality
        # Precision = 4 gives nearest 10m
        if self.simplify:
            polys_gdf = self._simplify_polygon(polys_gdf)

        # to equal area for area measurement
        equal_area_gdf = polys_gdf.to_crs("EPSG:3395")

        polys_gdf["area_km2"] = equal_area_gdf["geometry"].area / 10 ** 6
        geom = geojson.loads(polys_gdf.to_json())

        if self.grid:
            feats = [
                {
                    "ee_feature": ee.Feature(geom=f["geometry"], opt_properties={}),
                    "area_km2": f["properties"].get("area_km2"),
                }
                for f in geom["features"]
            ]

            # Grid large shapes
            gridded_feature_list = []
            for feat in feats:
                if feat["area_km2"] > self.area_threshold:
                    gridded_feature_list += self._create_grid(
                        ee_feature=feat["ee_feature"],
                        grid_size_degrees=self.grid_size_degrees,
                    )
                else:
                    gridded_feature_list += [feat["ee_feature"]]

            logger.info(
                f"Created {len(gridded_feature_list)} grid cells of size {self.grid_size_degrees} arc-degrees."
            )
            return gridded_feature_list
        else:
            return [
                ee.Feature(geom=f["geometry"], opt_properties={})
                for f in geom["features"]
            ]

    def _create_grid(self, ee_feature, grid_size_degrees):
        """
        Breaks down a feature into an N x N grid and returns a new list of ee.Features.
        :param ee_feature:  ee.Feature
        :param grid_size_degrees: Grid size in arc degrees
        :return: list of ee.Features
        """

        # Arc grid JS equivalent here https://code.earthengine.google.com/bdb4f409515d1fda0592a8330a0f6528

        # Get bounds of grid
        bounds = ee_feature.bounds().geometry().bounds().getInfo()

        x_coords = [b[0] for b in bounds["coordinates"][0]]
        y_coords = [b[1] for b in bounds["coordinates"][0]]

        lon_start = min(x_coords)
        lon_end = max(x_coords)
        lat_start = min(y_coords)
        lat_end = max(y_coords)

        lon_width = lon_end - lon_start
        lat_width = lat_end - lat_start

        # test grid size against bounding box
        if grid_size_degrees > lon_width and grid_size_degrees > lat_width:
            logger.info("Grid larger than feature. Skipping.")
            return [ee_feature]

        elif grid_size_degrees > lon_width / 2 and grid_size_degrees > lat_width / 2:
            logger.warning(
                "Expecting less than 4 grids. Consider using a smaller grid_size_degrees or larger area_threshold."
            )

        # Generate grid over ee_feature
        polys = []
        lon = lon_start
        while lon < lon_end:
            x1 = lon
            x2 = lon + grid_size_degrees
            lon += grid_size_degrees

            lat = lat_start
            while lat < lat_end:
                y1 = lat
                y2 = lat + grid_size_degrees
                lat += grid_size_degrees

                polys.append(ee.Feature(ee.Geometry.Rectangle(x1, y1, x2, y2), {}))

        # Intersects grid against ee_feature
        intersected_feats = []
        for p in polys:
            intersection = p.intersection(ee_feature, ee.ErrorMargin(1))
            intersected_feats.append(
                ee.Feature(intersection).set(
                    {"area": intersection.area().divide(1000 * 1000).floor()}
                )
            )

        return intersected_feats
