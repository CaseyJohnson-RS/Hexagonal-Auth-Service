from typing import List
from .. import UseCase

from app.application.dto.user import ChangePasswordInputDTO
from app.application.exceptions.not_found import UserNotFound

from app.core.domain.events import BaseEvent
from app.core.ports.repositories import UserRepositoryPort
from app.core.ports.services.access_token_verifier import AccessTokenVerifierPort
from app.core.ports.transaction import TransactionPort
from app.core.ports.services.event_publisher import EventPublisherPort


class ChangePasswordCase(UseCase):
    """
    Application use case for changing a user's password.

    Handles access token verification, password change,
    persistence, and event publishing.
    """

    def __init__(
        self,
        tx: TransactionPort,
        user_repo: UserRepositoryPort,
        access_token_verifier: AccessTokenVerifierPort,
        event_publisher: EventPublisherPort,
    ):
        self.tx = tx
        self.user_repo = user_repo
        self.access_token_verifier = access_token_verifier
        self.event_publisher = event_publisher

    async def execute(self, data: ChangePasswordInputDTO):
        """
        Execute password change operation.

        Args:
            data (ChangePasswordInputDTO): Input data containing access token,
                old password, and new password.

        Raises:
            UserNotFound: If the user does not exist.
        """
        events: List[BaseEvent] = []

        async with self.tx:
            # 1. Get user id
            user_id = self.access_token_verifier.verify(data.access_token)

            # 2. Get user and check exists
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFound()

            # 3. Change password
            user.change_password(data.old_password, data.new_password)

            # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

            # Pull events
            events.extend(user.pull_domain_events())

            # Save
            await self.user_repo.save(user)

        # Publish events
        await self.event_publisher.publish(events)
