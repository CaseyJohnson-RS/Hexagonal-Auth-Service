from typing import List
from .. import UseCase

from app.application.dto.user import PasswordRecoverInputDTO
from app.application.exceptions.not_found import (
    OneTimeTokenNotFound,
    UserNotFound,
)

from app.core.domain.events import BaseEvent
from app.core.ports.repositories import (
    OneTimeTokenRepositoryPort,
    UserRepositoryPort,
)
from app.core.ports.transaction import TransactionPort
from app.core.ports.services.event_publisher import EventPublisherPort


class PasswordRecoverCase(UseCase):
    """
    Application use case for completing password recovery.

    Validates the recovery token, restores the user's password,
    persists changes, and publishes resulting domain events.
    """

    def __init__(
        self,
        tx: TransactionPort,
        user_repo: UserRepositoryPort,
        ott_repo: OneTimeTokenRepositoryPort,
        event_publisher: EventPublisherPort,
    ):
        self.tx = tx
        self.user_repo = user_repo
        self.ott_repo = ott_repo
        self.event_publisher = event_publisher

    async def execute(self, data: PasswordRecoverInputDTO):
        """
        Execute password recovery.

        Args:
            data (PasswordRecoverInputDTO): Input data containing
                recovery token and new password.

        Raises:
            OneTimeTokenNotFound: If the recovery token does not exist.
            UserNotFound: If the user linked to the token does not exist.
        """
        events: List[BaseEvent] = []

        async with self.tx:
            # 1. Check token
            ott = await self.ott_repo.get_by_string(
                data.password_recover_token
            )
            if not ott:
                raise OneTimeTokenNotFound(
                    "Password recover token not found"
                )

            # 2. Check user
            user = await self.user_repo.get_by_id(ott.user_id)
            if not user:
                raise UserNotFound()

            # 3. Update password
            user.recover_password(data.password)

            # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

            # Pull events
            events.extend(user.pull_domain_events())

            # Save
            await self.user_repo.save(user)
            await self.ott_repo.save(ott)

        # Publish events
        await self.event_publisher.publish(events)
