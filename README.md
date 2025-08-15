# basically text over FM

ported from [pied-piper](https://github.com/rraval/pied-piper)

results depend on radio speaker quality, decoder mic quality, and transmitter antenna quality.

## install
```
git clone https://github.com/ChristopheJacquet/PiFmRds.git
cd PiFmRds/src
make clean
make
sudo cp pi_fm_rds /usr/local/bin/
sudo chmod +x /usr/local/bin/pi_fm_rds
```
for pi zero users that are having issues with compiling (getting issues like "expr: syntax error: unexpected argument ‘1’"):\
edit the makefile like this:
```
#RPI_VERSION := $(shell cat /proc/device-tree/model | grep -a -o "Raspberry\sPi\s[0-9]" | grep -o "[0-9]")
RPI_VERSION = 3
```
then do this again:
```
make clean
make
sudo cp pi_fm_rds /usr/local/bin/
sudo chmod +x /usr/local/bin/pi_fm_rds
```

## packages
```
pip install colorama numpy reedsolo
```


