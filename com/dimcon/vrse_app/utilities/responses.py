"""
Shared helpers for building HTTP responses in Lambda.
This class is stateless and domain‑agnostic.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

class ResponseBuilder:
    """
    A helper class for constructing HTTP responses in AWS Lambda.
    This class is designed to be stateless and domain-agnostic,
    so that it can be reused across different parts of the application.
    """

    _DEFAULT_HEADERS: dict[str, str] = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

    @classmethod
    def build_response(
        cls,
        status_code: int,
        body: Mapping[str, Any] | list[Any] | str,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a standard API Gateway proxy response.

        Parameters
        ----------
        status_code : int
            HTTP status code to return.
        body : dict | list | str
            Response payload; will be JSON‑encoded.
        headers : dict[str, str] | None, optional
            Extra headers to merge with the defaults.

        Returns
        -------
        dict[str, Any]
            Dict shaped exactly as API Gateway expects.
        """
        merged_headers = {**cls._DEFAULT_HEADERS, **(headers or {})}
        return {
            "statusCode": status_code,
            "headers": merged_headers,
            "body": json.dumps(body, default=str),
        }
