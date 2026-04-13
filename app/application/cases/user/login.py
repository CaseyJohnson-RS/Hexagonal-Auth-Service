from typing import List
from .. import UseCase

from app.application.exceptions.not_found import UserNotFound
from app.core.domain.entities.refresh_token import RefreshToken
from app.core.domain.events import BaseEvent

from app.core.ports.config import ConfigPort
from app.core.ports.repositories import RefreshTokenRepositoryPort, UserRepositoryPort
from app.core.ports.services.access_token_issuer import AccessTokenIssuerPort
from app.core.ports.transaction import TransactionPort
from app.core.ports.services.event_publisher import EventPublisherPort

from app.application.dto.user import LoginUserInputDTO, TokenPairDTO


class LoginUserCase(UseCase):
    """
    Application use case for user login.

    Handles user authentication, access and refresh token generation,
    persistence, and event publishing.
    """

    def __init__(
        self,
        tx: TransactionPort,
        user_repo: UserRepositoryPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
        config: ConfigPort,
        event_publisher: EventPublisherPort,
        access_token_issuer: AccessTokenIssuerPort,
    ):
        self.tx = tx
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.config = config
        self.event_publisher = event_publisher
        self.access_token_issuer = access_token_issuer

    async def execute(self, data: LoginUserInputDTO) -> TokenPairDTO:
        """
        Execute user login process.

        Args:
            data (LoginUserInputDTO): User login credentials.

        Raises:
            UserNotFound: If user with provided email does not exist.

        Returns:
            TokenPairDTO: Generated access and refresh tokens.
        """
        events: List[BaseEvent] = []

        async with self.tx:
            # 1. Check user exists and can login
            user = await self.user_repo.get_by_email(data.email)
            if not user:
                raise UserNotFound("User does not exist")
            user.assert_can_login(data.password)

            # 2. Generate access token and refresh token
            access_token = self.access_token_issuer.issue(
                user.id, self.config.access_token_exp()
            )
            refresh_token, refresh_token_str = RefreshToken.create(
                user_id=user.id,
                token_length=self.config.refresh_token_len(),
                expiry=self.config.refresh_token_exp(),
                location=data.location,
                client_ip=data.client_ip,
                user_agent=data.user_agent,
            )

            # 3. Prepare response data
            response_data = TokenPairDTO(
                access_token=access_token,
                refresh_token=refresh_token_str
            )

            # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

            # Pull domain events from aggregates
            events.extend(user.pull_domain_events())
            events.extend(refresh_token.pull_domain_events())

            # Persist aggregates
            await self.user_repo.save(user)
            await self.refresh_token_repo.save(refresh_token)

        # Publish events outside the transaction
        await self.event_publisher.publish(events)

        # Return access/refresh token pair
        return response_data
