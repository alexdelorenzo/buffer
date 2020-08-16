from typing import Iterable, Optional, Union
from itertools import chain
import logging
import tempfile

from wrapt.decorators import synchronized

from .chunk import Location, ChunkRead, ChunkLocation


MAX_SIZE = 5 * 1_024 * 1_024  # bytes
CHUNK = 4 * 1_024  # bytes
START = 0


class IterableBytes:
  def __init__(self, bytes_obj: bytes, chunk: int = CHUNK):
    self.bytes = bytes_obj
    self.chunk = chunk

  def get_iter(self) -> Iterable[bytes]:
    return iter(self)

  def __iter__(self) -> Iterable[bytes]:
    start: Optional[int] = None
    length = len(self.bytes)

    for start in range(START, length, CHUNK):
      window = slice(start, start + CHUNK)
      yield self.bytes[window]

    if start and (start + CHUNK) < length:
      window = slice(start + CHUNK, length)
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
    chunk_before = self._chunk_before_index(offset, size)
    chunk_after = self._chunk_at_index(size)
    buf.extend(chain(chunk_before, chunk_after))

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

    raise NotImplementedError(f"Indexing via {type(val)} is not supported. Use a slice().")

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
