import unittest
from api.api import Api


class TestApi(unittest.TestCase):
    """
    测试Api v2
    """

    def test_request_chain(self):
        def baidu_callback(resp, api_result):
            print(
                f'this http resp is {resp}, prev http res is {api_result.get_resp()}, callback result is {api_result.get_callback_result()}')
            return {'baidu': 'baidu result'}

        def souhu_callback(resp, api_result):
            print(
                f'this http resp is {resp}, http res is {api_result.get_resp()}, callback result is {api_result.get_callback_result()}')
            return {'souhu': 'souhu result'}

        def sina_callback(resp, api_result):
            print(
                f'this http resp is {resp}, http res is {api_result.get_resp()}, callback result is {api_result.get_callback_result()}')
            return {'sina': 'sina result'}

        def gitee_callback(resp, api_result):
            print(
                f'this http resp is {resp}, http res is {api_result.get_resp()}, callback result is {api_result.get_callback_result()}')
            return {'gitee': 'gitee result'}

        baidu_api = Api('http://www.baidu.com').callback(baidu_callback)
        souhu_api = Api('https://www.sohu.com/').callback(souhu_callback)
        sina_api = Api('https://www.sina.com.cn').callback(sina_callback)
        gitee_api = Api('https://gitee.com/').callback(gitee_callback)
        # 链式请求
        # 方式一
        #
        # baidu_api.then(souhu_api.then(sina_api.then(gitee_api))).send()
        # 方式二
        # baidu_api.then(souhu_api).then(sina_api).then(gitee_api).send()

        # 请求组
        baidu_api.then([sina_api, souhu_api]).then(gitee_api).send()

    def test_query(self):
        Api('https://www.baidu.com').query({'a':'b'}).send_and_print()
