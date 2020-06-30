import collections

import ee

from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.logging import get_logger

logger = get_logger("biodiversity-intactness")

metric_fields = {
    "area_km2": 0,
    "int_area": 0,
    "int_perc": 0,
    "percentile_0": 0,
    "percentile_10": 0,
    "percentile_20": 0,
    "percentile_30": 0,
    "percentile_40": 0,
    "percentile_50": 0,
    "percentile_60": 0,
    "percentile_70": 0,
    "percentile_80": 0,
    "percentile_90": 0,
}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class BiodiversityIntactnessMetric(MetricBase):
    """
    Biodiversity intactness index metric using UNEP/NHM global data. Units: pixels/decile bin
    """

    # compute flags
    default_scale = 300
    default_best_effort = True

    # config
    slug = MetricBase.config.get_property("metrics.biodiversity_intactness.slug")

    def __init__(self, **kwargs):
        """
        Initialise biodiversity metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        - Any further subsidiary GEE images use in calculations
        """
        super().__init__(**kwargs)

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property(
            "metrics.biodiversity_intactness.dataset"
        )

        # initialize ee.Image
        self._ee_im = ee.Image(self._ee_dataset).rename(["bii"])
        self._ee_im_mean = (
            self._ee_im.multiply(ee.Image.pixelArea())
            .divide(1e6)
            .rename("area_product")
        )
        self._ee_im_area = ee.Image.pixelArea().divide(1e6).rename("area")  # km2
        self._ee_im_bii_area = (
            self._ee_im.gte(0)
            .multiply(ee.Image.pixelArea())
            .divide(1e6)
            .rename("bii_area")
        )  # km2

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        feats = self._breakdown_shape(gdf)

        reducers = {
            "bii": {
                "reducer": ee.Reducer.fixedHistogram(0.0, 1.0, 10).unweighted(),
                "image": self._ee_im,
                "band": True,
            },
            "bii_area": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_bii_area,
                "band": True,
            },
            "area": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_area,
                "band": True,
            },
            "area_product": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im_mean,
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
        intactness = sum([d["bii_area"] for d in data])
        area_product = sum([d["area_product"] for d in data])
        mean = area_product / area
        tmp_hist = {
            "0.0": 0,
            "0.1": 0,
            "0.2": 0,
            "0.3": 0,
            "0.4": 0,
            "0.5": 0,
            "0.6": 0,
            "0.7": 0,
            "0.8": 0,
            "0.9": 0,
        }
        for d in data:
            bii_hist = d.get("bii", None)
            if bii_hist:
                for el in bii_hist:
                    perc_bin = str(float(round(el[0], 2)))
                    tmp_hist[perc_bin] += el[1]
        return {"area": area, "intactness": intactness, "mean": mean, "bii": tmp_hist}

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
            int_area=round(raw_data["intactness"]),
            int_perc=round(100.0 * raw_data["mean"]),
            percentile_0=raw_data["bii"]["0.0"],
            percentile_10=raw_data["bii"]["0.1"],
            percentile_20=raw_data["bii"]["0.2"],
            percentile_30=raw_data["bii"]["0.3"],
            percentile_40=raw_data["bii"]["0.4"],
            percentile_50=raw_data["bii"]["0.5"],
            percentile_60=raw_data["bii"]["0.6"],
            percentile_70=raw_data["bii"]["0.7"],
            percentile_80=raw_data["bii"]["0.8"],
            percentile_90=raw_data["bii"]["0.9"],
        )
        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/canada.geojson"

    logger.debug(f"Importing geometry from: {data_path}")
    gdf = gpd.read_file(data_path)

    biodiversity_intactness = BiodiversityIntactnessMetric(
        grid=True, simplify=True, best_effort=False
    )

    logger.debug(f"Running computations for: {biodiversity_intactness.slug}")
    m = biodiversity_intactness.measure(gdf)

    logger.debug(m)
