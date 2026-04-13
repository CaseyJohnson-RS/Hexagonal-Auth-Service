from typing import List
from .. import UseCase

from app.core.domain.events import BaseEvent
from app.core.ports.config import ConfigPort
from app.core.ports.repositories import OneTimeTokenRepositoryPort, UserRepositoryPort
from app.core.ports.services.event_publisher import EventPublisherPort
from app.core.ports.transaction import TransactionPort

from app.application.dto.user import RegisterUserInputDTO
from app.application.exceptions.conflict import UserAlreadyExists

from app.core.domain.entities.user import User
from app.core.domain.services import EmailVerificationService


class RegisterUserCase(UseCase):
    """
    Application use case for registering a new user.

    Handles user creation, email verification token generation,
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

    async def execute(self, data: RegisterUserInputDTO):
        """
        Execute the registration process.

        Args:
            data (RegisterUserInputDTO): User registration input data.

        Raises:
            UserAlreadyExists: If a verified user with the same email already exists.
        """
        events: List[BaseEvent] = []

        async with self.tx:
            # 1. Check user exists and email verified
            user = await self.user_repo.get_by_email(data.email)
            if user and user.is_email_verified:
                raise UserAlreadyExists()

            # 2. Create user (if not exists)
            user = user or User.create(data.email, data.password)

            # 3. Request email verification
            ott, _ = EmailVerificationService.request_verification(
                user=user,
                token_length=self.config.email_token_len(),
                token_expiry=self.config.email_token_exp(),
            )

            # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

            # Pull events from user aggregate
            events.extend(user.pull_domain_events())

            # Save changes to repositories
            await self.user_repo.save(user)
            await self.ott_repo.save(ott)

        # Publish events outside of transaction
        await self.event_publisher.publish(events)
