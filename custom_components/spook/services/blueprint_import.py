"""Spook - Not your homey."""
from __future__ import annotations

import voluptuous as vol

import asyncio
import aiohttp
import async_timeout

from homeassistant.components.blueprint import DOMAIN
from homeassistant.components.blueprint.importer import fetch_blueprint_from_url
from homeassistant.components.blueprint.models import DomainBlueprints
from homeassistant.components.blueprint.errors import FileAlreadyExists
from homeassistant.core import ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import HomeAssistantError


from ..models import AbstractSpookService


class SpookService(AbstractSpookService):
    """Blueprint integration service to import an Blueprint from an URL."""

    domain = DOMAIN
    service = "import"
    admin = True
    schema = vol.Schema(
        {
            vol.Required("url"): cv.url,
        }
    )

    async def async_handle_service(self, call: ServiceCall) -> None:
        """Handle the service call."""
        try:
            async with async_timeout.timeout(10):
                imported_blueprint = await fetch_blueprint_from_url(
                    self.hass, call.data["url"]
                )
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            raise HomeAssistantError("Error fetching blueprint from URL") from err

        if imported_blueprint is None:
            raise HomeAssistantError("This url is not supported")

        domain_blueprints: dict[str, DomainBlueprints] = self.hass.data.get(DOMAIN, {})
        if imported_blueprint.blueprint.domain not in domain_blueprints:
            raise HomeAssistantError(
                f"Unsupported domain: {imported_blueprint.blueprint.domain}"
            )

        imported_blueprint.blueprint.update_metadata(source_url=call.data["url"])

        try:
            await domain_blueprints[
                imported_blueprint.blueprint.domain
            ].async_add_blueprint(
                imported_blueprint.blueprint, imported_blueprint.suggested_filename
            )
        except FileAlreadyExists as ex:
            raise HomeAssistantError("File already exists") from ex
        except OSError as err:
            raise HomeAssistantError("Error writing file") from err
