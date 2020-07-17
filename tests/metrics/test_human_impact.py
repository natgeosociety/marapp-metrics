import pytest
from marapp_metrics.metrics.human_impact import HumanInfluenceEnsembleMetric

from ..util import (
    json_reader,
    traverse_nested,
    deepgetattr,
    geojson_reader,
    json_writer,
)


@pytest.mark.basic
@pytest.mark.parametrize(
    "shape_path,metric_path",
    [
        (
            "fixtures/shapes/romania-feature-collection.geojson",
            "fixtures/metrics/human-impact/romania-data.json",
        ),
        (
            "fixtures/shapes/spain-feature-collection.geojson",
            "fixtures/metrics/human-impact/spain-data.json",
        ),
        (
            "fixtures/shapes/france-feature-collection.geojson",
            "fixtures/metrics/human-impact/france-data.json",
        ),
        (
            "fixtures/shapes/canada-feature-collection.geojson",
            "fixtures/metrics/human-impact/canada-data.json",
        ),
        (
            "fixtures/shapes/africa-feature-collection.geojson",
            "fixtures/metrics/human-impact/africa-data.json",
        ),
        (
            "fixtures/shapes/russia-feature-collection.geojson",
            "fixtures/metrics/human-impact/russia-data.json",
        ),
    ],
)
def test_compute_basic(shape_path, metric_path):
    # Load the geometry..
    gdf = geojson_reader(shape_path)
    assert not gdf.empty

    handler = HumanInfluenceEnsembleMetric(
        config_filepath="src/marapp_metrics/earthengine.yaml"
    )

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
        #     "fixtures/metrics/human-impact/canada-gridded-data.json",
        # ),
        # (
        #     "fixtures/shapes/russia-feature-collection.geojson",
        #     "fixtures/metrics/human-impact/russia-gridded-data.json",
        # ),
    ],
)
def test_compute_grid(shape_path, metric_path):
    # Load the geometry..
    gdf = geojson_reader(shape_path)
    assert not gdf.empty

    handler = HumanInfluenceEnsembleMetric(
        config_filepath="src/marapp_metrics/earthengine.yaml",
        grid=True,
        simplify=True,
        best_effort=False,
    )

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
