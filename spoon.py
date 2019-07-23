# coding: utf8

from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request as BaseRequest
from werkzeug.wrappers import Response as BaseResponse

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


class Spoon:
    config = {}

    request_class = Request

    response_class = Response

    def __init__(self):
        self.url_map = Map()  # 路由Map
        self.view_funcs = {}

    def make_response(self, rv):
        if isinstance(rv, self.response_class):
            return rv
        if isinstance(rv, basestring):
            return self.response_class(rv)
        if isinstance(rv, tuple):
            return self.response_class(*rv)
        return self.response_class.force_type(rv, _request_ctx_stack.top.request.environ)


    def dispatch_request(self):
        endpoint, values = _request_ctx_stack.top.url_adapter.match()
        rv = self.view_funcs[endpoint](**values)
        return rv

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
request = LocalProxy(lambda : _request_ctx_stack.top.request)