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
