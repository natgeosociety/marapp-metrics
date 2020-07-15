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

import logging
import pytest
from marapp_metrics.metrics.biodiversity_intactness import BiodiversityIntactnessMetric

from ..util import (
    json_reader,
    traverse_nested,
    deepgetattr,
    geojson_reader,
    json_writer,
)

logger = logging.getLogger(__name__)


@pytest.mark.basic
@pytest.mark.parametrize(
    "shape_path,metric_path",
    [
        (
            "fixtures/shapes/romania-feature-collection.geojson",
            "fixtures/metrics/biodiversity-intactness/romania-data.json",
        ),
        (
            "fixtures/shapes/spain-feature-collection.geojson",
            "fixtures/metrics/biodiversity-intactness/spain-data.json",
        ),
        (
            "fixtures/shapes/france-feature-collection.geojson",
            "fixtures/metrics/biodiversity-intactness/france-data.json",
        ),
        (
            "fixtures/shapes/canada-feature-collection.geojson",
            "fixtures/metrics/biodiversity-intactness/canada-data.json",
        ),
        (
            "fixtures/shapes/africa-feature-collection.geojson",
            "fixtures/metrics/biodiversity-intactness/africa-data.json",
        ),
        (
            "fixtures/shapes/russia-feature-collection.geojson",
            "fixtures/metrics/biodiversity-intactness/russia-data.json",
        ),
    ],
)
def test_compute_basic(shape_path, metric_path):
    # Load the geometry..
    gdf = geojson_reader(shape_path)
    assert not gdf.empty

    handler = BiodiversityIntactnessMetric()

    # Compute the metric..
    metric = handler.measure(gdf)
    metric_data = metric._asdict()  # convert namedtuple to dict

    # Load or create precomputed data..
    precomputed_data = json_reader(metric_path, True)
    if precomputed_data is None:
        json_writer(metric_path, metric_data)

    # Compare results with precomputed metrics..
    for nested_key, value in traverse_nested(precomputed_data):
        if isinstance(value, float):
            assert deepgetattr(metric_data, nested_key) == pytest.approx(
                value, abs=1e-2
            )
        else:
            assert deepgetattr(metric_data, nested_key) == value


@pytest.mark.grid
@pytest.mark.parametrize(
    "shape_path,metric_path",
    [
        # (
        #     "fixtures/shapes/canada-feature-collection.geojson",
        #     "fixtures/metrics/biodiversity-intactness/canada-gridded-data.json",
        # ),
        # (
        #     "fixtures/shapes/russia-feature-collection.geojson",
        #     "fixtures/metrics/biodiversity-intactness/russia-gridded-data.json",
        # ),
    ],
)
def test_compute_grid(shape_path, metric_path):
    # Load the geometry..
    gdf = geojson_reader(shape_path)
    assert not gdf.empty

    handler = BiodiversityIntactnessMetric(grid=True, simplify=True, best_effort=False)

    # Compute the metric..
    metric = handler.measure(gdf)
    metric_data = metric._asdict()  # convert namedtuple to dict

    # Load or create precomputed data..
    precomputed_data = json_reader(metric_path, True)
    if precomputed_data is None:
        json_writer(metric_path, metric_data)

    # Compare results with precomputed metrics
    for nested_key, value in traverse_nested(precomputed_data):
        if isinstance(value, float):
            assert deepgetattr(metric_data, nested_key) == pytest.approx(
                value, abs=1e-2
            )
        else:
            assert deepgetattr(metric_data, nested_key) == value
