from distutils.core import setup, Extension
from Cython.Distutils import build_ext

zlib_wrapper = Extension(
        'spdylib._zlib_stream', ['cython/zlib_stream.pyx'],
        libraries=['z']
        )

setup(
            name="spdylib",
            version="2.0",
            description="Spdy library for version 2 & 3",
            author="Ashish Gupta",
            author_email="ashish049@gmail.com",
            long_description="Inspired by Colin Mark's implementation at https://github.com/colinmarc/python-spdy",
            requires=['Cython (>=0.15.1)', 'bitarray (>=0.7.0)'],
            cmdclass={'build_ext': build_ext},
            ext_modules=[zlib_wrapper],
            packages=["spdylib"],
            package_dir={"spdylib":"spdylib"},
            )
