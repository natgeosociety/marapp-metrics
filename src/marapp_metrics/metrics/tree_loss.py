import collections
import ee

from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import simple_mask_function
from ..helpers.logging import get_logger

logger = get_logger("tree-loss")

metric_fields = {"year_data": {}, "area_km2": 0}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class TreeLoss(MetricBase):
    """
    Calculates tree cover loss area at 30% tree cover threshold between 2001 and 2018.
    """

    # compute flags
    default_scale = 30
    default_best_effort = True

    # config
    slug = MetricBase.config.get_property("metrics.tree_loss.slug")

    def __init__(self, **kwargs):
        """
        Initialise Land Use metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        """
        super().__init__(**kwargs)

        self.years = 18

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property("metrics.tree_loss.dataset")

        # initialize ee.Images to be used for zonal statistics later
        area_im = ee.Image.pixelArea()  # area raster
        self._ee_im_area = area_im.divide(1e6).rename(["area"])  # km2

        _ee_im_loss = ee.Image(self._ee_dataset).select("lossyear_30")
        _ee_im_dict = {"area": self._ee_im_area}
        for j in range(1, self.years + 1):
            year = 2000 + j
            _ee_im_year = simple_mask_function(self._ee_im_area, _ee_im_loss, eq=j)
            _ee_im_dict[f"{year}"] = _ee_im_year

        _ee_im_col = ee.ImageCollection(list(_ee_im_dict.values()))
        _ee_im = _ee_im_col.toBands()
        self._ee_im = _ee_im.rename(list(_ee_im_dict.keys()))

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        feats = self._breakdown_shape(
            gdf
        )  # creates a featCol from target geom (i.e. multi-poly --> polygons)

        # reducer dict - keys match bands in raster
        reducers = {
            "tree_loss": {
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
        tmp_parsed_data = {f"{2000 + j}": 0 for j in range(1, self.years + 1)}

        area = 0
        for location in data:
            for k, v in location["tree_loss"].items():
                if k != "area":
                    tmp_parsed_data[k] += v
                else:
                    area += v

        return {"year_data": tmp_parsed_data, "area": area}

    def _package_metric(self, raw_data):
        """
        Serializes Metric object.
        :param self:
        :return: Metric object
        """
        if not raw_data:
            raise MetricPackageException("Could not package metric for geometry")

        metric = Metric(area_km2=raw_data["area"], year_data=raw_data["year_data"])

        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/rothschild-giraffe.geojson"

    logger.debug(f"Importing geometry from {data_path}")
    gdf = gpd.read_file(data_path)

    tree_loss = TreeLoss(grid=True, simplify=True, best_effort=False)

    logger.debug(f"Running computations for: {tree_loss.slug}")
    m = tree_loss.measure(gdf)

    logger.debug(m)
