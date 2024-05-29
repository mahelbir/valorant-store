import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

pkg_name = "valorantstore"
setuptools.setup(
    name=pkg_name,
    version="6.0.0.0",
    author="Mahmuthan Elbir",
    author_email="me@mahmuthanelbir.com.tr",
    description="Python module to display your Valorant store",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=['valorant store', 'valorant api'],
    license="MIT",
    url="https://github.com/mahelbir/valorant-store",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=[pkg_name],
    include_package_data=True,
    install_requires=[
        "requests~=2.28.2",
        "cfscrape~=2.1.1"
    ],
    python_requires=">=3.7"
)
