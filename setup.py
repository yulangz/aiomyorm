import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="aiomyorm",
    version="0.2.0",
    author="yulansp",
    author_email="1301481108@qq.com",

    install_requires=["aiomysql>=0.0.20",
                      "aiosqlite>=0.12.0"],

    description="A easy-to-use asynchronous ORM framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yulansp/aiomyorm",
    project_urls={
        "Documentation": "https://aiomyorm.readthedocs.io",
        "Source Code": "https://github.com/yulansp/aiomyorm",
    },
    # packages=['aiomyorm', 'tests'],
    packages=setuptools.find_packages(),
    # package_data={
    #     "aiomyorm": ["*.py"],
    #     "tests": ["*.py"],
    # },

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)