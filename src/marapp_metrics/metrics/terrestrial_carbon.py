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

from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import simple_mask_function
from ..helpers.logging import get_logger

logger = get_logger("terrestrial-carbon")

metric_fields = {
    "area_km2": 0,
    "carbon_density": 0,
    "carbon_soil_total_t": 0,
    "carbon_total_t": 0,
    "soil_density": 0,
    "soil_total_t": 0,
    "total_density": 0,
}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class TerrestrialCarbon(MetricBase):
    """
    Calculates total biomass, soil biomass, and carbon biomass in tonnes
    using total biomass density and carbon biomass density.

    Note Soil = Total biomass - Carbon biomass
    """

    # compute flags
    default_scale = 300
    default_best_effort = True

    # config
    slug = "terrestrial-carbon"

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
        self._ee_dataset = self._config.get_property(
            "metrics.terrestrial_carbon.dataset"
        )

        # initialize ee.Images to be used for zonal statistics later
        area_im = ee.Image.pixelArea()  # area raster
        self._ee_im_area = area_im.divide(1e6).rename(["area"])  # km2

        # Biomass carbon density
        _ee_im_carbon = ee.Image(self._ee_dataset.get("carbon"))
        _ee_im_carbon_density = simple_mask_function(
            _ee_im_carbon, _ee_im_carbon, gte=0
        )
        _ee_im_carbon = _ee_im_carbon_density.multiply(area_im).divide(1e4)  # ha

        # Total density
        _ee_im_total = ee.Image(self._ee_dataset.get("total"))
        _ee_im_total_density = simple_mask_function(_ee_im_total, _ee_im_total, gte=0)
        _ee_im_total = _ee_im_total_density.multiply(area_im).divide(1e4)  # ha

        _ee_im_col = ee.ImageCollection([_ee_im_carbon, _ee_im_total, self._ee_im_area])
        _ee_im = _ee_im_col.toBands()
        self._ee_im = _ee_im.rename(["carbon", "total", "area"])

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        feats = self._breakdown_shape(
            gdf
        )  # creates a list of ee.Features from target geom (i.e. multi-poly --> polygons)

        # reducer dict - keys match bands in raster
        reducers = {
            "terrestrial_carbon": {
                "reducer": ee.Reducer.sum().unweighted(),
                "image": self._ee_im,
                "band": False,  #  key is not a band name
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
        area = sum([d["terrestrial_carbon"]["area"] for d in data])
        metric_total = sum([d["terrestrial_carbon"]["total"] for d in data])
        metric_carbon = sum([d["terrestrial_carbon"]["carbon"] for d in data])

        return {
            "area": area,
            "carbon_soil": metric_total,
            "carbon": metric_carbon,
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
            carbon_soil_total_t=raw_data["carbon_soil"],
            carbon_total_t=raw_data["carbon"],
            soil_total_t=raw_data["carbon_soil"] - raw_data["carbon"],
            carbon_density=raw_data["carbon_soil"] / raw_data["area"],
            soil_density=raw_data["carbon"] / raw_data["area"],
            total_density=(raw_data["carbon_soil"] - raw_data["carbon"])
            / raw_data["area"],
        )
        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/canada.geojson"

    logger.debug(f"Importing geometry from: {data_path}")
    gdf = gpd.read_file(data_path)

    terrestrial_carbon = TerrestrialCarbon(
        config_filepath="src/marapp_metrics/earthengine.yaml",
        grid=True,
        simplify=True,
        best_effort=False,
    )

    logger.debug(f"Running computations for: {terrestrial_carbon.slug}")
    m = terrestrial_carbon.measure(gdf)

    logger.debug(m)
