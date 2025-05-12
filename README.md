### 介绍
这是一个Http请求处理模块，支持链式请求发送，方便的处理http请求。
### 使用
- 基本请求发送
```python
# 请求一个地址
Api('https://www.baidu.com').send()
# url参数
Api('https://www.baidu.com').query({'key':'val'}).send()
# 修改请求方法
Api('https://www.baidu.com').method('post').send()
# 修改参数
Api('https://www.baidu.com').body({'key':'val'}).method('post').send()
# 打印响应
Api('https://www.baidu.com').send_and_print()
```
### 链式请求发送
一些请求有先后顺序和依赖关系，例如OAUTH流程或解析某页面中的媒体元素然后下载。链式请求可以让这种
逻辑组织在一起，一个请求的参数可能要依赖上一个请求的结果
```python
# 编写API对象
def baidu_callback(resp, api_result):
    print(
        f'this http resp is {resp}, prev http res is {api_result.get_resp()}, callback result is {api_result.get_callback_result()}')
    return {'baidu': 'baidu result'}

def souhu_callback(resp, api_result):
    print(
        f'this http resp is {resp}, http res is {api_result.get_resp()}, callback result is {api_result.get_callback_result()}')
    return {'souhu': 'souhu result'}
baidu_api = Api('http://www.baidu.com').callback(baidu_callback)
souhu_api = Api('https://www.sohu.com/').callback(souhu_callback)
# 组织发送顺序
baidu_api.then(souhu_api).send()
```
- 返回结果
```python
# 返回结果是一个ApiResult对象，包含两部分，Response对象和Callback结果对象
```