from typing import Iterable, Optional, Union
from itertools import chain
import logging
import tempfile

from wrapt.decorators import synchronized

from .chunk import Location, ChunkRead, ChunkLocation


MAX_SIZE = 5 * 1_024 * 1_024  # bytes
CHUNK = 4 * 1_024  # bytes
START = 0
INDEX_SIZE = 2
STREAM_INDEX = 0

GETITEM_ERR = \
  f'Expected a collection with a length of {INDEX_SIZE} or a slice object.'


class IterableBytes:
  def __init__(self, bytes_obj: bytes, chunk: int = CHUNK, start: int = START):
    self.bytes = bytes_obj
    self.chunk = chunk
    self.start = start

  def iter(self) -> Iterable[bytes]:
    return iter(self)

  def __iter__(self) -> Iterable[bytes]:
    start: int = self.start  # just in case size is 0
    length = len(self.bytes)

    for start in range(self.start, length, self.chunk):
      window = slice(start, start + self.chunk)
      yield self.bytes[window]

    # variable start should leak from for-loop scope if len(bytes) > 0
    if start and (start + self.chunk) < length:
      window = slice(start + self.chunk, length)
      yield self.bytes[window]


Stream = Union[IterableBytes, Iterable[bytes], bytes]


class Buffer:
    stream: Stream
    size: int
    max_size: int
    stream_index: int
    temp: tempfile.SpooledTemporaryFile


class BufferLocation(Buffer, ChunkLocation):    
  def _chunk_location(self, offset: int, size: int) -> Location:
    end = offset + size

    if offset < self.stream_index and end <= self.stream_index:
      return Location.BeforeIndex
    
    elif offset < self.stream_index < end:
      return Location.Bisected
    
    elif offset == self.stream_index:
      return Location.AtIndex
    
    return Location.AfterIndex


class BufferRead(Buffer, ChunkRead):
  def _chunk_before_index(self, offset: int, size: int) -> bytes:
    self.temp.seek(offset)
    return self.temp.read(size)

  def _chunk_bisected_by_index(self, offset: int, size: int) -> bytes:
    buf = bytearray()
    
    existing_size = self.stream_index - offset
    chunk_before = self._chunk_before_index(offset, existing_size)
 
    new_size = size - len(chunk_before)
    chunk_after = self._chunk_at_index(new_size)
 
    chunks = chain(chunk_before, chunk_after)
    buf.extend(chunks)

    return bytes(buf)

  def _chunk_at_index(self, size: int) -> bytes:
    buf = bytearray()
    self.temp.seek(self.stream_index)

    for line in self.stream:
      self.stream_index += len(line)
      self.temp.write(line)
      buf.extend(line)

      if len(buf) >= size:
        return bytes(buf[:size])

    return bytes(buf)

  def _chunk_after_index(self, offset: int, size: int) -> bytes:
    buf = bytearray()
    self.temp.seek(self.stream_index)

    for line in self.stream:
      self.stream_index += len(line)
      self.temp.write(line)

      if self.stream_index >= offset:
        buf.extend(line)

      if len(buf) >= size:
        return bytes(buf[:size])
    
    return bytes(buf)


class StreamBuffer(BufferLocation, BufferRead):
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
    self.stream_index = STREAM_INDEX
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
    if isinstance(val, (tuple, list)) and len(val) == INDEX_SIZE:
      start, stop = val
      return self.read(start, stop - start)

    elif isinstance(val, slice):
      return self.read(val.start, val.stop - val.start)

    raise NotImplementedError(GETITEM_ERR)

  def is_exhausted(self) -> bool:
    try:
      item = next(self.stream)
    except StopIteration as e:
      return True

    self.stream = chain([item], self.stream)
    return False

  def read(self, offset: int, size: int) -> bytes:
    with synchronized(self):
      location = self._chunk_location(offset, size)

      if location == Location.BeforeIndex:
        return self._chunk_before_index(offset, size)

      elif location == Location.AtIndex:
        return self._chunk_at_index(size)

      elif location == Location.Bisected:
        return self._chunk_bisected_by_index(offset, size)

      elif location == Location.AfterIndex:
        return self._chunk_after_index(offset, size)
