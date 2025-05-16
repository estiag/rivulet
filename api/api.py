"""
API请求处理模块

提供了一套完整的API请求构建、发送和处理链式调用的功能。
包含ApiResult、Proxy、Env和Api四个主要类。
"""

import json

from bs4 import BeautifulSoup
from requests import Response

import time
from typing import Callable
from urllib.parse import urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor
import requests
import api.json_util as json_util


class ApiResult:
    """API请求结果封装类

    用于封装HTTP响应和回调函数处理结果。

    Attributes:
        __resp: 存储HTTP响应对象
        __callback_result: 存储回调函数处理结果
    """

    def __init__(self, resp, callback_result):
        """初始化ApiResult

        Args:
            resp: requests.Response对象或None
            callback_result: 回调函数处理结果或None
        """
        self.__resp = resp
        self.__callback_result = callback_result

    def get_resp(self):
        """获取HTTP响应对象

        Returns:
            requests.Response对象或None
        """
        return self.__resp

    def get_callback_result(self):
        """获取回调函数处理结果

        Returns:
            回调函数处理结果或None
        """
        return self.__callback_result

    def resp(self, resp):
        """设置HTTP响应对象

        Args:
            resp: requests.Response对象

        Returns:
            self: 支持链式调用
        """
        self.__resp = resp
        return self

    def callback_result(self, callback_result):
        """设置回调函数处理结果

        Args:
            callback_result: 回调函数处理结果

        Returns:
            self: 支持链式调用
        """
        self.__callback_result = callback_result
        return self


class Proxy:
    """代理服务器配置类

    Attributes:
        host: 代理服务器主机名
        port: 代理服务器端口
        protocol: 代理协议(http/https)
    """

    def __init__(self, host='localhost', port=None, protocol='http'):
        """初始化代理配置

        Args:
            host: 代理主机，默认为'localhost'
            port: 代理端口，默认为None
            protocol: 代理协议，默认为'http'
        """
        self.host = host
        self.port = port
        self.protocol = protocol


class Env:
    """API环境配置类

    Attributes:
        host: API主机名
        port: API端口
        protocol: API协议(http/https)
    """

    def __init__(self, host='localhost', port=None, protocol='http'):
        """初始化环境配置

        Args:
            host: API主机，默认为'localhost'
            port: API端口，默认为None
            protocol: API协议，默认为'http'
        """
        self.host = host
        self.port = port
        self.protocol = protocol

    def get_env(self):
        """获取完整的环境URL

        Returns:
            str: 格式为'{protocol}://{host}:{port}'的URL字符串
        """
        host = self.host
        if self.port:
            host = f'{host}:{self.port}'
        return f'{self.protocol}://{host}'


class Api:
    """API请求构建和发送类

    提供链式API构建方式，支持请求链、并行请求等功能。
    """

    def __init__(self, url=None, env=None, path=None, port=None, host=None, protocol=None, method=None,
                 query=None, fragment=None, headers=None, verify=True, proxy=None, body=None, cookie=None,
                 stream=None, callback=None, before_send=None):
        """初始化API请求

        Args:
            url: 完整API URL，可以是字符串或Env对象
            env: Env对象，提供主机、端口和协议
            path: API路径
            port: API端口
            host: API主机
            protocol: API协议(http/https)
            method: HTTP方法(get/post等)
            query: 查询参数
            fragment: URL片段
            headers: HTTP头
            verify: SSL验证开关
            proxy: 代理配置
            body: 请求体
            cookie: Cookie
            stream: 是否流式响应
            callback: 响应回调函数
            before_send: 发送前回调函数
        """
        # 初始化基本属性
        self.__port = None
        self.__host = ''
        self.__protocol = 'http'
        self.__method = 'get'
        self.__path = ''  # path优先级比url高，会覆盖url中的path
        self.__query = ''
        self.__fragment = ''
        self.__headers = {'Content-Type': 'application/json'}
        self.__verify = True
        self.__env = None
        self.__proxy = None
        self.__body = None
        self.__cookie = None
        self.__stream = False

        # 初始化可调用属性
        self.__callable_port = None
        self.__callable_host = None
        self.__callable_protocol = None
        self.__callable_method = None
        self.__callable_path = None
        self.__callable_query = None
        self.__callable_fragment = None
        self.__callable_headers = None
        self.__callable_verify = None
        self.__callable_env = None
        self.__callable_proxy = None
        self.__callable_body = None
        self.__callable_cookie = None
        self.__callable_stream = None
        self.__callable_url = None

        # 初始化请求链相关属性
        self.__next_api = None
        self.__next_api_list = None
        self.__callback = None
        self.__before_send = None
        self.__prev_result = None
        self.__count_sent = None
        self.__interval = None
        self.__count_request = None

        # 根据参数初始化属性
        if isinstance(url, Env):
            self.env(url)
        else:
            self.url(url)
            self.env(env)
        self.path(path)
        self.port(port)
        self.host(host)
        self.protocol(protocol)
        self.method(method)
        self.query(query)
        self.fragment(fragment)
        self.headers(headers)
        self.verify(verify)
        self.proxy(proxy)
        self.body(body)
        self.cookie(cookie)
        self.stream(stream)
        self.callback(callback)
        self.before_send(before_send)

    def __get_value_ignore_case(self, dictionary, key):
        """忽略大小写从字典中获取值

        Args:
            dictionary: 要查找的字典
            key: 查找的键

        Returns:
            匹配的值或None
        """
        for k, v in dictionary.items():
            if k.lower() == key.lower():
                return v
        return None

    def before_send(self, before_send: Callable[[ApiResult, object], object]):
        """设置请求发送前的回调函数

        Args:
            before_send: 回调函数，接收两个参数(上一步结果，本Api对象)

        Returns:
            self: 支持链式调用
        """
        if before_send:
            self.__before_send = before_send
        return self

    def get_before_send(self):
        """获取before_send属性

        Returns:
            Callable: 请求发送前的回调函数
        """
        return self.__before_send

    def callback(self, callback: Callable[[requests.Response, ApiResult], object]):
        """设置请求完成后的回调函数

        Args:
            callback: 回调函数，接收两个参数(本次http响应、上一步的结果)
                     如果有后续请求链并且后续请求依赖之前请求结果，需要返回处理结果

        Returns:
            self: 支持链式调用
        """
        if callback:
            self.__callback = callback
        return self

    def get_callback(self):
        """获取callback属性

        Returns:
            Callable: 请求完成后的回调函数
        """
        return self.__callback

    def prev_result(self, prev_result):
        """设置上一步请求的结果

        Args:
            prev_result: 上一步请求的结果

        Returns:
            self: 支持链式调用
        """
        if prev_result:
            self.__prev_result = prev_result
        return self

    def get_prev_result(self):
        """获取上一步请求的结果

        Returns:
            ApiResult: 上一步请求的结果
        """
        return self.__prev_result

    def next_api(self, next_api):
        """设置下一个要请求的API对象

        Args:
            next_api: 下一个要请求的Api对象

        Returns:
            self: 支持链式调用
        """
        if next_api:
            self.__next_api = next_api
        return self

    def get_next_api(self):
        """获取下一个要请求的API对象

        Returns:
            Api: 下一个要请求的Api对象
        """
        return self.__next_api

    def next_api_list(self, next_api_list):
        """设置下一步要请求的API对象数组

        Args:
            next_api_list: Api对象数组

        Returns:
            self: 支持链式调用
        """
        if next_api_list:
            self.__next_api_list = next_api_list
        return self

    def get_next_api_list(self):
        """获取下一步要请求的API对象数组

        Returns:
            list: Api对象数组
        """
        return self.__next_api_list

    def stream(self, stream):
        """设置是否为流式响应

        Args:
            stream: Bool/Function 如果是function则会在请求时动态解析

        Returns:
            self: 支持链式调用
        """
        if stream:
            if callable(stream):
                self.__callable_stream = stream
            else:
                self.__stream = stream
        return self

    def get_stream(self):
        """获取流式响应设置

        Returns:
            bool: 是否为流式响应
        """
        return self.__stream

    def cookie(self, cookie):
        """设置Cookie

        Args:
            cookie: Cookie值或返回Cookie的函数

        Returns:
            self: 支持链式调用
        """
        if cookie:
            if callable(cookie):
                self.__callable_cookie = cookie
            else:
                self.__cookie = cookie
        return self

    def get_cookie(self):
        """获取Cookie

        Returns:
            dict: Cookie字典
        """
        return self.__cookie

    def body(self, body):
        """设置请求体

        Args:
            body: 请求体或返回请求体的函数

        Returns:
            self: 支持链式调用
        """
        if body:
            if callable(body):
                self.__callable_body = body
            else:
                self.__body = body
        return self

    def get_body(self):
        """获取请求体

        Returns:
            str/dict: 请求体内容
        """
        return self.__body

    def proxy(self, proxy):
        """设置代理

        Args:
            proxy: Proxy对象或返回Proxy对象的函数

        Returns:
            self: 支持链式调用
        """
        if proxy:
            if callable(proxy):
                self.__callable_proxy = proxy
            else:
                self.__proxy = proxy
        return self

    def get_proxy(self):
        """获取代理配置

        Returns:
            dict: 包含http和https代理的字典或None
        """
        if self.__proxy:
            return {
                'http': f'http://{self.__proxy.host}:{self.__proxy.port}',
                'https': f'http://{self.__proxy.host}:{self.__proxy.port}'
            }
        else:
            return None

    def port(self, port):
        """设置端口

        Args:
            port: 端口号或返回端口号的函数

        Returns:
            self: 支持链式调用
        """
        if port:
            if callable(port):
                self.__callable_port = port
            else:
                self.__port = port
        return self

    def get_port(self):
        """获取端口

        Returns:
            int: 端口号
        """
        return self.__port

    def host(self, host):
        """设置主机

        Args:
            host: 主机名或返回主机名的函数

        Returns:
            self: 支持链式调用
        """
        if host:
            if callable(host):
                self.__callable_host = host
            else:
                self.__host = host
        return self

    def get_host(self):
        """获取主机

        Returns:
            str: 主机名
        """
        return self.__host

    def protocol(self, protocol):
        """设置协议

        Args:
            protocol: 协议(http/https)或返回协议的函数

        Returns:
            self: 支持链式调用
        """
        if protocol:
            if callable(protocol):
                self.__callable_protocol = protocol
            else:
                self.__protocol = protocol
        return self

    def get_protocol(self):
        """获取协议

        Returns:
            str: 协议(http/https)
        """
        return self.__protocol

    def url(self, url):
        """设置完整URL

        解析URL并设置协议、主机、端口、路径等属性

        Args:
            url: 完整URL或返回URL的函数

        Returns:
            self: 支持链式调用
        """
        if url:
            if callable(url):
                self.__callable_url = url
            else:
                parsed_url = urlparse(url)
                self.__protocol = parsed_url.scheme
                self.__host = parsed_url.hostname
                self.__port = parsed_url.port
                self.__path = parsed_url.path
                self.__query = parsed_url.query
                self.__fragment = parsed_url.fragment
        return self

    def get_url(self):
        """获取完整URL

        Returns:
            str: 完整URL或None
        """
        if not self.get_host():
            return None
        host = self.get_host()
        if self.get_port():
            host = f'{host}:{self.get_port()}'
        data = [self.get_protocol(), host, self.get_path(), '', self.get_query(),
                self.get_fragment()]
        return urlunparse(data)

    def method(self, method):
        """设置HTTP方法

        Args:
            method: HTTP方法(get/post等)或返回方法的函数

        Returns:
            self: 支持链式调用
        """
        if method:
            if callable(method):
                self.__callable_method = method
            else:
                self.__method = method
        return self

    def get_method(self):
        """获取HTTP方法

        Returns:
            str: HTTP方法
        """
        return self.__method

    def path(self, path):
        """设置路径

        Args:
            path: 路径或返回路径的函数

        Returns:
            self: 支持链式调用
        """
        if path:
            if callable(path):
                self.__callable_path = path
            else:
                self.__path = path
        return self

    def get_path(self):
        """获取路径

        Returns:
            str: 路径
        """
        return self.__path

    def fragment(self, fragment):
        """设置URL片段

        Args:
            fragment: URL片段或返回片段的函数

        Returns:
            self: 支持链式调用
        """
        if fragment:
            if callable(fragment):
                self.__callable_fragment = fragment
            else:
                self.__fragment = fragment
        return self

    def get_fragment(self):
        """获取URL片段

        Returns:
            str: URL片段
        """
        return self.__fragment

    def headers(self, headers):
        """设置HTTP头

        Args:
            headers: HTTP头字典或返回字典的函数

        Returns:
            self: 支持链式调用
        """
        if headers:
            if callable(headers):
                self.__callable_headers = headers
            else:
                self.__headers.update(headers)
        return self

    def get_headers(self):
        """获取HTTP头

        Returns:
            dict: HTTP头字典
        """
        return self.__headers

    def query(self, query):
        """设置查询参数

        Args:
            query: 查询参数字符串/字典或返回查询参数的函数

        Returns:
            self: 支持链式调用
        """
        if query:
            if callable(query):
                self.__callable_query = query
            else:
                if isinstance(query, dict):
                    temp_query_arr = []
                    for key in query:
                        temp_query_arr.append(f'{key}={query.get(key)}')
                    self.__query = '&'.join(temp_query_arr)
                else:
                    self.__query = query
        return self

    def get_query(self):
        """获取查询参数

        Returns:
            str: 查询参数字符串
        """
        return self.__query

    def verify(self, verify):
        """设置SSL验证开关

        Args:
            verify: 布尔值或返回布尔值的函数

        Returns:
            self: 支持链式调用
        """
        if isinstance(verify, bool):
            if callable(verify):
                self.__callable_verify = verify
            else:
                self.__verify = verify
        return self

    def get_verify(self):
        """获取SSL验证开关

        Returns:
            bool: 是否验证SSL证书
        """
        return self.__verify

    def env(self, env):
        """设置环境配置

        Args:
            env: Env对象或返回Env对象的函数

        Returns:
            self: 支持链式调用
        """
        if env:
            if isinstance(env, Env):
                self.port(env.port)
                self.host(env.host)
                self.protocol(env.protocol)
            if callable(env):
                self.__callable_env = env
        return self

    def get_env(self):
        """获取环境配置

        Returns:
            Env: 环境配置对象
        """
        return self.__env

    def get_desc(self):
        """获取API描述信息

        Returns:
            dict: 包含url、method、header等信息的字典
        """
        return {
            'url': self.get_url(),
            'method': self.get_method(),
            'header': self.get_headers(),
            'verify': self.get_verify(),
            'proxy': self.get_proxy()
        }

    def set_attr(self):
        """动态设置属性

        如果属性被设置为函数，则调用函数获取实际值
        """
        if callable(self.__callable_url):
            self.url(self.__callable_url(self.get_prev_result()))
        if callable(self.__callable_port):
            self.port(self.__callable_port(self.get_prev_result()))
        if callable(self.__callable_host):
            self.host(self.__callable_host(self.get_prev_result()))
        if callable(self.__callable_protocol):
            self.protocol(self.__callable_protocol(self.get_prev_result()))
        if callable(self.__callable_method):
            self.method(self.__callable_method(self.get_prev_result()))
        if callable(self.__callable_path):
            self.path(self.__callable_path(self.get_prev_result()))
        if callable(self.__callable_query):
            self.query(self.__callable_query(self.get_prev_result()))
        if callable(self.__callable_fragment):
            self.fragment(self.__callable_fragment(self.get_prev_result()))
        if callable(self.__callable_headers):
            self.headers(self.__callable_headers(self.get_prev_result()))
        if callable(self.__callable_verify):
            self.verify(self.__callable_verify(self.get_prev_result()))
        if callable(self.__callable_env):
            self.env(self.__callable_env(self.get_prev_result()))
        if callable(self.__callable_proxy):
            self.proxy(self.__callable_proxy(self.get_prev_result()))
        if callable(self.__callable_body):
            self.body(self.__callable_body(self.get_prev_result()))
        if callable(self.__callable_cookie):
            self.cookie(self.__callable_cookie(self.get_prev_result()))
        if callable(self.__callable_stream):
            self.stream(self.__callable_stream(self.get_prev_result()))

    def send_and_get_json(self):
        """发送请求并返回JSON响应

        Returns:
            dict: 响应的JSON内容
        """
        return self.send().get_resp().json()

    def send_and_print(self):
        """发送请求并打印响应

        尝试以JSON、HTML或纯文本格式美化输出

        Returns:
            ApiResult: 请求结果对象
        """
        api_result = self.send()
        try:
            print(json_util.format_json(api_result.get_resp().text))
            return api_result
        except Exception:
            pass
        try:
            api_result.get_resp().encoding = "utf-8"
            soup = BeautifulSoup(api_result.get_resp().text, features="html.parser")
            print(soup.prettify())
            return api_result
        except Exception:
            pass
        print(api_result.get_resp().text)
        return api_result

    def send(self):
        """发送API请求

        处理请求链、回调函数等逻辑

        Returns:
            ApiResult: 请求结果对象
        """
        # 执行发送前回调
        if self.get_before_send():
            self.get_before_send()(self.get_prev_result(), self)

        # 动态设置属性
        self.set_attr()

        this_result = ApiResult(None, None)
        resp = None

        # 发送请求
        if self.get_url():
            print(f'{self.get_method()} {self.get_url()}')

            # 处理请求体和Content-Type
            if self.get_headers() and self.__get_value_ignore_case(self.get_headers(), 'Content-Type'):
                if self.get_body() and 'application/json' in self.__get_value_ignore_case(self.get_headers(),
                                                                                          'Content-Type'):
                    self.body(json.dumps(self.get_body()))

            # 发送实际请求
            resp = requests.request(
                method=self.get_method(),
                url=self.get_url(),
                headers=self.get_headers(),
                data=self.get_body(),
                verify=self.get_verify(),
                cookies=self.get_cookie(),
                proxies=self.get_proxy(),
                stream=self.get_stream()
            )
            this_result.resp(resp)

        # 执行回调函数
        # 如果有callback就执行它然后把结果暂存在自己这
        if self.get_callback():
            prev_result = self.get_prev_result() or this_result
            this_callback_result = this_result.callback_result(self.get_callback()(resp, prev_result))
            this_result.callback_result(this_callback_result.get_callback_result())

        # 处理并行请求链
        # 如果next_request_list有值需要把自己的ApiResult给next_request_list中的每个Api，然后发送他们，把他们的结果汇总给下一个Api
        if self.get_next_api_list() and len(self.get_next_api_list()) > 0:
            response_list = []
            combined_result = {}
            for each_req in self.get_next_api_list():
                each_req.prev_result(this_result)
                each_result = each_req.send()
                combined_result.update(each_result.get_callback_result())
                response_list.append(each_result.get_resp())
            this_result = ApiResult(response_list, combined_result)

        # 处理串行请求链
        if self.get_next_api() and isinstance(self.get_next_api(), Api):
            self.get_next_api().prev_result(this_result)
            self.get_next_api().send()

        return this_result

    def get(self):
        """发送GET请求

        Returns:
            ApiResult: 请求结果对象
        """
        self.__method = 'get'
        return self.send()

    def post(self):
        """发送POST请求

        Returns:
            ApiResult: 请求结果对象
        """
        self.__method = 'post'
        return self.send()

    def then(self, param):
        """设置下一步请求

        Args:
            param: 可以是单个Api对象或Api对象列表

        Returns:
            self: 支持链式调用
        """
        if self.get_next_api():
            self.get_next_api().then(param)
        else:
            if isinstance(param, list):
                self.next_api_list(param)
                return self
            else:
                self.next_api(param)
        return self

    def __send_loop(self):
        """内部循环发送方法

        用于并行发送请求
        """
        while True:
            if self.__count_sent >= self.__count_request:
                return
            self.__count_sent += 1
            time.sleep(self.__interval)
            self.send()

    def send_parallel(self, count_request=1, count_thread=1, interval=0, all_done_callback=None, future_callback=None):
        """并行发送请求

        Args:
            count_request: 总发送次数
            count_thread: 线程个数
            interval: 每个请求的间隔时间(秒)
            all_done_callback: 所有任务完成后回调(无参数)
            future_callback: 每个任务完成后回调(1个参数，表示一个future对象)
        """
        self.__count_request = count_request
        self.__interval = interval
        self.__count_sent = 0

        with ThreadPoolExecutor() as executor:
            for i in range(count_thread):
                future = executor.submit(self.__send_loop)
                if future_callback:
                    future.add_done_callback(future_callback)

            # 等待所有任务完成
            executor.shutdown(wait=True)

            if all_done_callback:
                all_done_callback()


if __name__ == '__main__':
    # 示例用法
    Api("http://www.baidu.com").headers({}).send_and_print()