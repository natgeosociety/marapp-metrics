import collections
import ee

from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import simple_mask_function
from ..helpers.logging import get_logger

logger = get_logger("human-impact")

metric_fields = {
    "area_km2": 0,
    "area_0": 0,
    "area_1": 0,
    "area_2": 0,
    "area_3": 0,
    "area_4": 0,
    "area_no_data": 0,
    "area_masked": 0,
    "perc_0": 0,
    "perc_1": 0,
    "perc_2": 0,
    "perc_3": 0,
    "perc_4": 0,
    "perc_no_data": 0,
    "perc_masked": 0,
}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class HumanInfluenceEnsembleMetric(MetricBase):
    """
    Human impact index.
    """

    # compute flags
    default_scale = 1000
    default_best_effort = True

    # config
    slug = "human-impact"

    def __init__(self, **kwargs):
        """
        Initialise Human Impact Ensemble metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        """
        super().__init__(**kwargs)

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property(
            "metrics.human_impact.dataset"
        )  # only requires low impact

        # initialize ee.Images to be used for zonal statistics later
        area_im = ee.Image.pixelArea()  # area raster
        self._ee_im = ee.Image(self._ee_dataset).rename(
            ["li"]
        )  # converting asset into an image
        self._ee_im_area = area_im.divide(1e6).rename(["area"])  # km2

        # mask each category to get area
        # collapse into Image collection?
        self._ee_im_area_no_data = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=-1
        ).rename(["area_no_data"])
        self._ee_im_area_0 = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=0
        ).rename(["area_0"])
        self._ee_im_area_1 = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=1
        ).rename(["area_1"])
        self._ee_im_area_2 = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=2
        ).rename(["area_2"])
        self._ee_im_area_3 = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=3
        ).rename(["area_3"])
        self._ee_im_area_4 = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=4
        ).rename(["area_4"])

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        feats = self._breakdown_shape(
            gdf
        )  # creates a featCol from target geom (i.e. multi-poly --> polygons)

        # reducer dict - keys match bands in raster
        reducers = {
            "area_no_data": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area_no_data,
                "band": True,
            },
            "area_0": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area_0,
                "band": True,
            },
            "area_1": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area_1,
                "band": True,
            },
            "area_2": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area_2,
                "band": True,
            },
            "area_3": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area_3,
                "band": True,
            },
            "area_4": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area_4,
                "band": True,
            },
            "area": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area,
                "band": True,
            },
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
        area = sum([d["area"] for d in data])
        metric_area_no_data = sum([d["area_no_data"] for d in data])
        metric_area_0 = sum([d["area_0"] for d in data])
        metric_area_1 = sum([d["area_1"] for d in data])
        metric_area_2 = sum([d["area_2"] for d in data])
        metric_area_3 = sum([d["area_3"] for d in data])
        metric_area_4 = sum([d["area_4"] for d in data])
        metric_area_masked = (
            area
            - metric_area_no_data
            - metric_area_0
            - metric_area_1
            - metric_area_2
            - metric_area_3
            - metric_area_4
        )  # includes no data and masked

        metric_area_product = (
            metric_area_0
            + metric_area_1
            + metric_area_2
            + metric_area_3
            + metric_area_4
        )  # excludes no data
        mean = metric_area_product / area  # treating no-data as zero

        return {
            "area": area,
            "mean": mean,
            "area_no_data": metric_area_no_data,
            "area_masked": metric_area_masked,
            "area_0": metric_area_0,
            "area_1": metric_area_1,
            "area_2": metric_area_2,
            "area_3": metric_area_3,
            "area_4": metric_area_4,
        }

    def _package_metric(self, raw_data):
        """
        Serializes Metric object.
        :param self:
        :return: Metric object
        """
        if not raw_data:
            raise MetricPackageException("Could not package metric for geometry")

        metric = Metric(
            area_km2=raw_data["area"],
            area_0=raw_data["area_0"],
            area_1=raw_data["area_1"],
            area_2=raw_data["area_2"],
            area_3=raw_data["area_3"],
            area_4=raw_data["area_4"],
            area_no_data=raw_data["area_no_data"],
            area_masked=raw_data["area_masked"],
            perc_0=100 * raw_data["area_0"] / raw_data["area"],
            perc_1=100 * raw_data["area_1"] / raw_data["area"],
            perc_2=100 * raw_data["area_2"] / raw_data["area"],
            perc_3=100 * raw_data["area_3"] / raw_data["area"],
            perc_4=100 * raw_data["area_4"] / raw_data["area"],
            perc_no_data=100 * raw_data["area_no_data"] / raw_data["area"],
            perc_masked=100 * raw_data["area_masked"] / raw_data["area"],
        )
        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/romania.geojson"

    logger.debug(f"Importing geometry from: {data_path}")
    gdf = gpd.read_file(data_path)

    human_impact = HumanInfluenceEnsembleMetric(
        config_filepath="src/marapp_metrics/earthengine.yaml",
        grid=True,
        simplify=True,
        best_effort=False,
    )

    logger.debug(f"Running computations for: {human_impact.slug}")
    m = human_impact.measure(gdf)

    logger.debug(m)
