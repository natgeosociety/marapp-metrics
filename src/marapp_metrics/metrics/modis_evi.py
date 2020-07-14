"""
  Copyright 2018-2020 National Geographic Society

  Use of this software does not constitute endorsement by National Geographic
  Society (NGS). The NGS name and NGS logo may not be used for any purpose without
  written permission from NGS.

  Licensed under the Apache License, Version 2.0 (the "License"); you may not use
  this file except in compliance with the License. You may obtain a copy of the
  License at

      https://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software distributed
  under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
  CONDITIONS OF ANY KIND, either express or implied. See the License for the
  specific language governing permissions and limitations under the License.
"""

import collections

import ee
import numpy as np


from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import simple_mask_function
from ..helpers.logging import get_logger

logger = get_logger("modis-evi")

metric_fields = {
    "year_data": {},
    "mean": 0,
    "mean_norm": 0,
    "area_km2": 0,
    "std_p1": 0,
    "std_m1": 0,
    "std_p2": 0,
    "std_m2": 0,
    "rg_slope": 0,
    "rg_start": 0,
    "rg_end": 0,
}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class ModisEvi(MetricBase):
    """
    Calculates total evi per year as well as a mean evi for all the years.
    """

    # compute flags
    default_scale = 250
    default_best_effort = True

    # config
    slug = MetricBase.config.get_property("metrics.modis_evi.slug")

    def __init__(self, **kwargs):
        """
        Initialise Modis Evi metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        """
        super().__init__()

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property("metrics.modis_evi.dataset")

        # dictionary sorted by key
        datasets = collections.OrderedDict(
            sorted(self._ee_dataset.items(), key=lambda t: t[0])
        )

        self._years = [str(e) for e in datasets.keys()]

        # initialize ee.Images to be used for zonal statistics later
        area_im = ee.Image.pixelArea()  # area of the pixel in m2
        ee_im_area = area_im.divide(1e6).rename(["area"])  # km2

        ee_masked_im = {}
        for k, v in datasets.items():
            tmp_im = ee.Image(v)
            masked_im = simple_mask_function(tmp_im, tmp_im, gte=0)

            scaled_im = masked_im.multiply(
                ee_im_area
            )  # pixel value multiplied by the pixel area
            ee_masked_im[str(k)] = scaled_im

        ee_masked_im["area"] = ee_im_area

        ee_im_col = ee.ImageCollection(list(ee_masked_im.values()))
        ee_im = ee_im_col.toBands()

        self._ee_im = ee_im.rename(list(ee_masked_im.keys()))

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        # creates a featCol from target geom (i.e. multi-poly --> polygons)
        feats = self._breakdown_shape(gdf)

        # reducer dict - keys match bands in raster
        # gets the sum of all the pixel value times the pixel area within a shape
        reducers = {
            "modis_evi": {
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
        year_data = {
            year: dict(year=int(year), value=0, norm=0, rescale=0)
            for year in self._years
        }

        area_km2 = 0
        for loc in data:
            for k, v in loc["modis_evi"].items():
                if k == "area":
                    area_km2 += v
                else:
                    year_data[k]["value"] += v

        for data in year_data.values():
            data["norm"] = data["value"] / area_km2

        # rescales the values from 0 to 1
        max_norm = max([data["norm"] for data in year_data.values()])

        for data in year_data.values():
            data["rescale"] = data["norm"] / max_norm

        mean = sum([e["value"] for e in year_data.values()]) / len(year_data.values())
        mean_norm = mean / area_km2

        # calculate thresholds
        std = (
            sum([(v["norm"] - mean_norm) ** 2 for v in year_data.values()])
            / len(year_data)
        ) ** 0.5
        std_p1 = mean_norm + std
        std_m1 = mean_norm - std
        std_p2 = mean_norm + 2 * std
        std_m2 = mean_norm - 2 * std

        # calculate regression line
        min_year = int(self._years[0])
        max_year = int(self._years[-1])
        x = np.array(range(min_year, max_year + 1))
        y = np.array([v["norm"] for v in year_data.values()])

        # calculates the slope of the regression line, which follows the equation y = mx + c
        mc = np.polyfit(x, y, 1)
        y_predict = [
            (mc[0] * v + mc[1]) for v in x
        ]  # calculates the regression line using the equation y = mx +c
        rg_start = y_predict[0]  # regression line start value
        rg_end = y_predict[-1]  # regression line end value

        return {
            "year_data": list(year_data.values()),
            "mean": mean,
            "mean_norm": mean_norm,
            "area_km2": area_km2,
            "std_p1": std_p1,
            "std_m1": std_m1,
            "std_p2": std_p2,
            "std_m2": std_m2,
            "rg_slope": mc[0],
            "rg_start": rg_start,
            "rg_end": rg_end,  # gets the slope (m) from the mc element
        }

    def _package_metric(self, raw_data):
        """
        Serializes Metric object.
        :param self:
        :return: Metric object
        """

        if not raw_data:
            raise MetricPackageException("Could not package metrics for geometry")

        metric = Metric(
            year_data=raw_data["year_data"],
            mean=raw_data["mean"],
            mean_norm=raw_data["mean_norm"],
            area_km2=raw_data["area_km2"],
            std_p1=raw_data["std_p1"],
            std_m1=raw_data["std_m1"],
            std_p2=raw_data["std_p2"],
            std_m2=raw_data["std_m2"],
            rg_slope=raw_data["rg_slope"],
            rg_start=raw_data["rg_start"],
            rg_end=raw_data["rg_end"],
        )

        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/rothschild-giraffe.geojson"

    logger.debug(f"Importing geometry from: {data_path}")
    gdf = gpd.read_file(data_path)

    modis_evi = ModisEvi()

    logger.debug(f"Running computations for: {modis_evi.slug}")
    m = modis_evi.measure(gdf)

    logger.debug(m)
