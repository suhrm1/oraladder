from setuptools import find_packages, setup

setup(
    name="oraladder",
    version="2.1.0",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["filelock", "flask", "numpy", "pyyaml", "trueskill", "pytest", "pydantic"],
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
