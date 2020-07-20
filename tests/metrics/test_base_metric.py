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
    # Load the geometry..
    gdf = geojson_reader(shape_path)
    assert not gdf.empty

    polygon = ee.Geometry.Polygon([
    [[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]]
    ])

    ee_feature = ee.Feature(polygon,{})

    grids = MetricBase._create_grid(ee_feature, 1)

    ## Check that coorrect number of grids are made
    assert len(grids) == 20*20
