from collections.abc import Callable

import grpc

from app.core.security import ServicePrincipal, authenticate_service_token


def service_auth_metadata(token: str) -> list[tuple[str, str]]:
    return [("authorization", f"Bearer {token}")]


class ServiceAuthInterceptor(grpc.ServerInterceptor):
    def __init__(self, method_scopes: dict[str, set[str]] | None = None) -> None:
        self._method_scopes = method_scopes or {}

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler | None],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        handler = continuation(handler_call_details)
        if handler is None or handler.unary_unary is None:
            return handler

        required_scopes = self._method_scopes.get(handler_call_details.method, set())

        def wrapped_unary_unary(request, context):
            try:
                principal = self._authenticate(handler_call_details)
            except ValueError as exc:
                context.abort(grpc.StatusCode.UNAUTHENTICATED, str(exc))
            missing = [scope for scope in required_scopes if scope not in principal.scopes]
            if missing:
                context.abort(grpc.StatusCode.PERMISSION_DENIED, f"Missing service scopes: {', '.join(missing)}")
            return handler.unary_unary(request, context)

        return grpc.unary_unary_rpc_method_handler(
            wrapped_unary_unary,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )

    def _authenticate(self, details: grpc.HandlerCallDetails) -> ServicePrincipal:
        metadata = dict(details.invocation_metadata or [])
        authorization = metadata.get("authorization")
        if not authorization:
            raise ValueError("Missing authorization metadata")

        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise ValueError("Invalid authorization metadata format")

        try:
            return authenticate_service_token(token)
        except Exception as exc:
            raise ValueError("Invalid service token") from exc
