import asyncio
import os
import random
import threading
import traceback
from asyncio import create_task
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from .log_conf import uvicorn_log_config
from .schemas import Input, Output, Node
from .utils import parse_func_info, NodeValue, type_parse, read_text_if_path_exit, recursive_update


class record:
    recording = False
    nodes = []
    edges = []


class InParam(BaseModel):
    value: Optional[Any] = None
    useServer: Optional[bool] = False


class RunNodeReq(BaseModel):
    workId: str
    nodeId: str
    params: Dict[str, InParam]
    key: str


class StateSync:
    def __int__(self):
        pass


class NodeCtx:
    def __init__(self, work_id, node_id, work_manager):
        self.work_id = work_id
        self.node_id = node_id
        self.work_manager: WorkManager = work_manager

    def update_state(self, path, value):
        self.work_manager.update_state(self.node_id, path, value)


# 将一些共用实例，节点函数执行时本身的各种信息存在这个ctx里面，这样节点函数执行的时候就知道自己的节点id等等信息，同时还可以调用一些ws通信
def get_ctx(func) -> NodeCtx:
    ctx = getattr(getattr(func, 'real_func', {}), 'ctx')
    if ctx:
        func.real_func.ctx = None
    return ctx


def marge_list_dict(items_a: List[Dict], items_b: List[Dict]):
    if not items_a:
        return items_b or []
    if not items_b:
        return items_a or []
    items_dict = {}
    for item in items_a:
        item = item.copy()
        key = item['key']
        items_dict[key] = item
    for item in items_b:
        item = item.copy()
        key = item['key']
        if key not in items_dict:
            items_dict[key] = item
        else:
            item.update(items_dict[key])
            items_dict[key] = item
    return list(items_dict.items())


class Fine:
    def __init__(self, key: str, mod: str, use_ws=False):
        self.key = key
        self.mod = mod
        self.nodes = []
        self.node_conf_map = {}
        self.flows = []
        self.app = None
        self.work_map = {}
        self.node_func_map = {}
        # 节点状态信息的缓存，首次连接ws的时候，同步全部信息，断开重连的时候也是，这个功能是可选的，不是所有后端都需要和前端实时通信
        self.use_ws = use_ws

    def node(self, category: str = '', name: str = None, config: Node = {},
             vue=None):
        config = config.copy() if config else {}

        def warp_func(func):
            node_conf: Node = {}
            func_name, func_inputs, func_outputs = parse_func_info(func)
            node_conf['name'] = name or func_name
            node_key = f"{self.key}-{category}-{func_name}"
            node_conf['key'] = node_key
            node_conf['mod'] = self.mod
            config_input = config.get("input")
            config_output = config.get("output")
            if 'input' in config:
                del config['input']
            if 'output' in config:
                del config['output']
            node_conf['input'] = marge_list_dict(config_input, func_inputs)
            node_conf['output'] = marge_list_dict(config_output, func_outputs)
            node_conf['category'] = category
            if 'ui' not in node_conf:
                node_conf['ui'] = {}
            node_conf['ui']['component'] = read_text_if_path_exit(vue)
            if config:
                recursive_update(node_conf, config)
            self.nodes.append(node_conf)
            self.node_conf_map[node_key] = node_conf
            self.node_func_map[node_key] = func

            def warp(*args, **kwargs):
                return func(*args, **kwargs)
                # if record.recording:
                #     return self.make_res(node_conf, *args, **kwargs)
                # else:
                #     return func(*args, **kwargs)

            warp.real_func = func
            return warp

        return warp_func

    def init_app(self):
        sys_name = self.key
        app = FastAPI(
            title=sys_name,
            description=sys_name,
            version="v1.0.0",
            docs_url=f"/{self.key}/docs",
            openapi_url=f"/{self.key}/openapi.json"
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.app = app
        return self.app

    def init_server(self, host: str = "127.0.0.1", port: int = 8080):
        app = self.init_app()
        app.router.prefix = f"/{self.key}"

        class FuncReq(BaseModel):
            code: str
            params: dict

        @self.app.router.post('/func')
        def func(req: FuncReq):
            vars = {'params': req.params}
            exec(f"{req.code}\nres=func(params)", vars)
            return vars['res']

        @self.app.router.post('/run_node')
        def run_node(req: RunNodeReq):
            work_id = req.workId
            if work_id not in self.work_map:
                self.work_map[work_id] = WorkManager(work_id)
            node_key = req.key
            node_id = req.nodeId
            req_dict = req.model_dump()
            try:
                res = self.run_node(
                    work_id, node_id, node_key, req_dict['params'])
            except Exception as e:
                error_traceback = traceback.format_exc()
                # 将错误信息按行分割成列表
                traceback_lines = error_traceback.splitlines()
                # 获取最后五行的错误信息
                last_five_lines = traceback_lines[-5:]
                error_str = "\n".join(last_five_lines)
                print(error_str)
                return {'state': 0, 'msg': f'{error_str}', 'data': None}
            return {'state': 1, 'msg': '', 'data': res}

        @app.websocket("/ws/{work_id}")
        async def websocket_endpoint(websocket: WebSocket, work_id: str):
            await websocket.accept()
            if work_id not in self.work_map:
                self.work_map[work_id] = WorkManager(work_id)
            work_manager = self.work_map[work_id]
            ws_manager = WsManage(websocket, work_manager.gener_data)
            work_manager.ws_manager = ws_manager
            await ws_manager.run()

        @self.app.router.post('/get_nodes')
        def get_nodes():
            return {'state': 1, 'data': self.nodes, 'mod': self.mod}

        print(f"docs:  http://127.0.0.1:{port}{app.docs_url}")
        print(f"server url:  http://127.0.0.1:{port}/{self.key}")
        print(f"server key:  {self.key}")
        uvicorn.run(app, log_config=uvicorn_log_config, host=host, port=port)

    def create_work(self, work_id):
        if work_id not in self.work_map:
            self.work_map[work_id] = WorkManager(work_id)

    def run_node(self, work_id, node_id, node_key, params: Dict[str, InParam]):
        work: WorkManager = self.work_map[work_id]
        conf: Node = self.node_conf_map[node_key]
        func = self.node_func_map[node_key]
        kwargs = {}
        for key, item in params.items():
            user_server = item.get('useServer', False)
            value = item['value']
            if user_server:
                value = work.get_out_value_by_index(value)
            kwargs[key] = value
        func.ctx = NodeCtx(work_id, node_id, work)
        res = func(**kwargs)
        out_val_map = {}
        if len(conf['output']) == 1:
            key = conf['output'][0]['key']
            val = res
            val_conf = conf['output'][0]
            if val_conf.get('useServer', False):
                val_address = work.set_out_val(node_id, key, val)
                out_val_map[key] = val_address
            else:
                if val is not None:
                    out_val_map[key] = val
        else:
            for i, val_conf in enumerate(conf['output']):
                val = res[i]
                key = val_conf['key']
                if val_conf.get('useServer', False):
                    val_address = work.set_out_val(node_id, key, val)
                    out_val_map[key] = val_address
                else:
                    if val is not None:
                        out_val_map[key] = val
        return out_val_map


class WorkManager:
    def __init__(self, work_id: str):
        self.work_id = work_id
        # 节点输出值的缓存
        self.out_val_map = {}
        # 节点状态信息的缓存，首次连接ws的时候，同步全部信息，断开重连的时候也是，这个功能是可选的，不是所有后端都需要和前端实时通信
        self.state_map = {}
        self.ws = None
        self.ws_manager: WsManage = None

    def get_out_val(self, node_id, out_port_key):
        return self.out_val_map.get(node_id, {}).get(out_port_key, None)

    def set_out_val(self, node_id, out_port_key, value):
        if node_id not in self.out_val_map:
            self.out_val_map[node_id] = {}
        self.out_val_map[node_id][out_port_key] = value
        return f"{node_id}${out_port_key}"

    def get_out_value_by_index(self, index):
        # 通过index索引去寻找值，这个index是个复合字符串，f"{node_id}${key}"
        [node_id, key] = index.split('$')
        return self.get_out_val(node_id, key)

    def gener_data(self, event: str, data=None):
        if event == 'get_all_state':
            if self.ws_manager:
                self.ws_manager.send_json(
                    {'event': 'get_all_state', 'data': self.state_map})

    def update_state(self, node_id, path, value):
        if node_id not in self.state_map:
            self.state_map[node_id] = {}
        node_states = self.state_map[node_id]
        node_states[path] = value
        if self.ws_manager:
            self.ws_manager.send_json(
                {'event': 'update_node_state', 'data': {'path': path, 'node_id': node_id, 'value': value}})


class WsManage:
    def __init__(self, ws: WebSocket, gener_data: callable):
        self.ws = ws
        self.gener_data = gener_data

    async def run(self):
        while True:
            try:
                data = await self.ws.receive_json()
                self.gener_data_run(data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(e)

    def gener_data_run(self, data):
        event = data.get('event')
        data = data.get('data')
        self.gener_data(event, data)

    def send_json(self, data):
        threading.Thread(target=asyncio.run, args=(
            self.ws.send_json(data),)).start()
