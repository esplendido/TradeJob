from setuptools import setup, find_packages

setup(
    name="trade_job",
    version="1.0.0",
    install_requires=["pymongo", "python-binance", "requests"],
    extras_require={
        "develop": ["wheel", "pipdeptree"]
    },
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "trade_info = trade_job.trade_info_main:main",
            "trade_info_daily = trade_job.trade_info_daily:main",
        ]
    }
)