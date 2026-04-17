from typing import Type, TypeVar, Callable, get_type_hints
from inspect import signature, Parameter
from fastapi import Depends

from app.core.ports.config import ConfigPort
from app.core.ports.repositories import (
    OneTimeTokenRepositoryPort,
    RefreshTokenRepositoryPort,
    UserRepositoryPort,
)
from app.core.ports.services import (
    EventQueuePort,
    EventPublisherPort,
    AccessTokenIssuerPort,
    AccessTokenVerifierPort,
)
from app.core.ports.transaction import TransactionPort

from app.adapters.nexus import (
    get_config,
    get_event_publisher,
    get_event_queue,
    get_access_token_issuer,
    get_access_token_verifier,
    get_transaction,
    get_user_repo,
    get_ott_repo,
    get_refresh_token_repo,
)


T = TypeVar("T")


# Port type -> provider mapping
DEPENDENCY_PROVIDERS: dict[Type, Callable] = {
    TransactionPort: get_transaction,
    UserRepositoryPort: get_user_repo,
    OneTimeTokenRepositoryPort: get_ott_repo,
    RefreshTokenRepositoryPort: get_refresh_token_repo,
    ConfigPort: get_config,
    EventQueuePort: get_event_queue,
    EventPublisherPort: get_event_publisher,
    AccessTokenIssuerPort: get_access_token_issuer,
    AccessTokenVerifierPort: get_access_token_verifier,
}


def build_use_case(use_case_class: Type[T]) -> Callable[..., T]:
    """
    Automatically build a FastAPI dependency factory for a use case.

    Inspects the use case __init__ signature, resolves parameter types
    to the corresponding providers from DEPENDENCY_PROVIDERS.

    Args:
        use_case_class: The use case class to create a factory for.

    Returns:
        A factory function with proper Depends() bindings for FastAPI.

    Raises:
        ValueError: If no provider is found for a parameter type.

    Example:
        >>> get_register_use_case = build_use_case(RegisterUserCase)
        >>> @router.post("/register")
        >>> async def register(
        >>>     use_case: RegisterUserCase = Depends(get_register_use_case)
        >>> ):
        >>>     ...
    """
    # Get __init__ signature
    sig = signature(use_case_class.__init__)
    type_hints = get_type_hints(use_case_class.__init__)
    
    # Collect parameters for the factory
    factory_params = []
    param_names = []
    
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        
        # Get parameter type
        param_type = type_hints.get(param_name)
        
        if param_type is None:
            raise ValueError(
                f"Parameter '{param_name}' in {use_case_class.__name__}.__init__ "
                f"has no type annotation"
            )
        
        # Find a provider for this type
        provider = DEPENDENCY_PROVIDERS.get(param_type)
        
        if provider is None:
            raise ValueError(
                f"No provider found for type {param_type.__name__} "
                f"(parameter '{param_name}' in {use_case_class.__name__}.__init__). "
                f"Available providers: {list(DEPENDENCY_PROVIDERS.keys())}"
            )
        
        # Create parameter with Depends()
        factory_params.append(
            Parameter(
                name=param_name,
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=Depends(provider),
                annotation=param_type,
            )
        )
        param_names.append(param_name)
    
    # Create the factory function
    def factory(**kwargs) -> T:
        return use_case_class(**kwargs)
    
    # Override the signature
    from inspect import Signature
    factory.__signature__ = Signature(
        parameters=factory_params,
        return_annotation=use_case_class,
    )
    factory.__name__ = f"get_{use_case_class.__name__}"
    
    return factory
