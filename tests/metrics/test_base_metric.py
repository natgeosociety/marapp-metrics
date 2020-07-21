import ee
import pytest
from marapp_metrics.metrics.base.metric_base import MetricBase


@pytest.mark.basic
@pytest.mark.parametrize(
    "shape_path,metric_path",
    [("fixtures/shapes/canada-feature-collection.geojson", "",)],
)
def test_create_grid(shape_path, metric_path):
    degrees = 0.5
    base = MetricBase(config_filepath="src/marapp_metrics/earthengine.yaml")

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
    base = MetricBase(config_filepath="src/marapp_metrics/earthengine.yaml")
    degrees = 0.5

    # Create the geometry (triangle)
    polygon = ee.Geometry.Polygon([[[0, 0], [10, 0], [5, 5], [0, 0]]])
    ee_feature = ee.Feature(polygon, {})
    grids = base._create_grid(ee_feature, degrees)

    # Check that unnecessary grids are dropped
    assert len(grids) < 20 * (20 + 1)
