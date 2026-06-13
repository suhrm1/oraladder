from setuptools import find_packages, setup

setup(
    name="oraladder",
    version="3.0.0",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "filelock",
        "flask",
        "mariadb",
        "numpy",
        "pyyaml",
        "openskill",
        "sqlalchemy",
        "trueskill",
        "pydantic",
    ],
    extras_require={
        "dev": [
            "pytest",
            "black",
            "pre-commit",
        ],
    },
    entry_points=dict(
        console_scripts=[
            "ora-ladder = laddertools.ladder:run",
            "ora-dbtool  = laddertools.ladder:initialize_periodic_databases",
            "ora-mapstool = laddertools.mapstool:run",
            "ora-ragl   = laddertools.ragl:run",
            "ora-replay = laddertools.replay:run",
            "ora-srvwrap  = laddertools.srvwrap:run",
        ],
    ),
)
