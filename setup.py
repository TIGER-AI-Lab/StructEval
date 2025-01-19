from setuptools import setup, find_packages

setup(
    name='structeval',
    version='0.0.5',
    description='',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Dongfu Jiang',
    author_email='dongfu.jiang@uwaterloo.ca',
    packages=find_packages(),
    url='https://github.com/TIGER-AI-Lab/StructEval',
    entry_points={"console_scripts": ["structeval = structeval.cli:main"]},
    install_requires=[
        "fire",
        "transformers",
        "sentencepiece",
        "torch",
        "accelerate",
        "llm-engines"
    ],
    extras_require={}
)



# change it to pyproject.toml
# [build-system]
# python setup.py sdist bdist_wheel
# twine upload dist/*