from setuptools import setup, find_packages
from setuptools.command.install import install

# Setting up
setup(
        name="python_lab_control", 
        version='0.0.1',
        author="Florian Dupeyron",
        description='Convenient class to control lab tools such as oscilloscope',
        readme = "README.md",
        packages=find_packages(where='src'),
        package_dir = {"": "src", "instr": "src/instr"},
        install_requires=['imap-tools ==0.41.0',
                          'importlib-metadata ==4.10.1',
                          'importlib-resources ==5.4.0',
                          'libusb ==1.0.24b3',
                          'numpy ==1.22.1',
                          'packaging ==21.3',
                          'Pillow ==9.0.0',
                          'pkg-about ==1.0.4',
                          'pyparsing ==3.0.7',
                          'python-usbtmc ==0.8',
                          'pyusb ==1.2.1',
                          'zipp ==3.7.0'],
)