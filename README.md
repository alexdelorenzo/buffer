# buffer

A stream buffer backed by `tempfile.SpooledTemporaryFile`. Here's an [article that goes into more detail about `buffer`](https://alexdelorenzo.dev/programming/2019/04/14/buffer).

There's a [Rust version of this library](https://github.com/alexdelorenzo/buffers-rs), too.

## About
In Python, you cannot `seek()` or `slice` into an iterable like you can with `list` and other ordered collections.

Sometimes streaming and asynchronous data transfers are modeled as iterables in Python. In the case of HTTP responses, the amount of streamed data can vary from a small amount to a relatively large amount.

When you're working with a stream, you might want to go back in the stream, or skip ahead, without losing any streaming data in the process. To do that, you'd need a caching buffer.

A buffer can exist in memory, or it can exist on persistent storage, or both. `buffer` does a mix of both. Using a set memory buffer limit, small streams can remain in memory, and longer streams can buffer on the disk. You can wrap an iterable with `buffer.StreamBuffer` and treat it like a persistent file, and not a stream.

A `StreamBuffer` object is temporary, so when you're done using it, it will automatically clean up its memory and disk caches for you. 

# Example

```python3
from typing import Iterable

from buffer import StreamBuffer
from requests import get


BIG_FILE: str = "https://releases.ubuntu.com/20.04.1/ubuntu-20.04.1-desktop-amd64.iso"
LEN_KEY: str = 'Content-Length'

KB: int = 1024
START: int = 0


with get(BIG_FILE, stream=True) as response:
  length = int(response.headers[LEN_KEY])
  stream: Iterable[bytes] = response.iter_content()

  buffer = StreamBuffer(stream, length)

  # read from start of stream
  first_kb: bytes = buffer.read(START, size=KB)
  
  # skip ahead to any arbitrary location in the stream
  arbitrary_kb = buffer.read(20 * KB, size=KB)
  
  # skip back to any arbitrary location in the stream
  first_again = buffer.read(START, size=KB)
  
  assert first_again == first_kb
```

# Installation
```bash
python3 -m pip install buffer
```
