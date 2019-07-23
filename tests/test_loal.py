import sys
import os

sys.path[0] = os.path.abspath('../')

from sugars.local import Local


def test():
    lc.a = 'test'
    print('lc.a in test: ', lc.a)


if __name__ == '__main__':
    lc = Local()
    lc.a = 1
    print('lc.a in Main: ', lc.a)
    import threading
    t = threading.Thread(target=test, args=())
    t.start()