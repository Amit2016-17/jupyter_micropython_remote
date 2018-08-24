from pathlib import Path
from setuptools import setup


# Get the long description from the README file
project = Path(__file__).parent
with (project / 'README.rst').open(encoding='utf-8') as f:
    long_description = f.read()


setup(name='jupyter_micropython_remote',
      use_scm_version=True,
      description='Jupyter notebook kernel for remote execution on a Micropython system.',
      long_description=long_description,
      author='Andrew Leech, Julian Todd, Tony DiCola',
      author_email='andrew@alelec.net',
      keywords='jupyter micropython',
      url='https://gitlab.com/alelec/jupyter_micropython_remote',
      license='GPL3',
      packages=['mpy_kernel'],
      install_requires=['pyserial>=3.4', 'jupyter', 'mpy-cross'],
      setup_requires=['setuptools_scm'],
)
