"""Packaging metadata for Module 5 reproducible installs."""

from setuptools import setup


setup(
    name="module_5_gradcafe_analytics",
    version="0.1.0",
    description="Module 5 GradCafe analytics Flask app",
    py_modules=[
        "app",
        "load_data",
        "query_data",
        "data_builders",
        "db_config",
    ],
    package_dir={"": "src"},
)
