# pyboot
bootloader umdom devices (python)

### protocol modbus RTU
```
CMD_BOOT=100
CMD_READ=101
CMD_BOOT_EXIT=102
CMD_WRITE=103
```
### py boot py -h
```
usage: boot.py [-h] [-a ADR] [-b BEGINMEMORY] [-e ENDMEMORY] (-t | -fc | -r FILETOWRITE | -v VERIFY | -p PROG) [com]

boot Flash onto umdom boards

positional arguments:
  com                   COM port, default=smalest number COM

optional arguments:
  -h, --help            show this help message and exit
  -a ADR, --adr ADR     device address 1 - 127, default=1
  -b BEGINMEMORY, --beginmemory BEGINMEMORY
                        device memory start address, default=0x08001000
  -e ENDMEMORY, --endmemory ENDMEMORY
                        device memory end address or length, default=0x08020000
  -t, --test            check device and bootloader (enter to bootloader, exit from bootloader)
  -fc, --comports       list available COM ports
  -r FILETOWRITE, --read FILETOWRITE
                        read device program to file
  -v VERIFY, --verify VERIFY
                        verify device program
  -p PROG, --prog PROG  program device
  ```
