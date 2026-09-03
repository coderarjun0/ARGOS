"""ArgosRuntime composition root and application facade."""

import logging
from typing import Any, Self

from argos.brain.brain_core import BrainCore
from argos.brain.brain_result import BrainResult
from argos.brain.brain_status import BrainStatus
from argos.brain.capability_manager import create_default_capability_manager
from argos.brain.exceptions import (
    MaxCyclesExceededError,
    ProcessingError,
    ValidationError,
)
from argos.execution.exceptions import ExecutionError
from argos.execution.execution_status import ExecutionStatus
from argos.input.exceptions import InputProcessingError
from argos.input.input_request import InputRequest
from argos.intent.exceptions import IntentAnalysisError
from argos.memory.memory_engine import MemoryEngine
from argos.memory.models import AuthorizationRecord
from argos.planning.exceptions import PlanningError
from argos.policy.exceptions import PolicyEvaluationError
from argos.policy.policy_engine import PolicyEngine
from argos.runtime.exceptions import (
    RuntimeInitializationError,
    RuntimeShutdownError,
)
from argos.runtime.models import RuntimeResponse, RuntimeStatus

logger = logging.getLogger(__name__)


class ArgosRuntime:
    """Composition Root and application facade for ARGOS.

    Coordinates subsystem lifecycle, dependency injection, resource cleanup,
    and high-level request delegation to BrainCore.
    """

    def __init__(
        self,
        brain_core: BrainCore,
        memory_engine: MemoryEngine | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        """Initializes ArgosRuntime with provided or injected dependencies.

        Args:
            brain_core: Primary BrainCore instance for cognitive loop execution.
            memory_engine: Optional MemoryEngine instance.
            policy_engine: Optional PolicyEngine instance.
        """
        self._brain_core = brain_core
        self._memory_engine = memory_engine
        self._policy_engine = policy_engine
        self._is_shutdown = False

    @classmethod
    def create_default(cls, db_path: str = ":memory:") -> "ArgosRuntime":
        """Factory method constructing a default ArgosRuntime.

        Instantiates SQLiteStore, MemoryEngine, PolicyEngine, CapabilityManager,
        and BrainCore in proper dependency order.

        Args:
            db_path: Path to SQLite database file or ':memory:' for in-memory DB.

        Returns:
            A fully wired ArgosRuntime instance.

        Raises:
            RuntimeInitializationError: If dependency construction fails.
        """
        try:
            memory_engine = MemoryEngine(db_path=db_path)
            policy_engine = PolicyEngine(memory_engine=memory_engine)

            cap_mgr = create_default_capability_manager(
                memory_engine=memory_engine,
                policy_engine=policy_engine,
            )
            brain_core = BrainCore(capability_manager=cap_mgr)

            return cls(
                brain_core=brain_core,
                memory_engine=memory_engine,
                policy_engine=policy_engine,
            )
        except Exception as err:
            raise RuntimeInitializationError(
                f"Failed to initialize ArgosRuntime: {err}"
            ) from err

    @property
    def brain_core(self) -> BrainCore:
        """Provides access to the underlying BrainCore instance."""
        return self._brain_core

    @property
    def memory_engine(self) -> MemoryEngine | None:
        """Provides access to the underlying MemoryEngine instance."""
        return self._memory_engine

    @property
    def policy_engine(self) -> PolicyEngine | None:
        """Provides access to the underlying PolicyEngine instance."""
        return self._policy_engine

    @property
    def is_shutdown(self) -> bool:
        """Returns True if the runtime has been closed."""
        return self._is_shutdown

    def handle(
        self,
        request: InputRequest | str,
        session_id: str = "default",
        authorization: AuthorizationRecord | None = None,
        context: dict[str, Any] | None = None,
    ) -> RuntimeResponse:
        """Processes a single request through the BrainCore cognitive loop.

        Args:
            request: Raw input string or InputRequest instance.
            session_id: Session identifier string.
            authorization: Optional user authorization record for confirmation.
            context: Optional initial context dictionary for working memory.

        Returns:
            A compiled RuntimeResponse container.

        Raises:
            RuntimeShutdownError: If called on a shutdown runtime.
        """
        if self._is_shutdown:
            raise RuntimeShutdownError("Cannot process request: runtime is shut down.")

        try:
            brain_result: BrainResult = self._brain_core.process(
                request=request,
                authorization=authorization,
                session_id=session_id,
                context=context,
            )
            return self._map_brain_result_to_response(session_id, brain_result)

        except (InputProcessingError, ValidationError) as err:
            logger.warning("Input validation/processing failed: %s", err)
            return RuntimeResponse(
                status=RuntimeStatus.MALFORMED_INPUT,
                session_id=session_id,
                error_message=str(err),
            )

        except IntentAnalysisError as err:
            logger.warning("Intent analysis failed: %s", err)
            return RuntimeResponse(
                status=RuntimeStatus.INTENT_UNRESOLVED,
                session_id=session_id,
                error_message=str(err),
            )

        except PlanningError as err:
            logger.warning("Planning failed: %s", err)
            return RuntimeResponse(
                status=RuntimeStatus.PLANNING_FAILED,
                session_id=session_id,
                error_message=str(err),
            )

        except PolicyEvaluationError as err:
            logger.info("Policy evaluation requested user action: %s", err)
            return RuntimeResponse(
                status=RuntimeStatus.WAITING_FOR_USER,
                session_id=session_id,
                output=str(err),
                error_message=str(err),
            )

        except MaxCyclesExceededError as err:
            logger.warning("Max cycles exceeded: %s", err)
            return RuntimeResponse(
                status=RuntimeStatus.MAX_CYCLES_EXCEEDED,
                session_id=session_id,
                error_message=str(err),
            )

        except ProcessingError as err:
            err_msg = str(err)
            if (
                "DENY" in err_msg
                or "denied" in err_msg.lower()
                or "policy" in err_msg.lower()
            ):
                logger.warning("Policy denied capability execution: %s", err)
                return RuntimeResponse(
                    status=RuntimeStatus.POLICY_DENIED,
                    session_id=session_id,
                    error_message=err_msg,
                )
            logger.error("Capability processing error: %s", err)
            return RuntimeResponse(
                status=RuntimeStatus.SYSTEM_ERROR,
                session_id=session_id,
                error_message=err_msg,
            )

        except ExecutionError as err:
            logger.warning("Execution error: %s", err)
            return RuntimeResponse(
                status=RuntimeStatus.EXECUTION_FAILED,
                session_id=session_id,
                error_message=str(err),
            )

        except Exception as err:
            logger.error("Unexpected system error in runtime: %s", err, exc_info=True)
            return RuntimeResponse(
                status=RuntimeStatus.SYSTEM_ERROR,
                session_id=session_id,
                error_message=f"System error: {err}",
            )

    def _map_brain_result_to_response(
        self, session_id: str, brain_result: BrainResult
    ) -> RuntimeResponse:
        """Maps a BrainResult to an external RuntimeResponse DTO."""
        output_str = self._format_output(brain_result)

        if brain_result.brain_status == BrainStatus.COMPLETED:
            if (
                brain_result.execution_result
                and brain_result.execution_result.status != ExecutionStatus.SUCCESS
            ):
                err_msg = (
                    brain_result.execution_result.metadata.get("error")
                    or output_str
                )
                status = RuntimeStatus.EXECUTION_FAILED
                if "policy deny" in output_str.lower() or "deny" in output_str.lower():
                    status = RuntimeStatus.POLICY_DENIED
                return RuntimeResponse(
                    status=status,
                    session_id=session_id,
                    output=output_str,
                    brain_result=brain_result,
                    error_message=err_msg,
                )
            return RuntimeResponse(
                status=RuntimeStatus.SUCCESS,
                session_id=session_id,
                output=output_str,
                brain_result=brain_result,
            )

        if brain_result.brain_status == BrainStatus.WAITING_FOR_USER:
            return RuntimeResponse(
                status=RuntimeStatus.WAITING_FOR_USER,
                session_id=session_id,
                output=output_str,
                brain_result=brain_result,
            )

        if brain_result.brain_status == BrainStatus.FAILED:
            status = RuntimeStatus.EXECUTION_FAILED
            if "policy" in output_str.lower() or "deny" in output_str.lower():
                status = RuntimeStatus.POLICY_DENIED
            return RuntimeResponse(
                status=status,
                session_id=session_id,
                output=output_str,
                brain_result=brain_result,
                error_message=output_str,
            )

        if brain_result.brain_status == BrainStatus.TERMINATED:
            return RuntimeResponse(
                status=RuntimeStatus.MAX_CYCLES_EXCEEDED,
                session_id=session_id,
                output=output_str,
                brain_result=brain_result,
                error_message="Maximum cognitive cycles exceeded.",
            )

        return RuntimeResponse(
            status=RuntimeStatus.SUCCESS,
            session_id=session_id,
            output=output_str,
            brain_result=brain_result,
        )

    def _format_output(self, result: BrainResult) -> str:
        """Formats human-readable output text from a BrainResult."""
        if result.execution_result and result.execution_result.step_results:
            msgs = [
                sr.message
                for sr in result.execution_result.step_results
                if sr.message
            ]
            if msgs:
                return "\n".join(msgs)
        if result.decision_history:
            return result.decision_history[-1]
        return "Operation completed."

    def close(self) -> None:
        """Flushes memory and releases runtime resources."""
        if self._is_shutdown:
            return
        self._is_shutdown = True
        if self._memory_engine and hasattr(self._memory_engine, "close"):
            try:
                self._memory_engine.close()
            except Exception as err:
                logger.debug("Error closing MemoryEngine: %s", err)
        logger.info("ArgosRuntime shutdown completed.")

    def __enter__(self) -> Self:
        """Context manager entry point."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit point."""
        self.close()
