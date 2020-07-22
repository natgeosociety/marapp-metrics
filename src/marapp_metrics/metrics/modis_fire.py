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
from datetime import timedelta, datetime

from .base.metric_base import MetricBase, MetricPackageException
from ..helpers.earthengine import filter_fires
from ..helpers.logging import get_logger
from ..helpers.util import abspath

logger = get_logger("modis-fire")

metric_fields = {"year_isoweek": [], "start_date": None, "end_date": None}

Metric = collections.namedtuple(
    "Metric", metric_fields.keys(), defaults=metric_fields.values()
)


class ModisFire(MetricBase):
    """
    Calculates fire metric.
    """

    # compute flags
    default_scale = 500
    default_best_effort = True

    # config
    slug = "modis-fire"

    def __init__(self, **kwargs):
        """
        Initialise Modis Fire metric object.
        Sets:

        - pixel scale (m)
        - GEE Image Asset
        """
        super().__init__(**kwargs)

        # compute flags
        self._scale = kwargs.get("scale", self.default_scale)
        self._best_effort = kwargs.get("best_effort", self.default_best_effort)

        # config
        self._ee_dataset = self._config.get_property("metrics.modis_fire.dataset")

        # initialize ee.Images to be used for zonal statistics later
        ee_im_fires = ee.ImageCollection(self._ee_dataset).map(filter_fires)
        area_im = ee.Image.pixelArea()  # area raster
        self._ee_im_area = area_im.divide(1e6).rename(["area"])  # km2

        # set start and end dates
        im_date_list = [
            d.replace("_", "-")
            for d in ee_im_fires.aggregate_array("system:index").getInfo()
        ]

        self.start_date = kwargs.get("start_date", im_date_list[0])
        self.end_date = kwargs.get("end_date", im_date_list[-1])

        start_year = int(self.start_date.split("-")[0])
        end_year = int(self.end_date.split("-")[0])

        images = {}
        dates = self._generate_isoweek()

        for year in range(start_year, end_year + 1):
            image = (
                ee_im_fires.filterDate(f"{year}-01-01", f"{year}-12-31")
                .select("BurnDate")
                .mosaic()
            )
            filtered_dates = [d for d in dates if d["year"] == year]

            for d in filtered_dates:
                start_day = int(d["start"])
                end_day = int(d["end"]) - 1
                year = d["year"]
                week = d["isoweek"]
                if start_day > end_day:
                    mask = image.gte(start_day).Or(image.lt(end_day))
                    masked = self._ee_im_area.updateMask(mask)
                else:
                    mask = image.gte(start_day).And(image.lt(end_day))
                    masked = self._ee_im_area.updateMask(mask)
                images[f"{year}-{week}"] = masked

        ee_im_col = ee.ImageCollection(list(images.values()))
        ee_im = ee_im_col.toBands()

        self._ee_im = ee_im.rename(list(images.keys()))

    def _generate_isoweek(self):
        """
        Generates start and end dates for each iso-week between start and end dates.
        """
        generated_weeks = []
        start = datetime.strptime(self.start_date, "%Y-%m-%d")
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        while start < end - timedelta(weeks=1):
            tmp_end = start + timedelta(weeks=1)
            start_year, start_isoweek, _ = start.isocalendar()
            end_year, end_isoweek, _ = tmp_end.isocalendar()

            day_start = datetime.strptime(
                f"{start_year}-{start_isoweek}-6", "%Y-%W-%w"
            ).strftime("%j")
            day_end = datetime.strptime(
                f"{end_year}-{end_isoweek}-0", "%Y-%W-%w"
            ).strftime("%j")

            generated_weeks.append(
                {
                    "start": int(day_start),
                    "end": int(day_end),
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date": tmp_end.strftime("%Y-%m-%d"),
                    "year": start_year,
                    "isoweek": start_isoweek,
                }
            )
            start = tmp_end

        return generated_weeks

    def measure(self, gdf, area_km2=None):
        super().measure(gdf, area_km2)

        # creates a list of ee.Features from target geom (i.e. multi-poly --> polygons)
        feats = self._breakdown_shape(gdf)

        # reducer dict - keys match bands in raster
        reducers = {
            "modis_fire": {
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
        iso_weeks = self._generate_isoweek()

        for date in iso_weeks:
            iso_date = f"{date['year']}-{date['isoweek']}"

            # get same date from all locations
            filtered_values = []
            for loc in data:
                for k, v in loc["modis_fire"].items():
                    if k == iso_date:
                        filtered_values.append(v)

            total_area = 0
            if len(filtered_values) != 0:
                total_area = sum(filtered_values)

            date["value"] = total_area

        return [
            dict(year=d["year"], isoweek=d["isoweek"], value=d["value"])
            for d in iso_weeks
        ]

    def _package_metric(self, raw_data):
        """
        Serializes Metric object.
        :param self:
        :return: Metric object
        """
        if not raw_data:
            raise MetricPackageException("Could not package metric for geometry")

        metric = Metric(
            year_isoweek=raw_data, start_date=self.start_date, end_date=self.end_date
        )
        return metric


if __name__ == "__main__":
    import geopandas as gpd

    data_path = "sample-data/romania.geojson"

    logger.debug(f"Importing geometry from {data_path}")
    gdf = gpd.read_file(data_path)

    modis_fire = ModisFire(
        config_filepath=abspath(__file__, "../earthengine.yaml"),
        start_date="2018-01-01",
        end_date="2018-12-31",
        grid=True,
        simplify=True,
        area_threshold=1e6,
        best_effort=False,
        grid_size=0.5,
        simplify_tolerance=0.001,
    )

    logger.debug(f"Running computations for: {modis_fire.slug}")
    m = modis_fire.measure(gdf)

    logger.debug(m)
