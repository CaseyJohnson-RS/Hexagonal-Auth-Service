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


# Маппинг типов на провайдеры
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
    Автоматически создает FastAPI dependency factory для use case.
    
    Анализирует __init__ use case, находит типы параметров и подставляет
    соответствующие провайдеры из DEPENDENCY_PROVIDERS.
    
    Args:
        use_case_class: Класс use case для которого нужно создать фабрику
        
    Returns:
        Функция-фабрика с правильными Depends() для использования в FastAPI
        
    Raises:
        ValueError: Если для какого-то параметра не найден провайдер
        
    Example:
        >>> get_register_use_case = build_use_case(RegisterUserCase)
        >>> # В роуте:
        >>> @router.post("/register")
        >>> async def register(
        >>>     use_case: RegisterUserCase = Depends(get_register_use_case)
        >>> ):
        >>>     ...
    """
    # Получаем сигнатуру __init__
    sig = signature(use_case_class.__init__)
    type_hints = get_type_hints(use_case_class.__init__)
    
    # Собираем параметры для фабрики
    factory_params = []
    param_names = []
    
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        
        # Получаем тип параметра
        param_type = type_hints.get(param_name)
        
        if param_type is None:
            raise ValueError(
                f"Parameter '{param_name}' in {use_case_class.__name__}.__init__ "
                f"has no type annotation"
            )
        
        # Ищем провайдер для этого типа
        provider = DEPENDENCY_PROVIDERS.get(param_type)
        
        if provider is None:
            raise ValueError(
                f"No provider found for type {param_type.__name__} "
                f"(parameter '{param_name}' in {use_case_class.__name__}.__init__). "
                f"Available providers: {list(DEPENDENCY_PROVIDERS.keys())}"
            )
        
        # Создаем параметр с Depends()
        factory_params.append(
            Parameter(
                name=param_name,
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=Depends(provider),
                annotation=param_type,
            )
        )
        param_names.append(param_name)
    
    # Создаем функцию-фабрику
    def factory(**kwargs) -> T:
        return use_case_class(**kwargs)
    
    # Подменяем сигнатуру
    from inspect import Signature
    factory.__signature__ = Signature(
        parameters=factory_params,
        return_annotation=use_case_class,
    )
    factory.__name__ = f"get_{use_case_class.__name__}"
    
    return factory
