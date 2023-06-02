import setuptools


def open_requirements(path):
    with open(path) as f:
        requires = [
            r.split('/')[-1] if r.startswith('git+') else r
            for r in f.read().splitlines()]
    return requires


readme = open('README.md').read()
history = open('HISTORY.md').read()
requirements = open_requirements('requirements.txt')

setuptools.setup(
    name='optim_esm_tools',
    version='0.1.0',
    description='Tools for OptimESM',
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    author='Joran R. Angevaare',
    url='https://github.com/JoranAngevaare/optim_esm_tools',
    packages=setuptools.find_packages() + ['extra_requirements'],
    package_dir={'optim_esm_tools': 'optim_esm_tools',
                 'extra_requirements': 'extra_requirements'},
    package_data={'optim_esm_tools': ['data/*'],
                  'extra_requirements': ['requirements-tests.txt'],
                  },
    setup_requires=['pytest-runner'],
    install_requires=requirements,
    python_requires=">=3.8",
    tests_require=requirements + ['pytest',
                                  'hypothesis-numpy',
                                  'unittest',
                                  'coverage'],
    scripts=[],
    keywords=[],
    classifiers=['Intended Audience :: Science/Research',
                 'Development Status :: 2 - Pre-Alpha',
                 'Programming Language :: Python :: 3.8',
                 'Natural Language :: English',
                 'Programming Language :: Python :: 3.8',
                 'Programming Language :: Python :: 3.9',
                 'Programming Language :: Python :: 3.10',
                 'Intended Audience :: Science/Research',
                 'Programming Language :: Python :: Implementation :: CPython',
                 'Topic :: Scientific/Engineering :: Physics',
                 ],
    zip_safe=False)
