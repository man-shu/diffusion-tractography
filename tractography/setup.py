#!/usr/bin/env python
from setuptools import setup

if __name__ == "__main__":
    setup(
        name="tractography",
        version="0.1",
        description="Tractography pipelines",
        author="Demian Wassermann",
        author_email="demian.wassermann@inria.fr",
        packages=["tractography"],
        entry_points={
            "console_scripts": [
                "shrink_surface=tractography.utils.shrink_surface:command_line_main",
                "tractography=tractography.cli.run:main",
            ]
        },
        install_requires=[
            r.strip() for r in open("requirements.txt").readlines()
        ],
    )
