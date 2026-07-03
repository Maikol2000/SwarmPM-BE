from concurrent.futures import ThreadPoolExecutor

import grpc

from app.grpc.auth import ServiceAuthInterceptor
from app.services.core_logic_gateway import CoreLogicGrpcServer


def build_core_logic_grpc_server() -> grpc.Server:
    interceptor = ServiceAuthInterceptor(
        method_scopes={
            "/swarm.corelogic.v1.CoreLogicService/AssignPosition": {"corelogic:assign"},
            "/swarm.corelogic.v1.CoreLogicService/RebalanceWorkload": {"corelogic:rebalance"},
        }
    )
    server = grpc.server(ThreadPoolExecutor(max_workers=10), interceptors=[interceptor])
    service = CoreLogicGrpcServer()
    server.add_generic_rpc_handlers((service.method_handlers(),))
    return server
