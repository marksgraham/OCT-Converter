import pathlib
from setuptools import setup, find_packages

# the directory containing this file
HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name='oct_converter', 
    version='0.1',
    description='Extract OCT and fundus data from proprietary file formats.',
    long_description=README,
    long_description_content_type="text/markdown",
    url='https://github.com/marksgraham/OCT-Converter',
    author='Mark Graham',
    author_email='markgraham539@gmail.com',
    license="MIT",
    python_requires='>3.5',
    install_requires=['construct','imageio','natsort','numpy','opencv-python','pydicom','six','matplotlib','imageio-ffmpeg', 'pylibjpeg', 'pathlib'],
    packages=find_packages(),
    include_package_data=True
)
