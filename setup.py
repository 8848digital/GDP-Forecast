from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

print(requirements)

setup(
    name='gdp_forecasting',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
)
