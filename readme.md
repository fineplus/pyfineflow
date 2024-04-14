# pyfineflow

> fineflow的python节点后端

## usage

### install

```shell
pip install pyfineflow
```

### make a demo

create dir and files like this：

- pyfineflow-demo/
  - main.py
  - app.py
  - math_nodes.py

```python
# app.py
from pyfineflow.core import Fine
fine = Fine('pyserver', 'python后端')
```

```python
# math_nodes.py
import time
from datetime import datetime
from pathlib import Path
from pyfineflow.core import get_ctx
from app import fine


@fine.node(category='数学运算', name="相加")
def add(num1: int, num2: int) -> int:
    num = num2 + num1
    return num


@fine.node(category='数学运算', name="相减")
def sub(num1: int, num2: int = 2) -> int:
    num = num1 - num2
    return num


@fine.node(category='数学运算')
def 原路返回(num1: int, num2: int = 2) -> (int, int):
    return num1, num2
```

```python
# main.py
from app import fine


def init():
    import math_nodes
    _ = math_nodes


init()
fine.init_server(port=8081)

```

run it:

```shell
python main.py
```
