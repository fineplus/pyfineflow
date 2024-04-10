from setuptools import setup, find_packages
# --skip-existing 覆盖
# python setup.py sdist bdist_wheel
# twine upload dist/* --skip-existing
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()
setup(
    name='pyfineflow',
    version='1.1.0',
    packages=find_packages(exclude=['__pycache__']),
    description='python nodes server for fineflow',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'fastapi[all]~=0.110.1',
    ],
    entry_points={
        'console_scripts': [
            'pyfineflow = pyfineflow.__main__:main'
        ]
    }
)
