
import os
from setuptools import setup, find_namespace_packages

version="0.0.1"

if "BUILD_NUM" in os.environ.keys():
    version += "." + os.environ["BUILD_NUM"]

setup(
  name = "pyastbuilder",
  version = version,
  packages=find_namespace_packages(where='src'),
  package_dir = {'' : 'src'},
  author = "Matthew Ballance",
  author_email = "matt.ballance@gmail.com",
  description = ("Utility for generating AST classes from a json description"),
  license = "Apache 2.0",
  keywords = ["Parsing"],
  url = "https://github.com/mballance/pyastbuilder",
  entry_points={
    'console_scripts': [
      'astbuilder = astbuilder.__main__:main'
    ]
  },
  setup_requires=[
    'setuptools_scm'
  ],
  install_requires=[
  ],
)

