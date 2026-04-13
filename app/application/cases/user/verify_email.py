from typing import List
from .. import UseCase

from app.application.dto.user import VerifyEmailInputDTO
from app.application.exceptions.not_found import OneTimeTokenNotFound, UserNotFound

from app.core.domain.entities.one_time_token import OneTimeTokenPurpose
from app.core.domain.events import BaseEvent

from app.core.ports.repositories import OneTimeTokenRepositoryPort, UserRepositoryPort
from app.core.ports.services.event_publisher import EventPublisherPort
from app.core.ports.transaction import TransactionPort


class VerifyEmailCase(UseCase):
    """
    Application use case for verifying a user's email using a one-time token (OTT).

    Handles token validation, user email verification, persistence, and event publishing.
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

    async def execute(self, data: VerifyEmailInputDTO):
        """
        Execute the email verification process.

        Args:
            data (VerifyEmailInputDTO): Data containing the one-time token string.

        Raises:
            OneTimeTokenNotFound: If the provided token does not exist.
            UserNotFound: If the user associated with the token does not exist.
        """
        events: List[BaseEvent] = []

        async with self.tx:
            # 1. Retrieve token and check it exists
            ott = await self.ott_repo.get_by_string(data.one_time_token)
            if not ott:
                raise OneTimeTokenNotFound("Invalid token")

            # 2. Retrieve user and check it exists
            user = await self.user_repo.get_by_id(ott.user_id)
            if not user:
                raise UserNotFound()

            # 3. Use OTT and verify user email
            ott.use(OneTimeTokenPurpose.VERIFY_EMAIL)
            user.verify_email()

            # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

            # Pull events from user aggregate
            events.extend(user.pull_domain_events())

            # Save changes to repositories
            await self.user_repo.save(user)
            await self.ott_repo.save(ott)

        # Publish events outside of transaction
        await self.event_publisher.publish(events)
