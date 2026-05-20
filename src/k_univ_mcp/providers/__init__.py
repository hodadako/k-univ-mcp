from __future__ import annotations

from k_univ_mcp.providers.hanyang import create_hanyang_service
from k_univ_mcp.providers.sungshin import create_sungshin_service
from k_univ_mcp.providers.yonsei import create_yonsei_service
from k_univ_mcp.providers.gachon import create_gachon_service
from k_univ_mcp.providers.inha import create_inha_service
from k_univ_mcp.providers.soongsil import create_soongsil_service
from k_univ_mcp.providers.dongguk import create_dongguk_service
from k_univ_mcp.providers.myongji import create_myongji_service

__all__ = [
    "create_hanyang_service",
    "create_sungshin_service",
    "create_yonsei_service",
    "create_gachon_service",
    "create_inha_service",
    "create_soongsil_service",
    "create_dongguk_service",
    "create_myongji_service",
]
