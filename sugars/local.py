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

    def __repr__(self):
        try:
            obj = self._get_current_object()
        except RuntimeError:
            return '<%s unbound>' % self.__class__.__name__
        return repr(obj)

    def __nonzero__(self):
        try:
            return bool(self._get_current_object())
        except RuntimeError:
            return False

    def __unicode__(self):
        try:
            return unicode(self._get_current_object())
        except RuntimeError:
            return repr(self)

    def __getattr__(self, item):
        return getattr(self._get_current_object(), item)

    def __dir__(self):
        try:
            return dir(self._get_current_object())
        except RuntimeError:
            return []

    def __setitem__(self, key, value):
        self._get_current_object()[key] = value

    def __delitem__(self, key):
        del self._get_current_object()[key]

    def __setslice__(self, i, j, seq):
        self._get_current_object()[i:j] = seq

    def __delslice__(self, i, j):
        del self._get_current_object()[i:j]

    __setattr__ = lambda x, n, v: setattr(x._get_current_object(), n, v)
    __delattr__ = lambda x, n: delattr(x._get_current_object(), n)
    __str__ = lambda x: str(x._get_current_object())
    __lt__ = lambda x, o: x._get_current_object() < o
    __le__ = lambda x, o: x._get_current_object() <= o
    __eq__ = lambda x, o: x._get_current_object() == o
    __ne__ = lambda x, o: x._get_current_object() != o
    __gt__ = lambda x, o: x._get_current_object() > o
    __ge__ = lambda x, o: x._get_current_object() >= o
    __cmp__ = lambda x, o: cmp(x._get_current_object(), o)
    __hash__ = lambda x: hash(x._get_current_object())
    __call__ = lambda x, *a, **kw: x._get_current_object()(*a, **kw)
    __len__ = lambda x: len(x._get_current_object())
    __getitem__ = lambda x, i: x._get_current_object()[i]
    __iter__ = lambda x: iter(x._get_current_object())
    __contains__ = lambda x, i: i in x._get_current_object()
    __getslice__ = lambda x, i, j: x._get_current_object()[i:j]
    __add__ = lambda x, o: x._get_current_object() + o
    __sub__ = lambda x, o: x._get_current_object() - o
    __mul__ = lambda x, o: x._get_current_object() * o
    __floordiv__ = lambda x, o: x._get_current_object() // o
    __mod__ = lambda x, o: x._get_current_object() % o
    __divmod__ = lambda x, o: x._get_current_object().__divmod__(o)
    __pow__ = lambda x, o: x._get_current_object() ** o
    __lshift__ = lambda x, o: x._get_current_object() << o
    __rshift__ = lambda x, o: x._get_current_object() >> o
    __and__ = lambda x, o: x._get_current_object() & o
    __xor__ = lambda x, o: x._get_current_object() ^ o
    __or__ = lambda x, o: x._get_current_object() | o
    __div__ = lambda x, o: x._get_current_object().__div__(o)
    __truediv__ = lambda x, o: x._get_current_object().__truediv__(o)
    __neg__ = lambda x: -(x._get_current_object())
    __pos__ = lambda x: +(x._get_current_object())
    __abs__ = lambda x: abs(x._get_current_object())
    __invert__ = lambda x: ~(x._get_current_object())
    __complex__ = lambda x: complex(x._get_current_object())
    __int__ = lambda x: int(x._get_current_object())
    __long__ = lambda x: long(x._get_current_object())
    __float__ = lambda x: float(x._get_current_object())
    __oct__ = lambda x: oct(x._get_current_object())
    __hex__ = lambda x: hex(x._get_current_object())
    __index__ = lambda x: x._get_current_object().__index__()
    __coerce__ = lambda x, o: x.__coerce__(x, o)
    __enter__ = lambda x: x.__enter__()
    __exit__ = lambda x, *a, **kw: x.__exit__(*a, **kw)
