import collections
import ee

from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import simple_mask_function
from ..helpers.logging import get_logger
from ..helpers.util import json_reader

logger = get_logger("land-cover")

metric_fields = {"data_2015": {}, "area_km2": 0}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class LandUseLandCover(MetricBase):
    """
    Calculates area of land use / land cover classification for 2015.
    """

    # compute flags
    default_scale = 300
    default_best_effort = True

    # config
    slug = "land-use"

    def __init__(self, **kwargs):
        """
        Initialise Land Use metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        """
        super().__init__(**kwargs)

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property("metrics.land_use.dataset")
        self._dataset_defs = json_reader("../data/land_cover_defs.json")

        # initialize ee.Images to be used for zonal statistics later
        area_im = ee.Image.pixelArea()  # area raster
        self._ee_im_area = area_im.divide(1e6).rename(["area"])  # km2
        self._ee_im_lulc = ee.Image(self._ee_dataset)

        im_dict = {}
        taxonomy = self._dataset_defs["taxonomy"]
        for key in taxonomy.keys():
            tmp_im = simple_mask_function(
                self._ee_im_area, self._ee_im_lulc, eq=int(key)
            )
            im_dict[key] = tmp_im

        _ee_im_col_area = ee.ImageCollection(list(im_dict.values()))
        _ee_im = _ee_im_col_area.toBands()
        self._ee_im = _ee_im.rename(list(im_dict.keys()))

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        feats = self._breakdown_shape(
            gdf
        )  # creates a featCol from target geom (i.e. multi-poly --> polygons)

        # reducer dict - keys match bands in raster
        reducers = {
            "land_cover_2015": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im,
                "band": False,  # key is not a band name
            }
        }

        # ee compute area
        ee_data = self._intersect(feats, reducers, self._scale)

        # aggregate data
        raw_data = self._aggregate(ee_data)

        return self._package_metric(raw_data)

    def _aggregate(self, data):
        """
        Aggregates an array of data dicts into a single metric.
        :param data: JSON object
        :return: Metric object
        """
        # get tmp aggregation dict
        class_defs = self._dataset_defs["class_defs"]

        total_data_area = 0
        for class_def in class_defs:
            area_sum = 0
            for d in data:
                area_sum += sum(
                    [
                        v
                        for k, v in d["land_cover_2015"].items()
                        if k in class_def["classes"]
                    ]
                )
            total_data_area += area_sum
            class_def["area"] = area_sum

        return {
            "data_2015": {el["slug"]: el["area"] for el in class_defs},
            "area": total_data_area,
        }

    def _package_metric(self, raw_data):
        """
        Serializes Metric object.
        :param self:
        :return: Metric object
        """
        if not raw_data:
            raise MetricPackageException("Could not package metric for geometry")

        metric = Metric(area_km2=raw_data["area"], data_2015=raw_data["data_2015"])
        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/canada.geojson"

    logger.debug(f"Importing geometry from {data_path}")
    gdf = gpd.read_file(data_path)

    land_cover = LandUseLandCover(
        config_filepath="src/marapp_metrics/earthengine.yaml",
        grid=True,
        simplify=True,
        best_effort=False,
    )

    logger.debug(f"Running computations for: {land_cover.slug}")
    m = land_cover.measure(gdf)

    logger.debug(m)
