# coding: utf-8

try:
    from greenlet import greenlet
    get_current_greenlet = greenlet.getcurrent
    del greenlet
except:
    get_current_greenlet = int

from thread import get_ident as get_current_thread, allocate_lock

if get_current_greenlet is int:
    get_ident = get_current_thread
else:
    get_ident = lambda: (get_current_thread(), get_current_thread())


class Local(object):
    """
        类似ThreadLocal的实现, 可以应付协程场景。
    """
    __slots__ = ('__storage__', '__lock__')

    def __init__(self):
        object.__setattr__(self, '__storage__', {})
        object.__setattr__(self, '__lock__', allocate_lock())

    def __iter__(self):
        return self.__storage__.iteritems()

    def __release_local__(self):
        self.__storage__.pop(get_ident(), None)

    def __setattr__(self, key, value):
        self.__lock__.acquire()
        try:
            ident = get_ident()
            if ident in self.__storage__:
                self.__storage__[ident][key] = value
            else:
                self.__storage__[ident] = {key: value}
        finally:
            self.__lock__.release()

    def __getattr__(self, item):
        self.__lock__.acquire()
        try:
            return self.__storage__[get_ident()][item]
        except KeyError:
            raise AttributeError(item)
        finally:
            self.__lock__.release()

    def __delattr__(self, item):
        self.__lock__.acquire()
        try:
            del self.__storage__[get_ident()][item]
        except KeyError:
            raise AttributeError(item)
        finally:
            self.__lock__.release()


class LocalStack(object):
    """
        Local封装, 可以用使用Stack的方式压入弹出变量
        可优雅处理请求上下文
    """
    def __init__(self):
        self._local = Local()
        self._lock = allocate_lock()

    def push(self, obj):
        self._lock.acquire()
        try:
            rv = getattr(self._local, 'stack', None)
            if rv is None:
                self._local.stack = rv = []
            rv.append(obj)
        finally:
            self._lock.release()

    def pop(self):
        self._lock.acquire()
        try:
            stack = getattr(self._local, 'stack', None)
            if stack is None:
                return None
            if len(stack) == 1:
                del self._local.stack
            return stack.pop()
        finally:
            self._lock.release()

    @property
    def top(self):
        try:
            return self._local.stack[-1]
        except(AttributeError, IndexError):
            return None


class LocalProxy(object):
    """
        代理Local中特定对象， 如：
        lc = Local()
        lc.a = 1
        lc.b = 2
        a = LocalProxy(lc, 'a')
        则不同的上下文中a的值就是当前上下文的a，对于使用者来说相当于全局变量, 但内部又是
        动态绑定的，优雅不 :)

        当传入的不是一个Local对象时, 则会调用这个参数， 如：
        _request_ctx_stack = LocalStack()
        _request_ctx_stack.push(_RequestContext())
        request = LocalProxy(lambda: _request_ctx_stack.top.request)
        每次使用request时，都会动态获得当前上下文的request :)
    """
    __slots__ = ('__local__', '__dict__', '__name__')

    def __init__(self, local, name=None):
        object.__setattr__(self, '__local__', local)
        object.__setattr__(self, '__name__', name)

    def _get_current_object(self):
        if not isinstance(self.__local__, Local):
            return self.__local__()
        try:
            return getattr(self.__local__, self.__name__)
        except AttributeError:
            raise RuntimeError('no object bound to %s' % self.__name__)

    @property
    def __dict__(self):
        try:
            return self._get_current_object().__dict__
        except RuntimeError:
            return AttributeError('__dict__')

    def __getattr__(self, item):
        return getattr(self._get_current_object(), item)

    def __dir__(self):
        try:
            return dir(self._get_current_object())
        except RuntimeError:
            return []

