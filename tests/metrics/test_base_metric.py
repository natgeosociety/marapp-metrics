import ee
import pytest
from marapp_metrics.metrics.base.metric_base import MetricBase

from ..util import (
    json_reader,
    traverse_nested,
    geojson_reader,
    json_writer,
)

@pytest.mark.basic
@pytest.mark.parametrize(
    "shape_path,metric_path",
    [("fixtures/shapes/canada-feature-collection.geojson", "",)],
)
def test_create_grid(shape_path, metric_path):
    # Create the geometry.
    base = MetricBase(config_filepath="src/marapp_metrics/earthengine.yaml")

    degrees = 0.5
    polygon = ee.Geometry.Polygon(
        [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]]
    )
    ee_feature = ee.Feature(polygon, {})
    grids = base._create_grid(ee_feature, degrees)
    ## Check that coorrect number of grids are made
    assert len(grids) == 20 * (20 + 1)
