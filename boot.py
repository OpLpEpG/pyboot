#!/usr/bin/env python3
'''
boot com_port adr -t,p,v,r file
'''
import argparse 
import sys
import asyncio 
from os import path
from serial import Serial, threaded
from serial.tools.list_ports import comports
import threading

from pymodbus.pdu import ModbusRequest, ModbusResponse, ModbusExceptions
import pymodbus.framer.rtu_framer
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import struct

# --------------------------------------------------------------------------- #
# configure the client logging
# --------------------------------------------------------------------------- #
import logging
logging.basicConfig()
log = logging.getLogger()
#log.setLevel(logging.DEBUG)

class _AdrAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values not in range(1, 128):
            raise ValueError('device addres %d not in 1..127' % values)
        else: 
            namespace.adr = values 

class _FileExistsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if path.exists(values) and path.isfile(values):                        
            setattr(namespace, self.dest, values)
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
        help= "you mast select COM port, default=smalest number COM")
    parser.add_argument(
        '-a','--adr', 
        type=int, 
        #nargs='?',
        default=1,
        action=_AdrAction, 
        help="you mast select device address 1 - 127, default=1")
    parser.add_argument(
        '-b','--beginmemory', 
        type=lambda x: int(x,0), 
        default=Commands.MEMORY_START,
        help="you mast select device memory start address, default=0x08001000")
    parser.add_argument(
        '-e','--endmemory', 
        type=lambda x: int(x,0), 
        default=Commands.MEMORY_END,
        help="you mast select device end address or length, default=0x08020000")
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
        action=_FileExistsAction,
        help="verivy device program")
    group.add_argument(
        '-p','--prog', 
        type=str, 
        action=_FileExistsAction,
        help="program device")
    args = parser.parse_args()

class Commands():
    CMD_BOOT=100
    CMD_READ=101
    CMD_BOOT_EXIT=102
    CMD_WRITE=103
    MAGIC=0x12345678
    MEMORY_START=0x08001000
    MEMORY_END=0x08020000
    PART_STD=128

class BootReq(ModbusRequest):
    function_code = Commands.CMD_BOOT
    _rtu_frame_size = 1+1+4+2

    def __init__(self, magic=Commands.MAGIC, **kwargs):
        ModbusRequest.__init__(self, **kwargs)
        self.magic = magic

    def encode(self):
        return struct.pack('<L', self.magic)

class BootRes(ModbusResponse):
    function_code = Commands.CMD_BOOT
    _rtu_frame_size = 1+1+4+2

    def decode(self, data):
        self.magic = struct.unpack('<L', data)

class ReadReq(ModbusRequest):
    function_code = Commands.CMD_READ
    _rtu_frame_size = 1+1+4+2

    def __init__(self, memoryadr, **kwargs):
        ModbusRequest.__init__(self, **kwargs)
        self.memoryadr = memoryadr

    def encode(self):
        return struct.pack('<L', self.memoryadr)

class ReadRes(ModbusResponse):
    function_code = Commands.CMD_READ
    _rtu_frame_size = 1+1+4+Commands.PART_STD+2

    def decode(self, data):
        self.adr = struct.unpack('<L', data[0:4])
        self.memory = data[4:]


<<<<<<< HEAD
=======
class _PacketModbusRTU(threaded.Protocol):    

    def __init__(self):
        self.buffer = bytearray()
        self.transport = None
        self.adr=None
        self._current_command=None
        self.lock = threading.Lock()
        self.read_event = threading.Event()

    def connection_made(self, transport):
        """Store transport"""
        self.transport = transport
        self.adr = transport.serial.adr 
       # print('transport: ', self.transport.__class__)

    def connection_lost(self, exc):
        """Forget transport"""
        #print('lost: ', self.transport)
        self.transport = None
        super(_PacketModbusRTU, self).connection_lost(exc)


    def tobytearray(self, data: int, byteslen=0, byteorder = 'little')->bytearray:
        b = byteslen or (data.bit_length()+7)//8
        return bytearray(data.to_bytes(b, byteorder))

    def words2bytes(self, words: list, byteorder = 'big')->bytearray:
        '''
        big endian Modbus word data
        '''
        res = bytearray()
        for n in words:
            res.extend(self.tobytearray(n, byteslen=2, byteorder=byteorder))
        return res        

    def crc16(self, data: bytearray):
        '''
        CRC-16-ModBus Algorithm
        '''
        poly = 0xA001
        crc = 0xFFFF
        for b in data:
            crc ^= (0xFF & b)
            for _ in range(0, 8):
                if (crc & 0x0001):
                    crc = ((crc >> 1) & 0xFFFF) ^ poly
                else:
                    crc = ((crc >> 1) & 0xFFFF)
        return  crc

    def data_received(self, data):
        """Buffer received data, find TERMINATOR, call handle_packet"""
        if self.adr and self._current_command:
            with self.lock:
                self.buffer.extend(data)
                if ((len(self.buffer) > 3) 
                and (self.buffer[0] == self.adr) 
                and (self.buffer[1] == self._current_command) 
                and (self.crc16(self.buffer) == 0)):
                    self._current_command = None
                    self.read_event.set()        
        #print(self.buffer.hex(','))
        print(data)

    def command(self, command, data=None, timout=2.097152):
        indata = bytearray([self.transport.serial.adr, command])
        if type(data) is int:
            indata.extend(self.tobytearray(data))
        elif type(data) in [bytearray, bytes, str]:
            indata.extend(data)
        elif type(data) is list:
            indata.extend(self.words2bytes(data))
        else:
            indata.extend(bytearray(data))
        indata.extend(self.tobytearray(self.crc16(indata)))
        print(indata.hex(',')) 
        with self.lock:
            self.buffer.clear()
            self._current_command = command
        self.transport.write(indata)
        return self.buffer.copy() if self.read_event.wait(timout) else None
>>>>>>> 3cb6cc33b90369fbb43533c84d07951939a8629d

def main():
        
    if args.comports:   
        ports = list(sorted(comports()))     
        if ports:
            for port, desc, hwid in ports:
                print(f"{port}: {desc} [{hwid}]")
        else:
            print("COM ports not found!!!")  
    else:
        BAUD=115200
        with ModbusClient(method='rtu', port=args.com, baudrate=BAUD) as client:
            client.register(BootRes)
            client.register(ReadRes)
            if args.test:
<<<<<<< HEAD
                request = BootReq(unit=args.adr)
                result = client.execute(request)
                if isinstance(result, BootRes):
                    print(f'return magic: 0x{result.magic[0]:x}')
            if args.read:                    
                if args.endmemory < 0x08000000: 
                    args.endmemory += args.beginmemory
                ma = args.beginmemory
                print(f'write: {args.read}')
                with open(args.read,'wb') as memoryfile:
                    while ma < args.endmemory:
                        request = ReadReq(ma, unit=args.adr)
                        result = client.execute(request)
                        memoryfile.write(result.memory)
                        ma += Commands.PART_STD
                        print('.',end='')
                print(f'\nclose: {args.read}')
                    

=======
#                MAGIC = 0x12345678 
#                modbus.command(0xF8, MAGIC)
                res = modbus.command(3,[0,0xA])
                print('result:',res)
        #print(com)
>>>>>>> 3cb6cc33b90369fbb43533c84d07951939a8629d

    

if __name__ == "__main__":
    parse_args()
    print(args.com, args.adr, args.beginmemory, args.endmemory, args.test, args.verify, args.read, args.prog)
    main()