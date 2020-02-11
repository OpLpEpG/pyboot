import ctypes
pyarr = [1, 2, 3, 4]
arr = (ctypes.c_uint16 * len(pyarr))(*pyarr)
print(*pyarr, bytes(arr))

class FromCount