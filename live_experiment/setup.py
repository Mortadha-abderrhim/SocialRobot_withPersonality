from setuptools import find_packages, setup

package_name = 'live_experiment'

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
    maintainer='mortadha',
    maintainer_email='louay.najar@epfl.ch',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'live = live_experiment.live:main',
            'live_extro = live_experiment.live_extro:main',
            'live_intro = live_experiment.live_intro:main',
            'robot = live_experiment.robot:main'
        ],
    },
)
