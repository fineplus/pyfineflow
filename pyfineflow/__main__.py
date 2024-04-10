import sys
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
# from .log_conf import uvicorn_log_config
import argparse


def init_func_server(key='pyfunc', host="127.0.0.1", port=8083):
    app = FastAPI(
        title='func_server',
        description='func_server',
        version="v1.0.0",
        docs_url=f"/{key}/docs",
        openapi_url=f"/{key}/openapi.json"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class FuncReq(BaseModel):
        code: str
        params: dict

    @app.post('/func')
    def func(req: FuncReq):
        params = {'params': req.params}
        exec(f"{req.code}\nres=func(params)", params)
        return params['res']

    print(f"pyfunc_server_url:  http://{host}:{port}/{key}/func")
    uvicorn.run(app, host=host, port=port)


def main():
    parser = argparse.ArgumentParser(description="pyfunc_server for fineflow")
    parser.add_argument('-H', '--host', help='Host address', required=False, default='127.0.0.1')
    parser.add_argument('-P', '--port', help='Port number', required=False, default=8083, type=int)
    parser.add_argument('-K', '--key', help='key', required=False, default='pyfunc')
    args = parser.parse_args()

    port = args.port
    host = args.host
    key = args.key

    init_func_server(key, host, port)


if __name__ == "__main__":
    main()
