# buffer

A stream buffer backed by `tempfile.SpooledTemporaryFile`. 

[Click here to learn more about `buffer`](https://alexdelorenzo.dev/programming/2019/04/14/buffer).

[Click here for the Rust version of this library](https://gitlab.com/thismachinechills/buffers-rs).

# Installation
```bash
python3 -m pip install buffer==0.1.0
```

# Usage

```python3
from buffer import StreamBuffer
from requests import get


BIG_FILE = "https://releases.ubuntu.com/20.04.1/ubuntu-20.04.1-desktop-amd64.iso"


with get(BIG_FILE, stream=True) as response:
  stream = response.iter_content()
  length = int(response.headers['Content-Length'])
  
  buffer = StreamBuffer(stream, length)
  chunk = buffer.read(0, 1024)
```
