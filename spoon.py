# coding: utf8

import os
import sys

from jinja2 import PackageLoader, Environment
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request as BaseRequest
from werkzeug.wrappers import Response as BaseResponse
from werkzeug.exceptions import HTTPException

from sugars.local import LocalStack, LocalProxy


class Request(BaseRequest):
    pass


class Response(BaseResponse):
    default_mimetype = 'text/html'


class _RequestGlobals(object):
    pass


class _RequestContext(object):
    def __init__(self, app, environ):
        self.app = app
        self.url_adapter = app.url_map.bind_to_environ(environ)
        self.request = app.request_class(environ)
        self.g = _RequestGlobals()

    def __enter__(self):
        _request_ctx_stack.push(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_tb is None or not self.app.config.get('debug', None):
            _request_ctx_stack.pop()



def _get_package_path(name):
    try:
        return os.path.abspath(os.path.dirname(sys.modules[name].__file__))
    except (KeyError, AttributeError):
        return os.getcwd()


def render_template(template_name, **context):
    current_app.update_template_context(context)
    return current_app.jinja_env.get_template(template_name).render(context)


def _default_template_ctx_processor():
    reqctx = _request_ctx_stack.top
    return dict(
        request=reqctx.request,
        g=reqctx.g
    )


def url_for(endpoint, **values):
    return _request_ctx_stack.top.url_adapter.build(endpoint, values)


class Spoon:
    request_class = Request

    response_class = Response

    jinja_options = dict(
        autoescape=True,
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_']
    )

    def __init__(self, package_name):
        self.package_name = package_name
        self.root_path = _get_package_path(self.package_name)
        self.url_map = Map()  # 路由Map
        self.view_funcs = {}
        self.error_handlers = {}
        self.config = {}
        self.template_context_processors = [_default_template_ctx_processor]
        self.jinja_env = Environment(loader=self.create_jinja_loader(),
                                     **self.jinja_options)
        self.jinja_env.globals.update(
            url_for=url_for,
        )

    def create_jinja_loader(self):
        return PackageLoader(self.package_name)

    def update_template_context(self, context):
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
        if isinstance(rv, self.response_class):
            return rv
        if isinstance(rv, basestring):
            return self.response_class(rv)
        if isinstance(rv, tuple):
            return self.response_class(*rv)
        return self.response_class.force_type(rv, _request_ctx_stack.top.request.environ)

    def dispatch_request(self):
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
            if self.config.get('debug') or handler is None:
                raise
            return handler(e)

    def application(self, environ, start_response):
        with _RequestContext(self, environ):
            rv = self.dispatch_request()
            response = self.make_response(rv)
            return response(environ, start_response)

    def add_url_rule(self, rule, endpoint, **options):
        options['endpoint'] = endpoint
        options.setdefault('methods', ('GET',))
        self.url_map.add(Rule(rule, **options))

    def route(self, rule, **options):
        def decorator(func):
            self.add_url_rule(rule, func.__name__, **options)
            self.view_funcs[func.__name__] = func
            return func

        return decorator

    def run(self, host, port, **options):
        self.config.update(options)
        from werkzeug import run_simple
        use_reloader = use_debugger = self.config.get('debug', False)
        run_simple(host, port,
                   self.application,
                   use_reloader=use_reloader,
                   use_debugger=use_debugger)


_request_ctx_stack = LocalStack()
request = LocalProxy(lambda: _request_ctx_stack.top.request)
current_app = LocalProxy(lambda: _request_ctx_stack.top.app)
g = LocalProxy(lambda: _request_ctx_stack.top.g)