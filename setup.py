from setuptools import setup, find_packages

__version__ = "1.0.0"

install_requires = [
    "earthengine-api==0.1.215",
    "numpy==1.18.1",
    "geopandas==0.7.0",
    "Shapely==1.7.0",
    "geojson==2.5.0",
    "PyYAML==5.3",
]

setup(
    name="marapp_metrics",
    version=__version__,
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={"marapp_metrics": ["sample-data/*.json"]},
    install_requires=install_requires,
)
