from typing import List
from .. import UseCase

from app.application.dto.user import RevokeRefreshTokenInputDTO
from app.application.events.security import SuspiciousRefreshTokenRevocation
from app.application.exceptions.not_found import RefreshTokenNotFound

from app.core.domain.events import BaseEvent
from app.core.domain.services.refresh_token_security_policy import (
    RefreshTokenSecurityPolicy,
)

from app.core.ports.config import ConfigPort
from app.core.ports.repositories import RefreshTokenRepositoryPort
from app.core.ports.transaction import TransactionPort
from app.core.ports.services.event_publisher import EventPublisherPort


class RevokeTokenCase(UseCase):
    """
    Application use case for revoking a refresh token.

    Handles token revocation, security risk assessment, persistence,
    and event publishing.
    """

    def __init__(
        self,
        tx: TransactionPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
        config: ConfigPort,
        event_publisher: EventPublisherPort,
    ):
        self.tx = tx
        self.refresh_token_repo = refresh_token_repo
        self.config = config
        self.event_publisher = event_publisher

    async def execute(self, data: RevokeRefreshTokenInputDTO):
        """
        Execute refresh token revocation.

        Args:
            data (RevokeTokenInputDTO): Input data containing refresh token
                and current client context.

        Raises:
            RefreshTokenNotFound: If the refresh token does not exist.
        """
        events: List[BaseEvent] = []

        async with self.tx:
            # 1. Check token exists
            rt = await self.refresh_token_repo.get_by_string(
                data.refresh_token
            )
            if not rt:
                raise RefreshTokenNotFound()

            # 2. Revoke current token
            rt.revoke()

            # 3. Check location, ip and agent match
            security_threat = RefreshTokenSecurityPolicy.assess_risk(
                token_ip=rt.client_ip,
                token_agent=rt.user_agent,
                token_location=rt.location,
                current_ip=data.client_ip,
                current_agent=data.user_agent,
                current_location=data.location,
            )
            if security_threat:
                events.append(
                    SuspiciousRefreshTokenRevocation(
                        user_id=rt.user_id,
                        token_id=rt.id,
                        client_ip=data.client_ip,
                        user_agent=data.user_agent,
                        location=data.location,
                    )
                )

            # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

            # Pull events
            events.extend(rt.pull_domain_events())

            # Save
            await self.refresh_token_repo.save(rt)

        # Publish events
        await self.event_publisher.publish(events)
