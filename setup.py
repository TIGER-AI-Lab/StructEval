from setuptools import setup, find_packages

setup(
    name='structeval',
    version='0.0.5',
    description='',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Jialin Yang, Dongfu Jiang, Tony He, Sherman Siu, Yuxuan Zhang, Disen Liao, Zhuofeng Li, Huaye Zeng, Yiming Jia, Haozhe Wang, Benjamin Schneider, Chi Ruan, Wentao Ma, Zhiheng Lyu, Yifei Wang, Yi Lu, Quy Duc Do, Ziyan Jiang, Ping Nie, Wenhu Chen',
    author_email='dongfu.jiang@uwaterloo.ca',
    packages=find_packages(),
    url='https://github.com/TIGER-AI-Lab/StructEval',
    entry_points={"console_scripts": ["structeval = structeval.cli:main"]},
    install_requires=[
        "fire",
        "llm-engines",
        "playwright",
        "transformers",
        "sentencepiece",
        "torch",
        "accelerate",
        "xmltodict",
        "toml",
        "pdf2image",
        "dotenv",
        "markdown",
        "matplotlib"
    ],
    extras_require={}
)



# change it to pyproject.toml
# [build-system]
# python setup.py sdist bdist_wheel
# twine upload dist/*