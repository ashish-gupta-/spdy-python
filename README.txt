SPDY library in python. Many concepts are derived from https://github.com/colinmarc/python-spdy.

For developers
===============
python setup.py sdist
mv dist/spdylib-1.0.tar.gz req-binaries/
rm -rf MANIFEST dist

Requirements
------------
python version > 3.3
cython library version >= 0.15.1
bitarray library version >= 0.7.0
termcolor library version >= 1.1.0

Installing the scurl client
===========================
Install
-------
1. Click on the "Download ZIP" button on right hand side. put the zipped package to any location on your linux box.
2. unzip the package:-
unzip spdy-python-master.zip
cd spdy-python-master/req-binaries/

3. Install python 3.3:-
tar -zxvf Python-3.3.2.tgz
cd Python-3.3.2
./configure
make
make install
cd ..
rm -rf Python-3.3.2
python3.3 --version

4. Install cython:-
tar -zxvf Cython-0.19.1.tar.gz
cd Cython-0.19.1
python3.3 setup.py install
rm -rf Cython-0.19.1
cd ..

5. Install bitarray:-
tar -zxvf bitarray-0.8.1.tar.gz
cd bitarray-0.8.1
python3.3 setup.py install
rm -rf bitarray-0.8.1
cd ..

6. Install termcolor:-
tar -zxvf termcolor-1.1.0.tar.gz
cd termcolor-1.1.0
python3.3 setup.py install
rm -rf termcolor-1.1.0
cd ..

7. Install spdylib
tar -zxvf spdylib-1.0.tar.gz
cd spdylib-1.0
python3.3 setup.py install
cd ..

8. scurl is ready to use:-
python3.3 scurl.py -h
python3.3 scurl -v https://www.google.co.in



