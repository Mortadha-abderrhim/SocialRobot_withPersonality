from setuptools import find_packages, setup

package_name = 'llm_module'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Mortadha',
    maintainer_email='mortadha.abderrahim@epfl.ch',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'llm = llm_module.llm:main',
            'llm_extro = llm_module.llm_extro:main',
            'llm_intro = llm_module.llm_intro:main',
            'chi = llm_module.chi:main',
        ],
    },
)
