# coding: utf8

"""
    Spoon::
    学习Flask源码过程中，理解之后再仿造出的Wsgi framework. 目前设计模式基本与Flask相同，
    也是依赖Werkzeug和Jinja2.
    后面可能会参照其他wsgi framework(如bottle, tornado)的设计进行改造.

    :copyright: (c) 2019.07 by Ke Bo.
"""

import os
import sys

from jinja2 import PackageLoader, Environment
from werkzeug.contrib.securecookie import SecureCookie
from werkzeug.routing import Map, Rule
from werkzeug.test import create_environ
from werkzeug.wrappers import Request as BaseRequest
from werkzeug.wrappers import Response as BaseResponse
from werkzeug.exceptions import HTTPException
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from werkzeug.exceptions import abort
from jinja2 import Markup, escape

from sugars.local import LocalStack, LocalProxy


class Request(BaseRequest):
    """
        请求对象，其中包含当前请求的详细信息
    """
    pass


class Response(BaseResponse):
    """
        相应对象，其中包含响应信息，是一个wsgi application,
        当调用response(environ, start_response)时才真正向客户端输出响应
    """
    default_mimetype = 'text/html'


class _RequestGlobals(object):
    """
        用于保存当前请求的全局变量，如：
        g = _request_ctx_stack.top.g
        g.db = connect_db()

        from spoon import g
        cursor = g.db.cursor()
    """
    pass


class _RequestContext(object):
    """
        请求上下文::
        当server接到一个请求时, 会调用spoon中的application函数这个wsgi application,
        这时application 首先用environ和其他自身对象构造出请求上下文，也就是这个类的实例, 在请求结束
        之前, 当使用定义过的LocalProxy, 如这里的app, url_adapter, request, g等, 则会动态获取这个实例
        的对应对象。巧妙之处就在这里。
    """

    def __init__(self, app, environ):
        self.app = app
        self.url_adapter = app.url_map.bind_to_environ(environ)
        self.request = app.request_class(environ)
        self.session = app.open_session(self.request)
        self.g = _RequestGlobals()
        self.flashes = None

    def __enter__(self):
        _request_ctx_stack.push(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_tb is None or not self.app.debug:
            _request_ctx_stack.pop()


def flash(message):
    session['_flashes'] = (session.get('_flashes', [])) + [message]


def get_flashed_messages():
    flashes = _request_ctx_stack.top.flashes
    if flashes is None:
        _request_ctx_stack.top.flashes = flashes = \
            session.pop('_flashes', [])
    return flashes


def _get_package_path(name):
    """
        根据模块名获取包的路径, 用于构造jinja2的PackageLoader
    :param name:
    :return:
    """
    try:
        return os.path.abspath(os.path.dirname(sys.modules[name].__file__))
    except (KeyError, AttributeError):
        return os.getcwd()


def render_template(template_name, **context):
    """
        渲染模版, 先更新context(如加入request, session, g等.),
        再用jinja_env渲染(jinja_env.global.update， 可添加自定义函数)
    :param template_name:
    :param context:
    :return:
    """
    current_app.update_template_context(context)
    return current_app.jinja_env.get_template(template_name).render(context)


def _default_template_ctx_processor():
    """
        添加额外的context
    :return:
    """
    reqctx = _request_ctx_stack.top
    return dict(
        request=reqctx.request,
        session=reqctx.session,
        g=reqctx.g
    )


def url_for(endpoint, **values):
    """
        根据endpoint和参数构造url, 默认结果是相对路径
    :param endpoint:
    :param values:
    :return:
    """
    return _request_ctx_stack.top.url_adapter.build(endpoint, values)


class Spoon:
    # 请求类，默认为Request，可更改
    request_class = Request

    # 响应类, 默认为Response, 可更改
    response_class = Response

    jinja_options = dict(
        autoescape=True,
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_']
    )

    static_path = '/static'

    secret_key = None

    session_cookie_name = 'session'

    def __init__(self, package_name):
        self.package_name = package_name
        self.root_path = _get_package_path(self.package_name)
        self.url_map = Map()  # 路由Map
        self.view_funcs = {}
        self.before_request_funcs = []
        self.after_request_funcs = []
        self.error_handlers = {}
        self.debug = False
        self.template_context_processors = [_default_template_ctx_processor]
        self.jinja_env = Environment(loader=self.create_jinja_loader(),
                                     **self.jinja_options)
        self.jinja_env.globals.update(
            url_for=url_for,
            get_flashed_messages=get_flashed_messages,
        )

        if self.static_path is not None:
            """
                用werkzeug中的SharedDataMiddleware托管静态文件
            """
            self.url_map.add(Rule(self.static_path + '/<filename>',
                                  build_only=True, endpoint='static'))
            target = os.path.join(self.root_path, 'static')

            self.wsgi_app = SharedDataMiddleware(self.wsgi_app, {
                self.static_path: target
            })

    def before_request(self, func):
        """
            所有请求转发之前都要经过的函数的装饰器
        :param func:
        :return:
        """
        self.before_request_funcs.append(func)
        return func

    def after_request(self, func):
        """
            所有请求经视图函数处理完成后都要经过的函数的装饰器
        :param func:
        :return:
        """
        self.after_request_funcs.append(func)
        return func

    def preprocess_request(self):
        for func in self.before_request_funcs:
            rv = func()
            if rv is not None:
                return rv

    def process_response(self, response):
        session = _request_ctx_stack.top.session
        if session is not None:
            self.save_session(session, response)
        for handler in self.after_request_funcs:
            response = handler(response)
        return response

    def open_session(self, request):
        key = self.secret_key
        if key is not None:
            return SecureCookie.load_cookie(request, self.session_cookie_name,
                                            secret_key=key)

    def save_session(self, session, response):
        if session is not None:
            session.save_cookie(response, self.session_cookie_name)

    def create_jinja_loader(self):
        return PackageLoader(self.package_name)

    def context_processor(self, func):
        """
            添加模板变量的函数
        :param func:
        :return:
        """
        self.template_context_processors.append(func)
        return func

    def request_context(self, environ):
        return _RequestContext(self, environ)

    def test_request_context(self, *args, **kwargs):
        return self.request_context(create_environ(*args, **kwargs))

    def update_template_context(self, context):
        """
            更新jinja2上下文
        :param context:
        :return:
        """
        for func in self.template_context_processors:
            context.update(func())

    def errorhandler(self, code):
        """
            错误处理函数装饰器
        :param code: 错误状态码, 如404，500等。
        """

        def decorator(func):
            self.error_handlers[code] = func
            return func

        return decorator

    def make_response(self, rv):
        """
            根据视图函数的返回结果构造Response对象,
            最终发给客户端的响应则是调用Response对象生成的
        :param rv: 视图函数的返回结果
        :return: Response object
        """
        if isinstance(rv, self.response_class):
            return rv
        if isinstance(rv, basestring):
            return self.response_class(rv)
        if isinstance(rv, tuple):
            return self.response_class(*rv)
        return self.response_class.force_type(rv, _request_ctx_stack.top.request.environ)

    def dispatch_request(self):
        """
            路由转发
        :return: 路由处理函数的返回结果 或 抛出异常
        """
        try:
            endpoint, values = _request_ctx_stack.top.url_adapter.match()
            return self.view_funcs[endpoint](**values)
        except HTTPException, e:
            handler = self.error_handlers.get(e.code)
            if handler is None:
                return e
            return handler(e)
        except Exception, e:
            handler = self.error_handlers.get(500)
            if self.debug or handler is None:
                raise
            return handler(e)

    def wsgi_app(self, environ, start_response):
        """
            真正的wsgi application， 路由转发, 构造Response对象，
            最后调用response对象(也是一个 wsgi application)生成最终响应
        :param environ: 上下文字典
        :param start_response: server的start_response，用于发送status code & headers
        :return:
        """
        with _RequestContext(self, environ):
            rv = self.preprocess_request()
            if rv is None:
                rv = self.dispatch_request()
            response = self.make_response(rv)
            response = self.process_response(response)
            return response(environ, start_response)

    def add_url_rule(self, rule, endpoint, **options):
        """
            添加路由
        :param rule: 路由规则
        :param endpoint: 处理函数对应的key
        :param options: 其他参数, 构造Rule时用到, 如methods=['POST', 'PUT']
        :return:
        """
        options['endpoint'] = endpoint
        options.setdefault('methods', ('GET',))
        self.url_map.add(Rule(rule, **options))

    def route(self, rule, **options):
        """
            添加路由的装饰器函数
        :param rule:
        :param options:
        :return:
        """

        def decorator(func):
            self.add_url_rule(rule, func.__name__, **options)
            self.view_funcs[func.__name__] = func
            return func

        return decorator

    def test_client(self):
        from werkzeug.test import Client
        return Client(self, self.response_class, use_cookies=True)

    def run(self, host='localhost', port=5000, **options):
        """
            启动wekzeug中的简单server, 可用于调试
        :param host: 主机地址, 设置为0.0.0.0可开放访问
        :param port: 端口
        :param options:
        :return:
        """
        from werkzeug.serving import run_simple
        if 'debug' in options:
            self.debug = options.pop('debug')
        use_reloader = use_debugger = self.debug
        run_simple(host, port,
                   self,
                   use_reloader=use_reloader,
                   use_debugger=use_debugger)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


# 请求上下文栈
_request_ctx_stack = LocalStack()
# 请求上下文的request LocalProxy，可动态获取当前上下文的request
request = LocalProxy(lambda: _request_ctx_stack.top.request)
current_app = LocalProxy(lambda: _request_ctx_stack.top.app)
session = LocalProxy(lambda: _request_ctx_stack.top.session)
g = LocalProxy(lambda: _request_ctx_stack.top.g)
