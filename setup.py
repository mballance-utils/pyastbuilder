
import os
from setuptools import setup

version="0.0.1"

if "BUILD_NUM" in os.environ.keys():
    version += "." + os.environ["BUILD_NUM"]

setup(
  name = "pyastgen",
  version = version,
  packages=['astgen'],
  package_dir = {'' : 'src'},
  author = "Matthew Ballance",
  author_email = "matt.ballance@gmail.com",
  description = ("Utility for generating AST classes"),
  license = "Apache 2.0",
  keywords = ["Parsing"],
  url = "https://github.com/mballance/pyastgen",
  entry_points={
    'console_scripts': [
      'astgen = astgen.__main__:main'
    ]
  },
  setup_requires=[
    'setuptools_scm'
  ],
  install_requires=[
  ]
)

