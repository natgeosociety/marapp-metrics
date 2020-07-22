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

import ee
import pytest
from marapp_metrics.metrics.base.metric_base import MetricBase
from marapp_metrics.helpers.util import abspath


@pytest.mark.basic
@pytest.mark.parametrize(
    "shape_path,metric_path",
    [("fixtures/shapes/canada-feature-collection.geojson", "",)],
)
def test_create_grid(shape_path, metric_path):
    degrees = 0.5
    base = MetricBase(
        config_filepath=abspath(__file__, "../../src/marapp_metrics/earthengine.yaml")
    )

    # Create the geometry.
    polygon = ee.Geometry.Polygon([[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]])
    ee_feature = ee.Feature(polygon, {})
    grids = base._create_grid(ee_feature, degrees)

    # Check that correct number of grids are made (note the extra 1 is from rounding errors in the bounds method)
    assert len(grids) == 20 * (20 + 1)


@pytest.mark.basic
@pytest.mark.parametrize(
    "shape_path,metric_path",
    [("fixtures/shapes/canada-feature-collection.geojson", "",)],
)
def test_create_grid_intersections(shape_path, metric_path):
    base = MetricBase(
        config_filepath=abspath(__file__, "../../src/marapp_metrics/earthengine.yaml")
    )
    degrees = 0.5

    # Create the geometry (triangle)
    polygon = ee.Geometry.Polygon([[[0, 0], [10, 0], [5, 5], [0, 0]]])
    ee_feature = ee.Feature(polygon, {})
    grids = base._create_grid(ee_feature, degrees)

    # Check that unnecessary grids are dropped
    assert len(grids) < 20 * (20 + 1)
