# sst
Simple Secure Tunnel

## Help

```shell
$ python tunnel.py -h
usage: tunnel.py [-h] [-v] (-e EKEY | -d DKEY) forwards [forwards ...]

Simple Secure Tunnel

positional arguments:
  forwards              format: [[bind:]port:]target:port e.g.: 8.8.8.8:53
                        1053:8.8.8.8:53 127.0.0.1:1050:8.8.8.8:53

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose
  -e EKEY, --encrypt EKEY
                        Choose encrypt mode and specify the key
  -d DKEY, --decrypt DKEY
                        Choose decrypt mode and specify the key
```


## 应用场景：一个跳板程序

机器 A 不能直接访问机器 B 的 portB 端口，需要通过机器 C 做跳板间接访问，并且 A-C 和 C-B 之间的流量需要加密。

假设机器 B 为 DNS 服务器，机器 A 需要查询 B 获得 twitter.com 的 IP 地址。A 与 B 之间被互联网 DNS 污染，无法直接查询 B。

首先选择一个密码：testme，然后在机器 A 上开启加密转发服务，访问 A 的 8888 端口相当于访问 C 的 9999 端口：

```shell
python tunnel.py -e testme -v 8888:C:9999
```

然后在机器 C 上开启解密转发服务，访问 C 的 9999 端口相当于访问 B 的 53 端口：

```shell
python tunnel.py -d testme 9999:B:53
```

之后在 A 上就可以正常连接 B 了，并且流量是加密的：

```shell
dig +tcp twitter.com @127.0.0.1 -p 8888
```
