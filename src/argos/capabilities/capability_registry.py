"""CapabilityRegistry implementation for tool ecosystem discovery."""

from argos.capabilities.base_domain import CapabilityDomain
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
from argos.tools.base_tool import BaseTool, ToolManifest


class CapabilityRegistry:
    """Discovery registry indexing tool manifests and capability domains."""

    def __init__(self) -> None:
        """Initializes an empty CapabilityRegistry."""
        self._domains: dict[str, CapabilityDomain] = {}
        self._tool_manifests: dict[str, ToolManifest] = {}
        self._is_frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        """True if the registry is frozen against post-initialization mutation."""
        return self._is_frozen

    def register_domain(self, domain: CapabilityDomain) -> None:
        """Registers a CapabilityDomain instance during composition phase.

        Args:
            domain: CapabilityDomain instance to register.

        Raises:
            RegistryFrozenError: If registry is frozen.
            DuplicateDomainError: If domain_id is already registered.
        """
        if self._is_frozen:
            raise RegistryFrozenError(
                "Cannot register domain on frozen CapabilityRegistry."
            )
        if domain.domain_id in self._domains:
            raise DuplicateDomainError(
                f"Domain with ID '{domain.domain_id}' is already registered."
            )
        self._domains[domain.domain_id] = domain

    def index_tool(self, tool: BaseTool) -> None:
        """Indexes a BaseTool instance manifest during composition phase.

        Args:
            tool: BaseTool instance whose manifest will be indexed.

        Raises:
            RegistryFrozenError: If registry is frozen.
            DuplicateToolIndexError: If tool_id is already indexed.
        """
        if self._is_frozen:
            raise RegistryFrozenError(
                "Cannot index tool on frozen CapabilityRegistry."
            )
        manifest = tool.manifest
        if manifest.tool_id in self._tool_manifests:
            raise DuplicateToolIndexError(
                f"Tool with ID '{manifest.tool_id}' is already indexed."
            )
        self._tool_manifests[manifest.tool_id] = manifest

    def freeze(self) -> None:
        """Freezes the registry against post-initialization mutation."""
        self._is_frozen = True

    def list_domains(self) -> tuple[DomainDescriptor, ...]:
        """Returns sorted tuple of DomainDescriptors.

        Returns:
            Tuple of DomainDescriptors sorted lexicographically by domain_id.
        """
        descriptors = [d.to_descriptor() for d in self._domains.values()]
        return tuple(sorted(descriptors, key=lambda d: d.domain_id))

    def get_domain(self, domain_id: str) -> DomainDescriptor:
        """Resolves a DomainDescriptor by domain_id.

        Args:
            domain_id: Unique domain identifier string.

        Returns:
            The matching DomainDescriptor.

        Raises:
            CapabilityDomainError: If domain_id is not registered.
        """
        if domain_id not in self._domains:
            raise CapabilityDomainError(f"Domain '{domain_id}' not found.")
        return self._domains[domain_id].to_descriptor()

    def list_tools(self) -> tuple[ToolDescriptor, ...]:
        """Returns sorted tuple of ToolDescriptors across indexed tools.

        Returns:
            Tuple of ToolDescriptors sorted lexicographically by tool_id.
        """
        descriptors = [
            ToolDescriptor(
                tool_id=m.tool_id,
                version=m.version,
                description=m.description,
                supported_actions=tuple(Action(a) for a in m.supported_actions),
                risk_class=m.risk_class,
            )
            for m in self._tool_manifests.values()
        ]
        return tuple(sorted(descriptors, key=lambda t: t.tool_id))

    def get_tool_descriptor(self, tool_id: str) -> ToolDescriptor:
        """Resolves a ToolDescriptor by tool_id.

        Args:
            tool_id: Unique tool identifier string.

        Returns:
            The matching ToolDescriptor.

        Raises:
            CapabilityRegistryError: If tool_id is not indexed.
        """
        if tool_id not in self._tool_manifests:
            raise CapabilityRegistryError(f"Tool manifest '{tool_id}' not found.")
        m = self._tool_manifests[tool_id]
        return ToolDescriptor(
            tool_id=m.tool_id,
            version=m.version,
            description=m.description,
            supported_actions=tuple(Action(a) for a in m.supported_actions),
            risk_class=m.risk_class,
        )

    def get_action_schemas(self) -> tuple[ActionSchemaDescriptor, ...]:
        """Returns sorted tuple of ActionSchemaDescriptors across all indexed tools.

        Returns:
            Tuple of ActionSchemaDescriptors sorted by (action.value, tool_id).
        """
        schemas: list[ActionSchemaDescriptor] = []
        for manifest in self._tool_manifests.values():
            for action_raw in manifest.supported_actions:
                act = Action(action_raw)
                schemas.append(
                    ActionSchemaDescriptor(
                        action=act,
                        tool_id=manifest.tool_id,
                        risk_class=manifest.risk_class,
                        parameters=manifest.parameter_specs,
                    )
                )
        return tuple(sorted(schemas, key=lambda s: (s.action.value, s.tool_id)))

    def get_schema_for_action(self, action: Action) -> ActionSchemaDescriptor:
        """Resolves the single ActionSchemaDescriptor for a given Action.

        Args:
            action: Action enum instance.

        Returns:
            The ActionSchemaDescriptor matching the Action.

        Raises:
            ActionNotFoundError: If zero tools match the Action.
            AmbiguousActionError: If multiple tools match the Action.
        """
        matching: list[ActionSchemaDescriptor] = [
            ActionSchemaDescriptor(
                action=action,
                tool_id=m.tool_id,
                risk_class=m.risk_class,
                parameters=m.parameter_specs,
            )
            for m in self._tool_manifests.values()
            if action in [Action(a) for a in m.supported_actions]
        ]
        if len(matching) == 0:
            raise ActionNotFoundError(f"No tool indexed for action '{action.value}'.")
        if len(matching) > 1:
            tool_ids = [s.tool_id for s in matching]
            raise AmbiguousActionError(
                f"Multiple tools indexed for action '{action.value}': {tool_ids}"
            )
        return matching[0]
