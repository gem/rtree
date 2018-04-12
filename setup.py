import os
import platform
import shutil
import subprocess
import urllib.request
import tarfile

from distutils.util import get_platform
from setuptools import setup, Extension
from wheel.bdist_wheel import bdist_wheel as bdist_wheel_


def get_libname():
    libname = ["libspatialindex.so.4", "libspatialindex_c.so.4"]
    if platform.system() == "Darwin":
        libname = ["libspatialindex.4.dylib", "libspatialindex_c.4.dylib"]
    elif platform.system() == "Windows":
        libname = ["libspatialindex.dll", "libspatialindex_c.dll"]
    return libname


def untar(archive):
    tar = tarfile.open(archive)
    tar.extractall()
    tar.close()


# attempt to run parallel make with at most 8 workers
def cpu_count():
    try:
        import multiprocessing
        return min(8, multiprocessing.cpu_count())
    except:
        return 1


def get_readme():
    with open('docs/source/README.txt', 'r') as fp:
        return fp.read()


# Download, unzip, configure, and make spatialindex C library from github.
# Attempt to skip steps that may have already completed.
def build_spatialindex(libname):
    version = '1.8.5'
    archive = 'spatialindex-' + version + '.tar.gz'
    destdir = 'libspatialindex-' + version

    if not os.path.exists(destdir):
        if not os.path.exists(archive):
            print("Downloading latest spatialindex master")
            theurl = ('https://github.com/libspatialindex/libspatialindex'
                      + '/archive/' + version + '.tar.gz')
            name, hdrs = urllib.request.urlretrieve(theurl, archive)

        print("Unzipping spatialindex master archive")
        untar(archive)

    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), destdir)
    shutil.copy('CMakeLists.txt', root)
    print("making spatialindex")
    if platform.system() == "Darwin":
        os.environ['CFLAGS'] = "-arch x86_64 -arch i386"
    retcode = subprocess.Popen([
        'cmake', '.',
        ], cwd=root).wait()
    retcode = subprocess.Popen([
        'make',
        '-j',
        str(cpu_count())
        ], cwd=root).wait()
    if 0 != retcode:
        raise RuntimeError("make failed")

    src = os.path.join(root, 'bin')
    dst = os.path.join('rtree', '.libs')
    os.mkdir(dst)
    print("copying {} to {}".format(src, dst))
    for f in libname:
        shutil.copy(os.path.join(src, f), dst)


class bdist_wheel(bdist_wheel_):
    def run(self):
        libname = get_libname()
        if not os.path.exists('rtree/.libs'):
            build_spatialindex(libname)
        if not os.path.exists('rtree/.libs'):
            raise RuntimeError("Unable to find shared library {lib}."
                               .format(lib=libname))
        bdist_wheel_.run(self)

    def finalize_options(self):
        bdist_wheel_.finalize_options(self)
        self.plat_name_supplied = True
        self.plat_name = get_platform()
        self.universal = False
        self.root_is_pure = False

if __name__ == "__main__":
    if os.name == 'nt':
        data_files = [('Lib/site-packages/rtree',
                      [os.environ['SPATIALINDEX_LIBRARY']
                          if 'SPATIALINDEX_LIBRARY' in os.environ else
                          r'D:\libspatialindex\bin\spatialindex.dll',
                       os.environ['SPATIALINDEX_C_LIBRARY']
                          if 'SPATIALINDEX_C_LIBRARY' in os.environ else
                          r'D:\libspatialindex\bin\spatialindex_c.dll'])]
    else:
        data_files = None

    setup(
       name='Rtree',
       version='0.8.3',
       description='R-Tree spatial index for Python GIS',
       license='LGPL',
       keywords='gis spatial index r-tree',
       author='Sean Gillies',
       author_email='sean.gillies@gmail.com',
       maintainer='Howard Butler',
       maintainer_email='hobu@hobu.net',
       url='http://toblerity.github.com/rtree/',
       long_description=get_readme(),
       packages=['rtree'],
       include_package_data=True,
       package_data={"rtree": ['.libs/*']},
       cmdclass={'bdist_wheel': bdist_wheel},
       install_requires=['setuptools'],
       test_suite='tests.test_suite',
       data_files=data_files,
       zip_safe=False,
       classifiers=[
         'Development Status :: 5 - Production/Stable',
         'Intended Audience :: Developers',
         'Intended Audience :: Science/Research',
         'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
         'Operating System :: OS Independent',
         'Programming Language :: C',
         'Programming Language :: C++',
         'Programming Language :: Python',
         'Topic :: Scientific/Engineering :: GIS',
         'Topic :: Database',
         ],
       ext_modules=[Extension('rtree._mock_ext',
                              sources=['ext/mock.c'])]
    )
