from typing import Iterable, Optional, Union
from itertools import chain
import logging
import tempfile

from wrapt.decorators import synchronized


MAX_SIZE = 5 * 1_024 * 1_024
CHUNK = 4 * 1_024  # bytes
START = 0


class IterableBytes:
  def __init__(self, bytes_obj: bytes, chunk: int = CHUNK):
    self.bytes = bytes_obj
    self.chunk = chunk

  def __iter__(self) -> Iterable[bytes]:
    start: Optional[int] = None
    length = len(self.bytes)

    for start in range(START, length, CHUNK):
      window = slice(start, start + CHUNK)
      yield self.bytes[window]

    if start and (start + CHUNK) < length:
      window = slice(start + CHUNK, length)
      yield self.bytes[window]


   def get_iter(self) -> Iterable[bytes]:
       return iter(self)


Stream = Union[IterableBytes, Iterable[bytes], bytes]


class StreamBuffer:
    def __init__(self, 
                 stream: Stream,
                 size: int, 
                 max_size: int = MAX_SIZE):

        if isinstance(stream, bytes):
            stream = IterableBytes(stream)

        if isinstance(stream, IterableBytes):
            stream = iter(stream)

        self.stream = stream
        self.size = size
        self.stream_index = 0 
        self.temp = tempfile.SpooledTemporaryFile(max_size=max_size)
    
    def __del__(self):
        logging.debug(f'Releasing {self}')
        self.temp.close()
    
    def __repr__(self):
        name = StreamBuffer.__name__
        size = self.size
        stream_index = self.stream_index
        temp = self.temp
        
        return f'{name}<{size}, {stream_index}, {temp}>'
    
    def __getitem__(self, val) -> bytes:
        if isinstance(val, (tuple, list)):
            start, stop = val
            return self.read(start, stop - start)
        
        elif isinstance(val, slice):
            return self.read(val.start, val.stop - val.start)
        
        raise NotImplementedError()
        
    def is_exhausted(self) -> bool:
        try:
            item = next(self.stream)
        except StopIteration as e:
            return True
        
        self.stream = chain([item], self.stream)
        return False
    
    def read(self, offset: int, size: int) -> bytes:
        end = offset + size
        buf = bytearray()
        
        with synchronized(self):
            if offset < self.stream_index and end <= self.stream_index:
                self.temp.seek(offset)
                return self.temp.read(size)

            elif offset < self.stream_index < end:
                self.temp.seek(offset)
                return self.temp.read(end)        

            elif offset == self.stream_index:
                self.temp.seek(offset)
                for line in self.stream:
                    self.stream_index += len(line)
                    self.temp.write(line)
                    buf.extend(line)

                    if len(buf) >= size:
                        return bytes(buf[:size])
                
#                 if self.is_exhausted():
#                     self.size = self.stream_index 
                    
                return bytes(buf)

            elif self.stream_index < offset <= self.size: # and not self.is_exhausted():
                self.temp.seek(self.stream_index)

                for line in self.stream:
                    self.stream_index += len(line)
                    self.temp.write(line)

                    if self.stream_index >= offset:
                        buf.extend(line)

                    if len(buf) >= size:
                        return bytes(buf[:size])

#                 if self.is_exhausted():
#                     self.size = self.stream_index 
                    
                return bytes(buf)
            
#             elif self.is_exhausted() and offset >= self.stream_index:
#                 offset = self.stream_index - size
#                 self.temp.seek(offset)
#                 return self.temp.read(end)  
                

