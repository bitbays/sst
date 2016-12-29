#!/usr/bin/env python
# coding: utf-8
# yc@2015/01/29

import asyncoro
import time
import random


def coro_func(n, coro=None):
    s = random.uniform(0.5, 3)
    print '%f: coroutine %d sleeping for %f seconds' % (time.time(), n, s)
    yield coro.sleep(s)
    print '%f: coroutine %d terminated' % (time.time(), n)


for i in range(10):
    asyncoro.Coro(coro_func, i)
