"""Unit tests for the ARGOS Capability Ecosystem & Domain Registry subsystem."""

from dataclasses import FrozenInstanceError

import pytest

from argos.capabilities.capability_registry import CapabilityRegistry
from argos.capabilities.domains import (
    ApplicationDomain,
    FileSystemDomain,
    SystemInfoDomain,
    WebDomain,
)
from argos.capabilities.exceptions import (
    ActionNotFoundError,
    AmbiguousActionError,
    CapabilityDomainError,
    CapabilityRegistryError,
    DuplicateDomainError,
    DuplicateToolIndexError,
    RegistryFrozenError,
)
from argos.capabilities.models import (
    ActionSchemaDescriptor,
    DomainDescriptor,
    ToolDescriptor,
)
from argos.planning.action import Action
from argos.tools.base_tool import (
    BaseTool,
    ParameterSpec,
    RiskClass,
    ToolManifest,
    ToolResult,
)


class DummyTool(BaseTool):
    """Dummy BaseTool implementation for testing CapabilityRegistry indexing."""

    def __init__(
        self,
        tool_id: str,
        supported_actions: tuple[str, ...],
        risk_class: RiskClass = RiskClass.READ_ONLY,
    ) -> None:
        """Initializes DummyTool with provided attributes."""
        self._manifest = ToolManifest(
            tool_id=tool_id,
            version="1.0.0",
            description=f"Dummy tool {tool_id}",
            supported_actions=supported_actions,
            risk_class=risk_class,
            parameter_specs=(
                ParameterSpec(name="target", param_type=str, required=True),
            ),
        )

    @property
    def manifest(self) -> ToolManifest:
        """Returns dummy tool manifest."""
        return self._manifest

    def validate_parameters(self, parameters: dict) -> None:
        """Validates parameters (no-op for dummy tool)."""

    def run(self, parameters: dict) -> ToolResult:
        """Executes dummy tool run (no-op)."""
        return ToolResult(success=True, message="Executed dummy tool")


def test_models_immutability() -> None:
    """Verifies that discovery DTOs are frozen and immutable."""
    action_desc = ActionSchemaDescriptor(
        action=Action.OPEN_APP,
        tool_id="test_tool",
        risk_class=RiskClass.READ_ONLY,
        parameters=(),
    )
    assert action_desc.action == Action.OPEN_APP
    assert action_desc.tool_id == "test_tool"

    with pytest.raises(FrozenInstanceError):
        action_desc.tool_id = "other_tool"  # type: ignore[misc]

    domain_desc = DomainDescriptor(
        domain_id="domain.test",
        name="Test Domain",
        description="Description",
        supported_actions=(Action.OPEN_APP,),
    )
    assert domain_desc.domain_id == "domain.test"

    with pytest.raises(FrozenInstanceError):
        domain_desc.name = "New Name"  # type: ignore[misc]

    tool_desc = ToolDescriptor(
        tool_id="test_tool",
        version="1.0.0",
        description="Description",
        supported_actions=(Action.OPEN_APP,),
        risk_class=RiskClass.READ_ONLY,
    )
    assert tool_desc.tool_id == "test_tool"

    with pytest.raises(FrozenInstanceError):
        tool_desc.version = "2.0.0"  # type: ignore[misc]


def test_exceptions_hierarchy() -> None:
    """Verifies capability exception inheritance hierarchy."""
    assert issubclass(CapabilityDomainError, CapabilityRegistryError)
    assert issubclass(ActionNotFoundError, CapabilityRegistryError)
    assert issubclass(AmbiguousActionError, CapabilityRegistryError)
    assert issubclass(RegistryFrozenError, CapabilityRegistryError)
    assert issubclass(DuplicateDomainError, CapabilityRegistryError)
    assert issubclass(DuplicateToolIndexError, CapabilityRegistryError)


def test_concrete_domains() -> None:
    """Verifies metadata properties for concrete CapabilityDomains."""
    app_dom = ApplicationDomain()
    assert app_dom.domain_id == "domain.application"
    assert app_dom.name == "Application Execution Domain"
    assert Action.OPEN_APP in app_dom.supported_actions
    assert Action.CLOSE_APP in app_dom.supported_actions
    desc = app_dom.to_descriptor()
    assert desc.domain_id == "domain.application"

    fs_dom = FileSystemDomain()
    assert fs_dom.domain_id == "domain.filesystem"
    assert Action.READ_FILE in fs_dom.supported_actions
    assert Action.WRITE_FILE in fs_dom.supported_actions
    assert Action.CREATE_FILE in fs_dom.supported_actions
    assert Action.LIST_DIR in fs_dom.supported_actions

    sys_dom = SystemInfoDomain()
    assert sys_dom.domain_id == "domain.system_info"
    assert Action.QUERY_SYS_INFO in sys_dom.supported_actions

    web_dom = WebDomain()
    assert web_dom.domain_id == "domain.web"
    assert Action.SEARCH_WEB in web_dom.supported_actions


def test_capability_registry_registration_and_indexing() -> None:
    """Verifies domain registration, tool indexing, and lookup methods."""
    registry = CapabilityRegistry()
    assert not registry.is_frozen

    app_dom = ApplicationDomain()
    registry.register_domain(app_dom)

    tool1 = DummyTool(
        tool_id="dummy_app",
        supported_actions=("open_app",),
        risk_class=RiskClass.READ_ONLY,
    )
    registry.index_tool(tool1)

    domains = registry.list_domains()
    assert len(domains) == 1
    assert domains[0].domain_id == "domain.application"

    dom_desc = registry.get_domain("domain.application")
    assert dom_desc.name == "Application Execution Domain"

    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0].tool_id == "dummy_app"

    tool_desc = registry.get_tool_descriptor("dummy_app")
    assert tool_desc.tool_id == "dummy_app"
    assert tool_desc.risk_class == RiskClass.READ_ONLY


def test_capability_registry_freeze_lifecycle() -> None:
    """Verifies freeze semantics and post-freeze mutation rejection."""
    registry = CapabilityRegistry()
    registry.register_domain(ApplicationDomain())
    registry.freeze()

    assert registry.is_frozen

    with pytest.raises(RegistryFrozenError, match="Cannot register domain"):
        registry.register_domain(FileSystemDomain())

    dummy = DummyTool(tool_id="dummy", supported_actions=("read_file",))
    with pytest.raises(RegistryFrozenError, match="Cannot index tool"):
        registry.index_tool(dummy)


def test_capability_registry_duplicates() -> None:
    """Verifies duplicate domain and tool indexing rejection."""
    registry = CapabilityRegistry()
    registry.register_domain(ApplicationDomain())

    with pytest.raises(DuplicateDomainError, match="already registered"):
        registry.register_domain(ApplicationDomain())

    tool = DummyTool(tool_id="dummy", supported_actions=("open_app",))
    registry.index_tool(tool)

    with pytest.raises(DuplicateToolIndexError, match="already indexed"):
        registry.index_tool(tool)


def test_capability_registry_discovery_schemas() -> None:
    """Verifies get_action_schemas sorting and parameter extraction."""
    registry = CapabilityRegistry()

    tool_z = DummyTool(
        tool_id="z_tool",
        supported_actions=("read_file",),
        risk_class=RiskClass.READ_ONLY,
    )
    tool_a = DummyTool(
        tool_id="a_tool",
        supported_actions=("open_app",),
        risk_class=RiskClass.READ_ONLY,
    )
    registry.index_tool(tool_z)
    registry.index_tool(tool_a)

    schemas = registry.get_action_schemas()
    assert len(schemas) == 2
    # Sorting order by action.value: 'open_app' comes before 'read_file'
    assert schemas[0].action == Action.OPEN_APP
    assert schemas[0].tool_id == "a_tool"
    assert schemas[1].action == Action.READ_FILE
    assert schemas[1].tool_id == "z_tool"


def test_capability_registry_get_schema_for_action() -> None:
    """Verifies single action resolution, missing action, and ambiguity."""
    registry = CapabilityRegistry()

    tool1 = DummyTool(
        tool_id="tool_1",
        supported_actions=("open_app",),
        risk_class=RiskClass.READ_ONLY,
    )
    tool2 = DummyTool(
        tool_id="tool_2",
        supported_actions=("open_app",),
        risk_class=RiskClass.READ_ONLY,
    )
    tool3 = DummyTool(
        tool_id="tool_3",
        supported_actions=("search_web",),
        risk_class=RiskClass.NETWORK_READ,
    )

    registry.index_tool(tool3)

    # 1 matching tool
    schema = registry.get_schema_for_action(Action.SEARCH_WEB)
    assert schema.tool_id == "tool_3"
    assert schema.risk_class == RiskClass.NETWORK_READ

    # 0 matching tools
    with pytest.raises(ActionNotFoundError, match="No tool indexed for action"):
        registry.get_schema_for_action(Action.OPEN_APP)

    # Ambiguous matching tools (>1 tools)
    registry.index_tool(tool1)
    registry.index_tool(tool2)

    with pytest.raises(AmbiguousActionError, match="Multiple tools indexed for action"):
        registry.get_schema_for_action(Action.OPEN_APP)


def test_capability_registry_missing_lookups() -> None:
    """Verifies exception handling when querying non-existent domains or tools."""
    registry = CapabilityRegistry()

    err_msg_dom = "Domain 'domain.missing' not found"
    with pytest.raises(CapabilityDomainError, match=err_msg_dom):
        registry.get_domain("domain.missing")

    err_msg_tool = "Tool manifest 'missing_tool' not found"
    with pytest.raises(CapabilityRegistryError, match=err_msg_tool):
        registry.get_tool_descriptor("missing_tool")
