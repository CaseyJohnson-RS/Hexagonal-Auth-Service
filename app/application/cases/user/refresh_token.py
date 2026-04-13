from typing import List
from .. import UseCase

from app.application.dto.user import RefreshTokenInputDTO, TokenPairDTO
from app.application.events.security import RefreshTokenReuseDetected
from app.application.exceptions.not_found import RefreshTokenNotFound

from app.core.domain.events import BaseEvent
from app.core.domain.exceptions.token import RefreshTokenReuse
from app.core.domain.services import RefreshTokenRotationService
from app.core.ports.config import ConfigPort
from app.core.ports.repositories import RefreshTokenRepositoryPort
from app.core.ports.services.access_token_issuer import AccessTokenIssuerPort
from app.core.ports.transaction import TransactionPort
from app.core.ports.services.event_publisher import EventPublisherPort


class RefreshTokenCase(UseCase):
    """
    Application use case for refreshing access tokens using a refresh token.

    Handles refresh token rotation, access token issuance, persistence,
    domain events, and detection of refresh token reuse.
    """

    def __init__(
        self,
        tx: TransactionPort,
        refresh_token_repo: RefreshTokenRepositoryPort,
        config: ConfigPort,
        event_publisher: EventPublisherPort,
        access_token_issuer: AccessTokenIssuerPort,
    ):
        self.tx = tx
        self.refresh_token_repo = refresh_token_repo
        self.config = config
        self.event_publisher = event_publisher
        self.access_token_issuer = access_token_issuer

    async def execute(self, data: RefreshTokenInputDTO) -> TokenPairDTO:
        """
        Execute token refresh process.

        Args:
            data (RefreshTokenInputDTO): Input containing the refresh token string 
                and optional client metadata.

        Raises:
            RefreshTokenNotFound: If the provided refresh token does not exist.
            RefreshTokenReuse: If the token has already been used or replaced.

        Returns:
            TokenPairDTO: Newly issued access and refresh tokens.
        """
        events: List[BaseEvent] = []

        try:
            async with self.tx:
                # 1. Check token exists
                rt = await self.refresh_token_repo.get_by_string(data.refresh_token)
                if not rt:
                    raise RefreshTokenNotFound()

                # 2. Use refresh token (mark as used/revoked)
                rt.use()

                # 3. Generate new refresh token and access token
                new_rt, new_rt_str, access_token = RefreshTokenRotationService.rotate(
                    old_token=rt,
                    refresh_token_length=self.config.refresh_token_len(),
                    refresh_token_expiry=self.config.refresh_token_exp(),
                    access_token_expiry=self.config.access_token_exp(),
                    access_token_issuer=self.access_token_issuer
                )

                response_data = TokenPairDTO(
                    access_token=access_token,
                    refresh_token=new_rt_str
                )

                # = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

                # Pull domain events
                events.extend(rt.pull_domain_events())
                events.extend(new_rt.pull_domain_events())

                # Save tokens
                await self.refresh_token_repo.save(rt)
                await self.refresh_token_repo.save(new_rt)

            # Return new tokens
            return response_data

        except RefreshTokenReuse as e:
            # Detect and report refresh token reuse
            async with self.tx:
                rt = await self.refresh_token_repo.get_by_string(data.refresh_token)
                if rt:
                    events.append(
                        RefreshTokenReuseDetected(
                            user_id=rt.user_id,
                            token_id=rt.id,
                            client_ip=data.client_ip,
                            user_agent=data.user_agent,
                            location=data.location,
                        )
                    )

            # Publish reuse detection events
            await self.event_publisher.publish(events)
            raise e
