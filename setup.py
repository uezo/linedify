from setuptools import setup, find_packages

setup(
    name="linedify",
    version="0.2.0",
    url="https://github.com/uezo/linedify",
    author="uezo",
    author_email="uezo@uezo.net",
    maintainer="uezo",
    maintainer_email="uezo@uezo.net",
    description="💬⚡ linedify: Supercharging your LINE Bot with Dify power!",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["examples*", "tests*"]),
    install_requires=["aiohttp==3.9.5", "line-bot-sdk==3.11.0", "fastapi==0.111.0", "uvicorn==0.30.1"],
    license="Apache v2",
    classifiers=[
        "Programming Language :: Python :: 3"
    ]
)
