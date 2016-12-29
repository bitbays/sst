#!/usr/bin/env python
# coding: utf-8
# yc@2015/01/29

import asyncoro
import socket
import argparse
import signal
import time
from Crypto.Cipher import AES
from Crypto.Hash import SHA256, MD5

INIT_STREAM_SIZE = 2048


def log(msg):
    if args.verbose:
        print msg


def _new_sock():
    '''
    get a async sock obj
    '''
    return asyncoro.AsyncSocket(
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    )


def server_coro(local, remote, coro=None):
    s = _new_sock()
    args.socks.append(s)
    s.bind(local)
    s.listen(200)
    print 'Forwarding %s:%s => %s:%s' % (local + remote)
    while True:
        try:
            obj = yield s.accept()
            if obj is None:
                break
            conn, addr = obj
        except Exception, e:
            log('server_coro: %s' % e)
            break
        log('Accepted: %s:%s' % addr)
        asyncoro.Coro(client_coro, conn, addr, remote)
    print('Closing server %s:%s' % local)
    s.close()


def client_coro(conn, addr, remote, coro=None):
    s = _new_sock()
    log('Connecting %s:%s' % remote)
    try:
        yield s.connect(remote)
    except Exception, e:
        log('client_coro: %s' % e)
        s.close()
        return
    log('Proxying...')
    us = []
    p1 = asyncoro.Coro(proxy_coro, conn, s, us, is_encrypt=args.ekey)
    p2 = asyncoro.Coro(proxy_coro, s, conn, us, is_encrypt=args.dkey)
    us.append(p1)
    us.append(p2)
    args.proxy_coros[coro._id] = us
    yield p1.finish()
    yield p2.finish()
    del args.proxy_coros[coro._id]
    log('Closing client %s:%s' % remote)
    s.close()
    conn.close()


def proxy_coro(src, dst, us, coro=None, is_encrypt=None):
    # peer1, peer2 = src.getpeername(), dst.getpeername()
    cipher = AES.new(args.key256, AES.MODE_CFB, args.iv16)
    transform = cipher.encrypt if is_encrypt else cipher.decrypt
    transform = lambda i: i
    # auto adjust window size
    buffer_size = INIT_STREAM_SIZE
    fixed = False
    while True:
        try:
            data = yield src.recv(buffer_size)
        except Exception, e:
            log('proxy_coro: %s' % e)
            break
        if not data:
            break
        try:
            yield dst.sendall(transform(data))
        except Exception, e:
            log('proxy_coro: %s' % e)
            break
        size = len(data)
        if not fixed:
            # 还未固定
            if INIT_STREAM_SIZE <= size < buffer_size:
                log('buffer_size fixed: %d' % buffer_size)
                fixed = True
            else:
                # 增大 buffer
                buffer_size *= 2
                log('buffer_size => %d' % buffer_size)
        # log('[%d] %s -> %s' % (size, peer1, peer2))
    for i in us:
        if i is not coro:
            try:
                i.terminate()
            except Exception, e:
                log('proxy_coro: %s' % e)


def parse_args():
    parser = argparse.ArgumentParser(description='Simple Secure Tunnel')
    group = parser.add_mutually_exclusive_group(required=True)
    parser.add_argument('-v', '--verbose', action='store_true')
    group.add_argument(
        '-e', '--encrypt', dest='ekey', type=str,
        help='Choose encrypt mode and specify the key')
    group.add_argument(
        '-d', '--decrypt', dest='dkey', type=str,
        help='Choose decrypt mode and specify the key')
    parser.add_argument(
        'forwards', type=str, nargs='+',
        help=(
            'format: [[bind:]port:]target:port e.g.: 8.8.8.8:53 '
            '1053:8.8.8.8:53 127.0.0.1:1050:8.8.8.8:53'
        )
    )
    return parser.parse_args()


def parse_forwards(raw):
    '''
    8.8.8.8:53
    1053:8.8.8.8:53
    127.0.0.1:1053:8.8.8.8:53
    '''
    ret = {}
    for i in raw:
        j = i.split(':')
        k = len(j)
        if k == 2:
            p = int(j[1])
            ret[('', p)] = (j[0], p)
        elif k == 3:
            ret[('', int(j[0]))] = (j[1], int(j[2]))
        elif k == 4:
            ret[(j[0], int(j[1]))] = (j[2], int(j[3]))
        else:
            log('Cannot parse "%s"' % i)
    return ret


def make_key(raw):
    '''
    make a 32 bytes key
    '''
    length = len(raw)
    if length == 32:
        return raw
    elif length > 32:
        return raw[:16] + SHA256.new(raw).digest()[:16]
    else:
        return raw + SHA256.new(raw).digest()[:(32 - length)]


def dying(signum, frame):
    # main thread
    args.keep_alive = False
    # server_coro
    print 'quiting server_coro...'
    for i in args.socks:
        # close active server_coro
        i.close()
    for i in args.servers:
        try:
            # hack to wakeup & kill sleeping server_coro
            i._proceed_()
        except Exception, e:
            print 'dying: %s' % e
    # proxy_coro and client_coro
    print 'quiting proxy_coro...'
    for proxys in args.proxy_coros.values():
        for p in proxys:
            try:
                p.terminate()
            except Exception, e:
                print 'dying: %s' % e


args = parse_args()
forwards_map = parse_forwards(args.forwards)
args.key = args.ekey or args.dkey
args.key256 = make_key(args.key)
args.iv16 = MD5.new(args.key).digest()
args.servers = []
args.socks = []
args.proxy_coros = {}
args.keep_alive = True

# setup singal
signal.signal(signal.SIGINT, dying)
signal.signal(signal.SIGTERM, dying)

print 'Listenning...'
for local, remote in forwards_map.items():
    args.servers.append(asyncoro.Coro(server_coro, local, remote))

while args.keep_alive:
    time.sleep(1)
