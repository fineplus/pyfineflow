import ast
import inspect
from pathlib import Path
from typing import Callable, List, Dict

from .schemas import Input, Output, Component
import hashlib


def get_md5_hash(input_string):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()


type_map = {
    'int': 'integer',
    'float': 'float',
    'bool': 'boolean',
    'list': 'list',
    'str': 'string',
    'Enum': 'enum'

}


def recursive_update(default, custom):
    if not isinstance(default, dict) or not isinstance(custom, dict):
        raise TypeError('Params of recursive_update should be dicts')

    for key in custom:
        if isinstance(custom[key], dict) and isinstance(
                default.get(key), dict):
            default[key] = recursive_update(default[key], custom[key])
        else:
            default[key] = custom[key]

    return default


def read_text_if_path_exit(path):
    if path:
        path = Path(path)
        if path.exists() and path.is_file():
            return path.read_text(encoding='utf-8')
    return ''


def type_parse(type_name):
    return type_map.get(type_name, type_name)


def get_return_variable_names(func):
    source = inspect.getsource(func)
    tree = ast.parse(source)
    for ast_node in ast.walk(tree):
        if isinstance(ast_node, ast.Return):
            if isinstance(ast_node.value, ast.Tuple):
                return [elem.id for elem in ast_node.value.elts if isinstance(elem, ast.Name)]
            elif isinstance(ast_node.value, ast.Name):
                return [ast_node.value.id]


def is_use_server(type_name):
    return type_name not in ['int', 'str', 'list', 'float', 'bool']


def parse_vue(code: str) -> Component:
    """
    把vue解析为component
    """
    return {}


def get_name(return_annotation):
    if hasattr(return_annotation, "_name"):
        return getattr(return_annotation, "_name")
    if hasattr(return_annotation, "__name__"):
        return getattr(return_annotation, "__name__")
    return "Any"


def parse_func_info(fun: Callable) -> (str, List[Input], List[Output]):
    signature = inspect.signature(fun)
    parameters = signature.parameters
    output_keys = get_return_variable_names(fun)
    func_name = fun.__name__
    inputs: List[Input] = []
    outputs: List[Output] = []
    for param in list(parameters.values()):
        key = param.name
        input_config: Input = {
            "key": key,
            "name": key,
            "default": param.default if param.default != inspect._empty else None,
            "useServer": is_use_server(get_name(param.annotation)),
            "config": {"type": type_parse(get_name(param.annotation))}}
        inputs.append(input_config)
    if signature.return_annotation != inspect._empty:
        if type(signature.return_annotation) in [tuple]:
            for key, item in zip(output_keys, signature.return_annotation):
                output_config: Output = {"key": key,
                                         "name": key,
                                         "useServer": is_use_server(get_name(item)),
                                         "config": {"type": type_parse(get_name(item))}}
                outputs.append(output_config)
        else:
            type_name = get_name(signature.return_annotation)
            key = output_keys[0]
            outputs.append({"key": key,
                            "name": key,
                            "useServer": is_use_server(type_name),
                            "config": {"type": type_parse(type_name)}})
    return func_name, inputs, outputs


class NodeValue:
    """
    节点参数值的封装
    .value是消费行为，只能使用一次
    """

    def __init__(self, value, node_id, key):
        self.value = value
        self.id = node_id
        self.key = key

    def __getattr__(self, key):
        if key == 'value':
            return self.value
        else:
            return self.__getattribute__(key)
