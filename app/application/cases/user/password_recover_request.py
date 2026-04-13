from typing import List
from .. import UseCase

from app.application.dto.user import PasswordRecoverRequestInputDTO
from app.application.exceptions.not_found import UserNotFound

from app.core.domain.events import BaseEvent
from app.core.domain.services.password_recover import PasswordRecoverService

from app.core.ports.config import ConfigPort
from app.core.ports.repositories import (
    OneTimeTokenRepositoryPort,
    UserRepositoryPort,
)
from app.core.ports.transaction import TransactionPort
from app.core.ports.services.event_publisher import EventPublisherPort


class PasswordRecoverRequestCase(UseCase):
    """
    Application use case for initiating password recovery.

    Handles user lookup, one-time token generation,
    persistence, and event publishing.
    """

    def __init__(
        self,
        tx: TransactionPort,
        user_repo: UserRepositoryPort,
        ott_repo: OneTimeTokenRepositoryPort,
        config: ConfigPort,
        event_publisher: EventPublisherPort,
    ):
        self.tx = tx
        self.user_repo = user_repo
        self.ott_repo = ott_repo
        self.config = config
        self.event_publisher = event_publisher

    async def execute(self, data: PasswordRecoverRequestInputDTO):
        """
        Execute password recovery request.

        Args:
            data (PasswordRecoverRequestInputDTO): Input data containing user email.

        Raises:
            UserNotFound: If the user does not exist.
        """
        events: List[BaseEvent] = []

        async with self.tx:
            # 1. Check user exists and email verified
            user = await self.user_repo.get_by_email(data.email)
            if not user:
                raise UserNotFound()

            # 2. Request password recover
            ott, token_string = PasswordRecoverService.request_password_recover(
                user=user,
                token_length=self.config.password_recover_token_len(),
                token_expiry=self.config.password_recover_token_exp(),
            )

            # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

            # Pull events
            events.extend(user.pull_domain_events())

            # Save
            await self.user_repo.save(user)
            await self.ott_repo.save(ott)

        # Publish events
        await self.event_publisher.publish(events)
