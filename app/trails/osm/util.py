from functools import partial
from multiprocessing.pool import Pool


def verify_identical_nodes(trails_in, trails_out):
    nodes_in = set()
    for trail in trails_in:
        for node in trail.nodes:
            nodes_in.add(node)

    nodes_out = set()
    for trail in trails_out:
        for node in trail.nodes:
            nodes_out.add(node)

    assert nodes_out == nodes_in


def window(iterable, size=2):
    i = iter(iterable)
    win = []
    for e in range(0, size):
        win.append(next(i))
    yield win
    for e in i:
        win = win[1:] + [e]
        yield win


def pmap(iter, func, pool: Pool, chunksize=1):
    if pool._processes == 1:  # type: ignore

        def splat(arg_tup):
            return func(*arg_tup)

        return list(map(splat, iter))
    else:
        return pool.starmap(func, iter, chunksize=chunksize)


class memoize(object):
    """cache the return value of a method

    This class is meant to be used as a decorator of methods. The return value
    from a given method invocation will be cached on the instance whose method
    was invoked. All arguments passed to a method decorated with memoize must
    be hashable.

    If a memoized method is invoked directly on its class the result will not
    be cached. Instead the method will be invoked like a static method:
    class Obj(object):
        @memoize
        def add_to(self, arg):
            return self + arg
    Obj.add_to(1) # not enough arguments
    Obj.add_to(1, 2) # returns 3, result is not cached
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res
