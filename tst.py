import ctypes
pyarr = [1, 2, 3, 4]
arr = (ctypes.c_uint16 * len(pyarr))(*pyarr)
print(*pyarr, bytes(arr))

import asyncio, asyncio.futures

async def ares():
    return 42


class Awaitable(asyncio.Future):
    def __await__(self):
        if not self.done():
            print(self._state)
            self.set_result(10)
            print(self._state)
#        for _ in range(80):   
#            print('.',end='') 
#            yield from self
        return super().__await__()    
        

async def func():
    e = await Awaitable()
    print('e', e)
    return e+1

async def main():
    print('main1')
    print(await func())  
    print('main2')


import click
import time

for filename in range(3):
    with click.progressbar(range(100)) as bar:
        for user in bar:
            time.sleep(0.01)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())