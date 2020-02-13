#!/usr/bin/env python3
import argparse 
import struct
import click
from os import path
from serial.tools.list_ports import comports

from pymodbus.pdu import ModbusRequest, ModbusResponse, ModbusExceptions
import pymodbus.framer.rtu_framer
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

# --------------------------------------------------------------------------- #
# configure the client logging
# --------------------------------------------------------------------------- #
import logging
logging.basicConfig()
log = logging.getLogger()
#log.setLevel(logging.DEBUG)

CMD_BOOT=100
CMD_READ=101
CMD_BOOT_EXIT=102
CMD_WRITE=103
MAGIC=0x12345678
MEMORY_START=0x08001000
MEMORY_END=0x08020000
PART_STD=128
BAUD=115200


class AdrAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values not in range(1, 128):
            raise ValueError('device addres %d not in 1..127' % values)
        else: 
            namespace.adr = values 

class FileExistsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        v =str(values).strip()
        if path.exists(v) and path.isfile(v):                        
            setattr(namespace, self.dest, v)
        else:
            raise ValueError('file for %s: %s not exists' % (self.dest, values))

def parse_args():

    global args

    ports = [x for (x,y,z) in sorted(comports())]

    parser = argparse.ArgumentParser(description="boot Flash onto umdom boards")
    parser.add_argument(
        'com', 
        type=str, 
        nargs='?',
        default=ports[0] if ports else None,
        help= "COM port, default=smalest number COM")
    parser.add_argument(
        '-a','--adr', 
        type=int, 
        #nargs='?',
        default=1,
        action=AdrAction, 
        help="device address 1 - 127, default=1")
    parser.add_argument(
        '-b','--beginmemory', 
        type=lambda x: int(x,0), 
        default=MEMORY_START,
        help="device memory start address, default=0x08001000")
    parser.add_argument(
        '-e','--endmemory', 
        type=lambda x: int(x,0), 
        default=MEMORY_END,
        help="device memory end address or length, default=0x08020000")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-t','--test', 
        action='store_true', 
        help="check device and bootloader (enter to bootloader, exit from bootloader)")
    group.add_argument(
        '-fc','--comports', 
        action='store_true', 
        help="list available COM ports")
    group.add_argument(
        '-r','--read', 
        metavar='FILETOWRITE', 
        type=str, 
        help="read device program to file")
    group.add_argument(
        '-v','--verify', 
        type=str, 
        action=FileExistsAction,
        help="verify device program")
    group.add_argument(
        '-p','--prog', 
        type=str, 
        action=FileExistsAction,
        help="program device")
    args = parser.parse_args()

class BootReq(ModbusRequest):
    function_code = CMD_BOOT
    _rtu_frame_size = 1+1+4+2

    def __init__(self, magic=MAGIC, **kwargs):
        ModbusRequest.__init__(self, **kwargs)
        self.magic = magic

    def encode(self):
        return struct.pack('<L', self.magic)

class BootRes(ModbusResponse):
    function_code = CMD_BOOT
    _rtu_frame_size = 1+1+4+2

    def decode(self, data):
        self.magic = struct.unpack('<L', data)[0]

class ReadReq(ModbusRequest):
    function_code = CMD_READ
    _rtu_frame_size = 1+1+4+2

    def __init__(self, memoryadr, **kwargs):
        ModbusRequest.__init__(self, **kwargs)
        self.memoryadr = memoryadr

    def encode(self):
        return struct.pack('<L', self.memoryadr)

class ReadRes(ModbusResponse):
    function_code = CMD_READ
    _rtu_frame_size = 1+1+4+PART_STD+2

    def decode(self, data):
        self.adr = struct.unpack('<L', data[0:4])[0]
        self.memory = data[4:]

class BootExitReq(ModbusRequest):
    function_code = CMD_BOOT_EXIT
    _rtu_frame_size = 1+1+2

    def encode(self):
        return b'' 

class BootExitRes(ModbusResponse):
    function_code = CMD_BOOT_EXIT
    _rtu_frame_size = 1+1+2

    def decode(self, data):
        self.exit = 1

class WriteReq(ModbusRequest):
    function_code = CMD_WRITE
    _rtu_frame_size = 1+1+4+PART_STD+2

    def __init__(self, memoryadr, data, **kwargs):
        ModbusRequest.__init__(self, **kwargs)
        self.memoryadr = memoryadr
        self.data = data

    def encode(self):
        tmp = struct.pack('<L', self.memoryadr) +  self.data
        return tmp

class WriteRes(ModbusResponse):
    function_code = CMD_WRITE
    _rtu_frame_size = 1+1+4+4+2

    def decode(self, data):
        (self.adr, self.err) = struct.unpack('<LL', data)

def main():
        
    if args.comports:   
        ports = list(sorted(comports()))     
        if ports:
            for port, desc, hwid in ports:
                print(f"{port}: {desc} [{hwid}]")
        else:
            print("COM ports not found!!!")  
    else:
        with ModbusClient(method='rtu', port=args.com, baudrate=BAUD) as client:
            client.register(BootRes)
            client.register(BootExitRes)
            client.register(ReadRes)
            client.register(WriteRes)

            def enter_boot():
                for i in range(4):
                    print(f'{i}) SEND: enter boot ')
                    request = BootReq(unit=args.adr)
                    result = client.execute(request)
                    if isinstance(result, BootRes) and (result.magic == request.magic): 
                        print(f'{i}) READ: magic ok! in boot')
                        break
                else:
                    raise Exception('Can`t enter bootloader !!!')

            def exit_boot():
                for i in range(4):
                    print(f'{i}) SEND: exit boot')
                    result = client.execute(BootExitReq(unit=args.adr))
                    if isinstance(result, BootExitRes): 
                        print(f'{i}) READ: in program')
                        break
                else:
                    raise Exception('Can`t enter program !!!')

            def loadFile(name)->bytearray:
                with open(name,'rb') as f:
                    p = bytearray(f.read())
                    # correct size
                    r = len(p) % PART_STD
                    if r:
                        p.extend(b'\0'*(PART_STD-r))
                return p

            if args.test:
            #==========================================================================================
                enter_boot()
                exit_boot()
            elif args.read:                    
            #==========================================================================================
                enter_boot()
                try:
                    if args.endmemory < 0x08000000: 
                        args.endmemory += args.beginmemory
                    print(f'write: {args.read} from {args.beginmemory:x} to {args.endmemory:x} ')
                    with open(args.read,'wb') as f:
                        with click.progressbar(range(args.beginmemory, args.endmemory, PART_STD)) as bar:
                            for ma in bar:
                                request = ReadReq(ma, unit=args.adr)
                                result = client.execute(request)
                                f.write(result.memory)
                    print(f'close: {args.read}')
                finally:
                    exit_boot()
            elif args.verify:                    
            #==========================================================================================
                enter_boot()
                try:
                    p = loadFile(args.verify)
                    print(f'verify file: {args.verify} from {args.beginmemory:x} to {args.beginmemory+len(p):x}')
                    errcnt=0
                    fileidx=0
                    with click.progressbar(range(0, len(p), PART_STD)) as bar:
                        for ma in bar:
                            if errcnt > 15:
                                break
                            request = ReadReq(args.beginmemory+ma, unit=args.adr)
                            result = client.execute(request)
                            for i in range(PART_STD):
                                if p[fileidx] != result.memory[i]:
                                    errcnt += 1
                                    ea = args.beginmemory+ma+i
                                    print(f'\n{errcnt}: adr: {ea:x}-{fileidx:<20x} file|mem: {p[fileidx]:<3x}<> {result.memory[i]:<3x}')
                                    if errcnt > 15:
                                        break
                                fileidx += 1
                    a = 'OK' if errcnt == 0 else 'BAD'
                    print(f'verify {a}')
                finally:
                    exit_boot()
            elif args.prog:
            #==========================================================================================
                enter_boot()
                errcnt=0
                try:
                    p = loadFile(args.prog)
                    print(f'==== program flash: {args.prog} from {args.beginmemory:x} to {args.beginmemory+len(p):x}  ====')
                    # check file
                    (stak, enter) = struct.unpack('<LL', p[0:8])
                    if not ((stak & 0xFFFF0000 == 0x20000000) and (enter & 0xFFF00000 == 0x08000000)):
                        raise Exception(f'bad file data: stack: {stak:x} prog enter: {enter:x}')
                    # start
                    with click.progressbar(range(0, len(p), PART_STD)) as bar:
                        for ma in bar:
                            if errcnt > 0:
                                break
                            for i in range(5):
                                request = WriteReq(args.beginmemory+ma, p[ma:ma+PART_STD], unit=args.adr)
                                result = client.execute(request)
                                if isinstance(result, WriteRes) and ((result.err == 0xFFFFFFFF) or (result.err == 0xFFFFFFFE)):
                                    break
                                else:
                                    errcnt += 1
                                    err = 0 or result.err
                                    print(f'\n{i}) err at adr: {err:x}')                                
                    a = 'OK' if errcnt == 0 else 'BAD'
                    print(f'programm {a}')
                finally:
                    if not errcnt: 
                        exit_boot()

if __name__ == "__main__":
    parse_args()
    print(args.com, args.adr, hex(args.beginmemory), hex(args.endmemory), args.test, args.verify, args.read, args.prog)
    main()