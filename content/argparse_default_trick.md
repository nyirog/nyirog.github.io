Title: Argparse default trick
Date: 2021-01-03T12:00:00
Category: Python

At work we have a repetitive job to create small helper scripts for our
internal services. Most of them are simple xmlrpc client which expose only a
couple of methods and the methods have zero or one parameter. This minimalist
requirements can be implemented with standard python libraries.

# argparse subparsers

The `add_subparsers` method of `ArgumentParser` can be used to select the xmlrpc
method:

```python
import argparse
import xmlrpc.client

parser = argparse.ArgumentParser()
sub_parsers = parser.add_subparsers(dest="command", required=True)

sub_parsers.add_parser("list")

get_parser = sub_parsers.add_parser("get")
get_parser.add_argument("id")

client = xmlrpc.client.ServerProxy("http://127.0.0.1:1234")
args = parser.parse_args()

if args.command == "list":
    client.list()
elif args.command == "get":
    client.get(args.id)
```

and `argparse` will generate the usual interactive help for our client:

```text
usage: client.py [-h] {list,get} ...

positional arguments:
  {list,get}

optional arguments:
  -h, --help  show this help message and exit
```

```text
usage: client.py get [-h] id

positional arguments:
  id

optional arguments:
  -h, --help  show this help message and exit
```

# set_defaults

This is nice, but it would better if the function call and the argument
definition would be closer. The `set_defaults` method can help to register our
xmlrpc call into the parsed args:

```python
import argparse
import xmlrpc.client

client = xmlrpc.client.ServerProxy("http://127.0.0.1:1234")

parser = argparse.ArgumentParser()
sub_parsers = parser.add_subparsers(dest="command", required=True)

list_parser = sub_parsers.add_parser("list")
list_parser.set_defaults(action=lambda _: client.list())

get_parser = sub_parsers.add_parser("get")
get_parser.add_argument("id")
get_parser.set_defaults(action=lambda args: client.get(args.id))

args = parser.parse_args()
args.action(args)
```

# argparse_action

It's more compact but not so pythonic. The code would be more readable if the
argument definition would be created from the function signature not the other
way around. The `inspect.signature` can help us to create a helper module
(`argparse_action`) for this:


```python
import inspect

def add_action(sub_parsers, func):
    parser = sub_parsers.add_parser(func.__name__)
    sig = inspect.signature(func)

    for name in sig.parameters:
        parser.add_argument(name)

    def action(cli_args):
        func_args = [getattr(cli_args, name) for name in sig.parameters]
        return func(*func_args)

    parser.set_defaults(action=action)
```

```python
import argparse
import xmlrpc.client

from argparse_action import add_action


def get(id):
    client = _connect()
    return client.get(id)

def list():
    client = _connect()
    return client.list()

def _connect():
    return xmlrpc.client.ServerProxy("http://127.0.0.1:1234")


parser = argparse.ArgumentParser()
sub_parsers = parser.add_subparsers(dest="command", required=True)
add_action(sub_parsers, list)
add_action(sub_parsers, get)

args = parser.parse_args()
args.action(args)
```

# action.add decorator

It is more readable but we cannot see easily which function is exposed to CLI.
A decoration could help:

```python
import inspect


class Action:
    def __init__(self, pasrer):
        self._parsers = parser.add_subparsers(dest="command", required=True)

    def add(self, func):
        parser = self._parsers.add_parser(func.__name__)
        return add_action(parser, func)

def add_action(parser, func):
    sig = inspect.signature(func)

    for name in sig.parameters:
        parser.add_argument(name)

    def action(cli_args):
        func_args = [getattr(cli_args, name) for name in sig.parameters]
        return func(*func_args)

    parser.set_defaults(action=action)
    return action
```

```python
import argparse
import xmlrpc.client

from argparse_action import add_action

parser = argparse.ArgumentParser()
action = Action(parser)


@action.add()
def get(id):
    client = _connect()
    return client.get(id)

@action.add()
def list():
    client = _connect()
    return client.list()

def _connect():
    return xmlrpc.client.ServerProxy("http://127.0.0.1:1234")

args = parser.parse_args()
args.action(args)
```

The [argparse_action](https://pypi.org/project/argparse-action/) is published
to [pypi](https://pypi.org/) so you can try the its other features.
