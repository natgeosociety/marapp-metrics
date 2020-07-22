import collections
import ee

from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import simple_mask_function
from ..helpers.logging import get_logger

logger = get_logger("protected-areas")

metric_fields = {
    "area_km2": 0,
    "marine_area_km2": 0,
    "marine_perc": 0,
    "terrestrial_area_km2": 0,
    "terrestrial_perc": 0,
    "unprotected_area_km2": 0,
    "unprotected_perc": 0,
}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class ProtectedAreas(MetricBase):
    """
    Breakdown of land area protected by type: Marine, Land, Both, No Protection
    """

    # compute flags
    default_scale = 30
    default_best_effort = True

    # config
    slug = "protected-areas"

    def __init__(self, **kwargs):
        """
        Initialise Protected Area metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        """
        super().__init__(**kwargs)

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property("metrics.protected_areas.dataset")

        # initialize ee.Images to be used for zonal statistics later
        area_im = ee.Image.pixelArea()  # area raster
        self._ee_im = ee.Image(self._ee_dataset).rename(
            ["pa"]
        )  # converting asset into an image
        self._ee_im_area = area_im.divide(1e6).rename(["area"])  # km2

        # mask each category to get area
        # collapse into Image collection?
        self._ee_im_unprotected = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=0
        ).rename(["area_unprotected"])
        self._ee_im_land = simple_mask_function(
            self._ee_im_area, self._ee_im, eq_or=[1, 3]
        ).rename(["area_land"])
        self._ee_im_marine = simple_mask_function(
            self._ee_im_area, self._ee_im, eq=2
        ).rename(["area_marine"])

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        feats = self._breakdown_shape(
            gdf
        )  # creates a featCol from target geom (i.e. multi-poly --> polygons)

        # reducer dict - keys match bands in raster
        reducers = {
            "area": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area,
                "band": True,
            },
            "area_unprotected": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_unprotected,
                "band": True,
            },
            "area_land": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_land,
                "band": True,
            },
            "area_marine": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_marine,
                "band": True,
            },
        }

        # ee compute area
        ee_data = self._intersect(feats, reducers, self._scale)
        logger.info(ee_data[0])
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
        metric_area_unprotected = sum([d["area_unprotected"] for d in data])
        metric_area_land = sum([d["area_land"] for d in data])
        metric_area_marine = sum([d["area_marine"] for d in data])

        return {
            "area": area,
            "area_unprotected": metric_area_unprotected,
            "area_land": metric_area_land,
            "area_marine": metric_area_marine,
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
            marine_area_km2=raw_data["area_marine"],
            terrestrial_area_km2=raw_data["area_land"],
            unprotected_area_km2=raw_data["area_unprotected"],
            marine_perc=100 * raw_data["area_marine"] / raw_data["area"],
            terrestrial_perc=100 * raw_data["area_land"] / raw_data["area"],
            unprotected_perc=100 * raw_data["area_unprotected"] / raw_data["area"],
        )
        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/romania.geojson"

    logger.debug(f"Importing geometry from {data_path}")
    gdf = gpd.read_file(data_path)

    protected_areas = ProtectedAreas(
        config_filepath="src/marapp_metrics/earthengine.yaml",
        grid=True,
        simplify=True,
        best_effort=False,
    )

    logger.debug(f"Running computations for: {protected_areas.slug}")
    m = protected_areas.measure(gdf)

    logger.debug(m)
