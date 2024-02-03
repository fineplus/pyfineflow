from typing import Union, Optional, List, Literal, Any, TypedDict
from pydantic import BaseModel, Field



class ParamConfigModel(BaseModel):
    type: Union[str, Literal["string", "integer", "float", "boolean", "enum", "any", "custom"]]
    config: Optional[dict]


class ParamModel(BaseModel):
    name: str
    des: Optional[str]
    config: ParamConfigModel


# 组件输入参数的显示配置
class InputShowModel(BaseModel):
    # all为False将全部隐藏
    all: Optional[bool]
    # 输入组件是否显示,没有input的时候会显示名称
    input: Optional[bool]
    # 端口是否显示
    port: Optional[bool]
    # 名称是否显示
    name: Optional[bool]
    # 名称显示的位置,默认内部
    namePosition: Optional[Literal["outer", "inner"]]


class InputModel(ParamModel):
    key: str
    default: Optional[Any]
    useServer: Optional[bool]
    show: Optional[InputShowModel]


class OutputModel(ParamModel):
    key: str
    useServer: Optional[bool]
    show: Optional[InputShowModel]


class ComponentModel(BaseModel):
    template: str
    options: str
    css: str


class FuncModel(BaseModel):
    lang: Optional[Literal["python", "javascript"]]
    code: str


class NodeUiModel(BaseModel):
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]
    titleColor: Optional[str]
    titleBg: Optional[str]
    bg: Optional[str]
    component: Optional[ComponentModel]


class NodeModel(BaseModel):
    name: Optional[str]
    key: Optional[str]
    # 点所属server的key，例如python服务，java服务等
    serverKey: Optional[str]
    func: Optional[FuncModel]
    input: Optional[List[InputModel]]
    output: Optional[List[OutputModel]]
    ui: Optional[NodeUiModel]
    des: Optional[str]


class ParamConfig(TypedDict, total=False):
    type: Union[str, Literal["string", "integer", "float", "boolean", "enum", "any", "custom"]]
    config: Optional[dict]


class Param(TypedDict, total=False):
    name: str
    des: Optional[str]
    config: ParamConfig


class InputShow(TypedDict, total=False):
    all: Optional[bool]
    input: Optional[bool]
    port: Optional[bool]
    name: Optional[bool]
    namePosition: Optional[Literal["outer", "inner"]]


class Input(Param, total=False):
    key: str
    default: Optional[Any]
    useServer: Optional[bool]
    show: Optional[InputShow]


class Output(Param, total=False):
    key: str
    useServer: Optional[bool]


class Component(TypedDict, total=False):
    template: str
    options: str
    css: str


class Func(TypedDict, total=False):
    lang: Optional[Literal["python", "javascript"]]
    code: str


class NodeUi(TypedDict, total=False):
    x: Optional[float]
    y: Optional[float]
    width: Optional[float]
    height: Optional[float]
    titleColor: Optional[str]
    titleBg: Optional[str]
    bg: Optional[str]
    component: Optional[Component]


class NodeExtendConfig(TypedDict, total=False):
    mod: Optional[str]
    category: Optional[str]


class Node(NodeExtendConfig, total=False):
    name: Optional[str]
    key: Optional[str]
    serverKey: Optional[str]
    func: Optional[Func]
    input: Optional[List[Input]]  # Changed alias to in_
    output: Optional[List[Output]]
    ui: Optional[NodeUi]
    des: Optional[str]
