from setuptools import setup
from pathlib import Path

requirements = Path('requirements.txt').read_text().split('\n')
readme = Path('README.md').read_text()


setup(name="buffer",
      version="0.0.7",
      description="A stream buffer backed by a spooled temporary file.",
      long_description=readme,
      long_description_content_type="text/markdown",
      url="https://alexdelorenzo.dev",
      author="Alex DeLorenzo",
      license="AGPL-3.0",
      packages=['buffer'],
      zip_safe=True,
      install_requires=requirements,
      keywords="stream-buffer stream buffer file buffer temporary file".split(' '),
      python_requires='>=3.6',
)
