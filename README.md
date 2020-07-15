## marapp-metrics
 
Marapp Python package for shape metric calculations with [Google Earth Engine](https://earthengine.google.com).

## Installation

To install the Python package use:

```bash
pipenv install -e git+git@github.com/natgeosociety/marapp-metrics.git@1.0.0#egg=marapp-metrics
```
For all available versions see tagged release versions.

## Usage

Basic usage example:

```python
import geopandas as gpd
from marapp_metrics.metrics.terrestrial_carbon import TerrestrialCarbon

# create a geopandas GeoDataFrame from a geojson shape file
gdf = gpd.read_file('./sample-data/rothschild-giraffe.geojson')

# instantiate the metric object
terrestrial_carbon = TerrestrialCarbon()

# compute the metric
metric = terrestrial_carbon.measure(gdf)
```

## Setup

Available commands:

| **Command**       | **Description**              |
| ----------------- | ---------------------------- |
| make setup        | Install dependencies         |
| make clean        | Clean all dependencies       |
| make test         | Run all tests                |
| make lint         | Lint code sources            |

Install all dependency packages.

```bash
$ make setup
```

A virtualenv will automatically be created, and packages from the [Pipfile](./Pipfile) installed.

## Running

Activate the virtualenv.

```bash
$ pipenv shell
```

Install the project in editable mode (i.e. setuptools "develop mode").

```bash
$ pip3 install -e .
```

The following environment variables are required by the application.

| **Key**                | **Description**                                                                  |
| ---------------------- |----------------------------------------------------------------------------------|
| GOOGLE_SERVICE_ACCOUNT | GCP Service Account Private Key.                                                 |

The required environment variables are also described in [.env.sample](.env.sample).

If you do not have a service account file to export via the `GOOGLE_SERVICE_ACCOUNT` argument, you can manually authenticate via the Earth Engine command line tool. 
 
```bash
$ earthengine authenticate
```

Earth Engine uses the OAuth 2.0 protocol for authenticating clients. Running this command will prompt you through the authentication process using your web browser.

Running a single example. Data from [sample-data](sample-data) directory is bundled for running samples.

```bash
$ python3 -m marapp_metrics.metrics.biodiversity_intactness
```

To kill the virtualenv.

```bash
$ deactivate
```

## Tests

The fixture data for the metric computations are generated on the first run of the tests, because results are highly dependent on the Earth Engine assets used. 

Subsequent test runs will use the previously generated data as reference for thresholding results.

Sequential execution.

```bash
$ pytest -v tests/
```

Parallel execution. Speed up test runs by making use of multiple CPUs.
```bash
$ pytest -v -n 4 tests/
```
Especially for longer running tests or tests requiring a lot of I/O this can lead to considerable speed ups. This option can also be set to `auto` for automatic detection of the number of CPUs.

Restrict a test run to only run tests marked with markers. Options are: `basic`, `grid`.

```bash
$ pytest -v -m basic tests/ 
```

## Packaging & deployment

Increment the package version from [setup.py](setup.py) as well as any dependencies changed.

Note: To get a list of all packages specified in Pipfile.lock run:
```bash
pipenv run pip freeze
```

Create a Git tag using the package version from [setup.py](setup.py).
```bash
git tag 1.0.0
```

Push the Git tags.

```bash
git push origin --tags
```

The package can now be installed from the Git repository.

## Configure Earth Engine assets

The template from [earthengine.yaml](src/earthpulse_metrics/earthengine.yaml) is required to map existing [Google Earth Engine](https://earthengine.google.com) image assets to computations supported by the library.

For more details about managing assets in Earth Engine, see: https://developers.google.com/earth-engine/asset_manager

The following public assets serve as examples for different types of computations supported by the library.

| **Type** | **Dataset** |
| ------------- |---------------- |
| `biodiversity_intactness` | https://data.nhm.ac.uk/dataset/global-map-of-the-biodiversity-intactness-index-from-newbold-et-al-2016-science |
| `human_footprint` | https://datadryad.org/stash/dataset/doi:10.5061/dryad.052q5 |
| `human_impact` | http://hdr.undp.org/en/content/human-development-index-hdi |
| `land_cover` | http://maps.elie.ucl.ac.be/CCI/viewer/ |
| `modis_evi` | https://lpdaac.usgs.gov/products/mod13q1v006/ |
| `modis_fire`|  http://modis-fire.umd.edu/ |
| `protected_areas` | https://www.protectedplanet.net/ |
| `terrestrial_carbon` | https://developers.google.com/earth-engine/datasets/catalog/WCMC_biomass_carbon_density_v1_0 |
| `tree_loss` | https://earthenginepartners.appspot.com/science-2013-global-forest/download_v1.5.html |
