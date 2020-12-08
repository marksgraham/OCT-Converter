from setuptools import setup, find_packages

setup(

    name='oct_converter', 
    version='0.1',
    description='Extract OCT and fundus data from proprietary file formats.',  
    url='https://github.com/marksgraham/OCT-Converter',
    author='Mark Graham',
    author_email='markgraham539@gmail.com',
    python_requires='>3.5',
    install_requires=['construct','imageio','natsort','numpy','opencv-python','pydicom','six','matplotlib','imageio-ffmpeg', 'pylibjpeg', 'pathlib'],
    packages=find_packages()

)
