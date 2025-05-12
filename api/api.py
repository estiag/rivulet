import json

from bs4 import BeautifulSoup
from requests import Response

import time
from typing import Callable
from urllib.parse import urlparse, urlunparse
from concurrent.futures import ThreadPoolExecutor
import requests
import api.json_util as json_util


class RequestGroup:
    def __init__(self, request_list, next_api):
        self.__request_list = request_list
        self.__next_api = next_api

    def request_list(self, request_list):
        self.__request_list = request_list
        return self

    def get_request_list(self):
        return self.__request_list

    def next_api(self, next_api):
        self.__next_api = next_api
        return self

    def get_next_api(self):
        return self.__next_api


class ApiResult:
    def __init__(self, resp, callback_result):
        self.__resp = resp
        self.__callback_result = callback_result

    def get_resp(self):
        return self.__resp

    def get_callback_result(self):
        return self.__callback_result

    def resp(self, resp):
        self.__resp = resp
        return self

    def callback_result(self, callback_result):
        self.__callback_result = callback_result
        return self


class Proxy:
    def __init__(self, host='localhost', port=None, protocol='http'):
        self.host = host
        self.port = port
        self.protocol = protocol


class Env:
    def __init__(self, host='localhost', port=None, protocol='http'):
        self.host = host
        self.port = port
        self.protocol = protocol

    def get_env(self):
        host = self.host
        if self.port:
            host = f'{host}:{self.port}'
        return f'{self.protocol}://{host}'


class Api:

    def __init__(self, url=None, env=None, path=None, port=None, host=None, protocol=None, method=None,
                 query=None, fragment=None, headers=None, verify=True, proxy=None, body=None, cookie=None,
                 stream=None, callback=None, before_send=None):
        self.__port = None
        self.__host = ''
        self.__protocol = 'http'
        self.__method = 'get'
        self.__path = ''  # path 优先级比url高，会覆盖url
        self.__query = ''
        self.__fragment = ''
        self.__headers = {'Content-Type': 'application/json'}
        self.__verify = True
        self.__env = None
        self.__proxy = None
        self.__body = None
        self.__cookie = None
        self.__stream = False
        # 储存函数形式传入的属性
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

        self.__next_api = None
        self.__next_api_list = None
        self.__callback = None
        self.__before_send = None
        self.__prev_result = None
        self.__count_sent = None
        self.__interval = None
        self.__count_request = None
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

    def get_value_ignore_case(self, dictionary, key):
        for k, v in dictionary.items():
            if k.lower() == key.lower():
                return v
        return None

    def before_send(self, before_send: Callable[[ApiResult, object], object]):
        """
        before_send需要两个参数(上一步结果，本Api对象)，在请求前调用
        """
        if before_send:
            self.__before_send = before_send
        return self

    def get_before_send(self):
        return self.__before_send

    def callback(self, callback: Callable[[Response, ApiResult], object]):
        """
        callback需要2个函数(本次http响应、上一步的结果)，在请求完成后调用，用来处理网络返回的结果
        如果有后续请求链并且后续请求依赖之前请求结果，那么callback需要把结果return出去
        """
        if callback:
            self.__callback = callback
        return self

    def get_callback(self):
        return self.__callback

    def prev_result(self, prev_result):
        if prev_result:
            self.__prev_result = prev_result
        return self

    def get_prev_result(self):
        return self.__prev_result

    def next_api(self, next_api):
        if next_api:
            self.__next_api = next_api
        return self

    def get_next_api(self):
        return self.__next_api

    def next_api_list(self, next_api_list):
        if next_api_list:
            self.__next_api_list = next_api_list
        return self

    def get_next_api_list(self):
        return self.__next_api_list

    def stream(self, stream):
        if stream:
            if callable(stream):
                self.__callable_stream = stream
            else:
                self.__stream = stream
        return self

    def get_stream(self):
        return self.__stream

    def cookie(self, cookie):
        if cookie:
            if callable(cookie):
                self.__callable_cookie = cookie
            else:
                self.__cookie = cookie
        return self

    def get_cookie(self):
        return self.__cookie

    def body(self, body):
        if body:
            if callable(body):
                self.__callable_body = body
            else:
                self.__body = body
        return self

    def get_body(self):
        return self.__body

    def proxy(self, proxy):
        if proxy:
            if callable(proxy):
                self.__callable_proxy = proxy
            else:
                self.__proxy = proxy
        return self

    def get_proxy(self):
        if self.__proxy:
            return {
                'http': f'http://{self.__proxy.host}:{self.__proxy.port}',
                'https': f'http://{self.__proxy.host}:{self.__proxy.port}'
            }
        else:
            return None

    def port(self, port):
        if port:
            if callable(port):
                self.__callable_port = port
            else:
                self.__port = port
        return self

    def get_port(self):
        return self.__port

    def host(self, host):
        if host:
            if callable(host):
                self.__callable_host = host
            else:
                self.__host = host
        return self

    def get_host(self):
        return self.__host

    def protocol(self, protocol):
        if protocol:
            if callable(protocol):
                self.__callable_protocol = protocol
            else:
                self.__protocol = protocol
        return self

    def get_protocol(self):
        return self.__protocol

    def url(self, url):
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
        if not self.get_host():
            return None
        host = self.get_host()
        if self.get_port():
            host = f'{host}:{self.get_port()}'
        data = [self.get_protocol(), host, self.get_path(), '', self.get_query(),
                self.get_fragment()]
        return urlunparse(data)

    def method(self, method):
        if method:
            if callable(method):
                self.__callable_method = method
            else:
                self.__method = method
        return self

    def get_method(self):
        return self.__method

    def path(self, path):
        if path:
            if callable(path):
                self.__callable_path = path
            else:
                self.__path = path
        return self

    def get_path(self):
        return self.__path

    def fragment(self, fragment):
        if fragment:
            if callable(fragment):
                self.__callable_fragment = fragment
            else:
                self.__fragment = fragment
        return self

    def get_fragment(self):
        return self.__fragment

    def headers(self, headers):
        if headers:
            if callable(headers):
                self.__callable_headers = headers
            else:
                self.__headers.update(headers)
        return self

    def get_headers(self):
        return self.__headers

    def query(self, query):
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
        return self.__query

    def verify(self, verify):
        if isinstance(verify, bool):
            if callable(verify):
                self.__callable_verify = verify
            else:
                self.__verify = verify
        return self

    def get_verify(self):
        return self.__verify

    def env(self, env):
        if env:
            if isinstance(env, Env):
                self.port(env.port)
                self.host(env.host)
                self.protocol(env.protocol)
            if callable(env):
                self.__callable_env = env
        return self

    def get_env(self):
        return self.__env

    def get_desc(self):
        return {
            'url': self.get_url(),
            'method': self.get_method(),
            'header': self.get_headers(),
            'verify': self.get_verify(),
            'proxy': self.get_proxy()
        }

    def set_attr(self):
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
        return self.send().get_resp().json()

    def send_and_print(self):
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
        if self.get_before_send():
            self.get_before_send()(self.get_prev_result(), self)
        self.set_attr()
        this_result = ApiResult(None, None)
        resp = None
        if self.get_url():
            print(f'{self.get_method()} {self.get_url()}')
            # 先把自己的请求发出去
            if self.get_headers() and self.get_value_ignore_case(self.get_headers(), 'Content-Type'):
                if self.get_body() and 'application/json' in self.get_value_ignore_case(self.get_headers(),
                                                                                        'Content-Type'):
                    self.body(json.dumps(self.get_body()))
            resp = requests.request(method=self.get_method(), url=self.get_url(), headers=self.get_headers(),
                                    data=self.get_body(), verify=self.get_verify(), cookies=self.get_cookie(),
                                    proxies=self.get_proxy(), stream=self.get_stream())
            this_result.resp(resp)

        if self.get_callback():
            # 如果有callback就执行它然后把结果暂存在自己这
            prev_result = self.get_prev_result() or this_result
            this_callback_result = this_result.callback_result(self.get_callback()(resp, prev_result))
            this_result.callback_result(this_callback_result.get_callback_result())

        if self.get_next_api_list() and len(self.get_next_api_list()) > 0:
            # 如果next_request_list有值需要把自己的ApiResult给next_request_list中的每个Api，然后发送他们，把他们的结果汇总给下一个Api
            response_list = []
            combined_result = {}
            for each_req in self.get_next_api_list():
                each_req.prev_result(this_result)
                each_result = each_req.send()
                combined_result.update(each_result.get_callback_result())
                response_list.append(each_result.get_resp())
            this_result = ApiResult(response_list, combined_result)

        if self.get_next_api() and isinstance(self.get_next_api(), Api):
            # request链有值,需要做链式请求
            self.get_next_api().prev_result(this_result)
            self.get_next_api().send()

        return this_result

    def get(self):
        self.__method = 'get'
        return self.send()

    def post(self):
        self.__method = 'post'
        return self.send()

    def then(self, param):
        """
        param有可能是Api对象也有可能是Api列表
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
        while True:
            if self.__count_sent >= self.__count_request:
                return
            self.__count_sent += 1
            time.sleep(self.__interval)
            self.send()

    def send_parallel(self, count_request=1, count_thread=1, interval=0, all_done_callback=None, future_callback=None):
        """
        :param count_request: 总发送次数
        :param count_thread: 线程个数
        :param interval: 每个请求的间隔时间(秒)
        :param all_done_callback: 所有任务完成后回调(无参数)
        :param future_callback: 每个任务完成后回调(1个参数，表示一个future对象)
        :return:
        """
        self.__count_request = count_request
        self.__interval = interval
        self.__count_sent = 0

        with ThreadPoolExecutor() as executor:
            for i in range(count_thread):
                future = executor.submit(self.__send_loop)
                if future_callback:
                    future.add_done_callback(future_callback)
            # 等待所有任务执行完成后调用all_done_callback
            executor.shutdown(wait=True)
            if all_done_callback:
                all_done_callback()


if __name__ == '__main__':
    Api("http://www.baidu.com").headers({}).send_and_print()
