# spoon
🥄 一个勺子

## 简介
学习Flask v0.1源码的产物，先理解，然后尝试自己写出来。工具类有Werkzeug提供, 如路由，Session, 静态文件托管中间件等。
Werkzeug的Local实现很巧妙，我照着它的设计也写了一个。模板由jinja2提供。

## 依赖
Werkzeug>=0.6.1
Jinja2>=2,4

## 使用
``` python
from spoon import Spoon

app = Spoon(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
```
