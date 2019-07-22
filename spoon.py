# coding: utf8

from werkzeug.routing import Map, Rule


class Spoon:
    config = {}

    def __init__(self):
        self.url_map = Map()  # 路由Map
        self.view_funcs = {}

    def not_found(self, environ, start_response):
        status = '404 NOT FOUND'
        start_response(status, [('test', 'not found')])
        return 'NOT FOUND'

    def dispatch_request(self):
        pass

    def application(self, environ, start_response):
        url_adapter = self.url_map.bind_to_environ(environ)
        endpoint, values = url_adapter.match()
        res = self.view_funcs[endpoint](**values)
        start_response('200 OK', [])
        return res

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
