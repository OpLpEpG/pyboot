# pyboot
bootloader umdom devices (python)

protocol modbus RTU
```
usage: boot.py [-h] [-a ADR] (-t | -fc | -r FILETOWRITE | -v VERIFY | -p PROG) [com]

boot Flash onto umdom boards

positional arguments:
  com                   you mast select COM port, default=smalest number COM

optional arguments:
  -h, --help            show this help message and exit
  -a ADR, --adr ADR     you mast select device address 1 - 127, default=1
  -t, --test            check device and bootloader (enter to bootloader, exit from
                        bootloader)
  -fc, --comports       list available COM ports
  -r FILETOWRITE, --read FILETOWRITE
                        read device program to file
  -v VERIFY, --verify VERIFY
                        verivy device program
  -p PROG, --prog PROG  program device
  ```
