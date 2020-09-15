
#!/usr/bin/env python
from setuptools import setup, find_packages
import os


data_files = [(d, [os.path.join(d, f) for f in files])
              for d, folders, files in os.walk(os.path.join('src', 'config'))]


setup(name='simple-commands',
      version='.01',
      description='library for simple commands and stuff',
      author='Adam Pridgen',
      author_email='adam.pridgen.phd@gmail.com',
      install_requires=['wheel', 'quart', 'mongoengine', 'regex', 
                        'ipython', 'flask', 'flask_restful', 'requests', 
                        'paramiko', 'boto3', 'netifaces', 'scp', 'hypercorn'],
      packages=find_packages('src'),
      package_dir={'': 'src'},
)
