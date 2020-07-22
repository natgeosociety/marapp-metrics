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

from ..helpers.util import abspath
from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import simple_mask_function
from ..helpers.logging import get_logger

logger = get_logger("human-footprint")

metric_fields = {
    "area_km2": 0,
    "delta": 0,
    "mean_09": 0,
    "mean_93": 0,
    "sum_09": 0,
    "sum_93": 0,
}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class HumanFootprint(MetricBase):
    """
    Calculates human footprint over two time ranges: 1993, 2009.
    """

    # compute flags
    default_scale = 300
    default_best_effort = True

    # config
    slug = "human-footprint"

    def __init__(self, **kwargs):
        """
        Initialise Terrestrial Carbon metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        """
        super().__init__(**kwargs)

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property("metrics.human_footprint.dataset")

        # initialize ee.Images to be used for zonal statistics later
        area_im = ee.Image.pixelArea()  # area raster
        self._ee_im_area = area_im.divide(1e6).rename(["area"])  # km2

        _ee_im_1993_area = ee.Image(self._ee_dataset.get("1993")).multiply(
            self._ee_im_area
        )
        _ee_im_2009_area = ee.Image(self._ee_dataset.get("2009")).multiply(
            self._ee_im_area
        )
        _ee_im_col_area = ee.ImageCollection(
            [_ee_im_1993_area, _ee_im_2009_area, self._ee_im_area]
        )
        _ee_im = _ee_im_col_area.toBands()
        self._ee_im = _ee_im.rename(["1993", "2009", "area"])

        _ee_im_1993_px = simple_mask_function(_ee_im_1993_area, _ee_im_1993_area, gte=0)
        _ee_im_2009_px = simple_mask_function(_ee_im_2009_area, _ee_im_2009_area, gte=0)
        _ee_im_col_px = ee.ImageCollection([_ee_im_1993_px, _ee_im_2009_px])
        _ee_px = _ee_im_col_px.toBands()
        self._ee_px = _ee_px.rename(["1993", "2009"])

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        feats = self._breakdown_shape(
            gdf
        )  # creates a featCol from target geom (i.e. multi-poly --> polygons)

        # reducer dict - keys match bands in raster
        reducers = {
            "human_footprint_area": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im,
                "band": False,  # key is not a band name
            },
            "human_footprint_px": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_px,
                "band": False,  # key is not a band name
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
        area = sum([d["human_footprint_area"]["area"] for d in data])
        metric_area_93 = sum([d["human_footprint_area"]["1993"] for d in data])
        metric_area_09 = sum([d["human_footprint_area"]["2009"] for d in data])
        metric_px_93 = sum([d["human_footprint_px"]["1993"] for d in data])
        metric_px_09 = sum([d["human_footprint_px"]["2009"] for d in data])

        return {
            "area": area,
            "sum_area_93": metric_area_93,
            "sum_area_09": metric_area_09,
            "px_93": metric_px_93,
            "px_09": metric_px_09,
        }

    def _package_metric(self, raw_data):
        """
        Serializes Metric object.
        :param self:
        :return: Metric object
        """
        if not raw_data:
            raise MetricPackageException("Could not package metric for geometry")

        area = raw_data["area"]
        mean_09 = raw_data["sum_area_09"] / area
        mean_93 = raw_data["sum_area_93"] / area

        metric = Metric(
            area_km2=area,
            delta=mean_09 - mean_93,
            mean_09=mean_09,
            mean_93=mean_93,
            sum_09=mean_09 * raw_data["px_09"],
            sum_93=mean_93 * raw_data["px_93"],
        )
        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/canada.geojson"

    logger.debug(f"Importing geometry from: {data_path}")
    gdf = gpd.read_file(data_path)

    human_footprint = HumanFootprint(
        config_filepath=abspath(__file__, "../earthengine.yaml"),
        grid=True,
        simplify=True,
        best_effort=False,
    )

    logger.debug(f"Running computations for: {human_footprint.slug}")
    m = human_footprint.measure(gdf)

    logger.debug(m)
