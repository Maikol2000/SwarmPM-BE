import json
from dataclasses import asdict, dataclass

import grpc

from app.core.config import get_settings
from app.schemas import AssignmentRequest, RebalanceRequest
from app.services.core_logic import choose_assignment_target, compute_workload_recommendation


@dataclass(slots=True)
class AssignmentDecision:
    assigned_to: str
    rationale: str


@dataclass(slots=True)
class RebalanceDecision:
    updates: list[dict[str, int | str]]


class CoreLogicGateway:
    def assign(self, payload: AssignmentRequest) -> AssignmentDecision:
        raise NotImplementedError

    def rebalance(self, payload: RebalanceRequest) -> RebalanceDecision:
        raise NotImplementedError


class InProcessCoreLogicGateway(CoreLogicGateway):
    def assign(self, payload: AssignmentRequest) -> AssignmentDecision:
        assigned_to, rationale = choose_assignment_target(payload)
        return AssignmentDecision(assigned_to=assigned_to, rationale=rationale)

    def rebalance(self, payload: RebalanceRequest) -> RebalanceDecision:
        updates: list[dict[str, int | str]] = []
        for member in payload.team:
            recommended, reason = compute_workload_recommendation(member.capacity_hours)
            updates.append(
                {
                    "user_id": member.user_id,
                    "recommended_capacity": recommended,
                    "reason": reason,
                }
            )
        return RebalanceDecision(updates=updates)


class GrpcCoreLogicGateway(CoreLogicGateway):
    def __init__(self, target: str, timeout_seconds: float = 2.0) -> None:
        self._target = target
        self._timeout_seconds = timeout_seconds

    def _call(self, method: str, payload: dict) -> dict:
        with grpc.insecure_channel(self._target) as channel:
            rpc = channel.unary_unary(
                method,
                request_serializer=lambda value: json.dumps(value).encode("utf-8"),
                response_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
            )
            return rpc(payload, timeout=self._timeout_seconds)

    def assign(self, payload: AssignmentRequest) -> AssignmentDecision:
        response = self._call(
            "/swarm.corelogic.v1.CoreLogicService/AssignPosition",
            payload.model_dump(),
        )
        return AssignmentDecision(
            assigned_to=response["assigned_to"],
            rationale=response["rationale"],
        )

    def rebalance(self, payload: RebalanceRequest) -> RebalanceDecision:
        response = self._call(
            "/swarm.corelogic.v1.CoreLogicService/RebalanceWorkload",
            payload.model_dump(),
        )
        return RebalanceDecision(updates=response["updates"])


class CoreLogicGatewayFactory:
    @staticmethod
    def build() -> CoreLogicGateway:
        settings = get_settings()
        if settings.core_logic_transport.lower() == "grpc":
            return GrpcCoreLogicGateway(target=settings.core_logic_grpc_target)
        return InProcessCoreLogicGateway()


class CoreLogicGrpcServer:
    def __init__(self) -> None:
        self._service = InProcessCoreLogicGateway()

    @staticmethod
    def _request_deserializer(raw: bytes) -> dict:
        return json.loads(raw.decode("utf-8"))

    @staticmethod
    def _response_serializer(payload: dict) -> bytes:
        return json.dumps(payload).encode("utf-8")

    def assign(self, request: dict, _context: grpc.ServicerContext) -> dict:
        payload = AssignmentRequest.model_validate(request)
        result = self._service.assign(payload)
        return asdict(result)

    def rebalance(self, request: dict, _context: grpc.ServicerContext) -> dict:
        payload = RebalanceRequest.model_validate(request)
        result = self._service.rebalance(payload)
        return asdict(result)

    def method_handlers(self) -> grpc.GenericRpcHandler:
        handlers = {
            "AssignPosition": grpc.unary_unary_rpc_method_handler(
                self.assign,
                request_deserializer=self._request_deserializer,
                response_serializer=self._response_serializer,
            ),
            "RebalanceWorkload": grpc.unary_unary_rpc_method_handler(
                self.rebalance,
                request_deserializer=self._request_deserializer,
                response_serializer=self._response_serializer,
            ),
        }
        return grpc.method_handlers_generic_handler("swarm.corelogic.v1.CoreLogicService", handlers)
