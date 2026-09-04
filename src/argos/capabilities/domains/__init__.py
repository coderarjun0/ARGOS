"""Domain implementations for the ARGOS Capability Ecosystem."""

from argos.capabilities.domains.application_domain import ApplicationDomain
from argos.capabilities.domains.file_system_domain import FileSystemDomain
from argos.capabilities.domains.system_info_domain import SystemInfoDomain
from argos.capabilities.domains.web_domain import WebDomain

__all__ = [
    "ApplicationDomain",
    "FileSystemDomain",
    "SystemInfoDomain",
    "WebDomain",
]
