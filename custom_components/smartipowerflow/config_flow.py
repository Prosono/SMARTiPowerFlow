import logging
from homeassistant import config_entries
import voluptuous as vol
from aiohttp import ClientSession, ClientError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

VERIFY_SUBSCRIPTION_URL = "https://smarti.pythonanywhere.com/verify-subscription"

@config_entries.HANDLERS.register(DOMAIN)
class SmartiUpdaterFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMARTi PowerFlow™."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            _LOGGER.info(f"User input received: {user_input}")

            # Validate email
            email = user_input.get("email")
            if not email or "@" not in email:
                errors["email"] = "Please enter a valid email address."
            else:
                # Check subscription via Flask app using aiohttp
                try:
                    async with ClientSession() as session:
                        async with session.post(
                            VERIFY_SUBSCRIPTION_URL, json={"email": email}, timeout=10
                        ) as response:
                            if response.status == 200:
                                _LOGGER.info("Subscription verified successfully.")
                                # Proceed with creating the entry
                                return self.async_create_entry(
                                    title="SMARTi PowerFlow™",
                                    data=user_input,
                                )
                            elif response.status == 403:
                                _LOGGER.warning("Subscription not found.")
                                errors["base"] = "Subscription not found. Please ensure you have an active subscription."
                            else:
                                _LOGGER.error(
                                    f"Unexpected response: {response.status}"
                                )
                                errors["base"] = "An unexpected error occurred. Please try again later."
                except ClientError as e:
                    _LOGGER.error(f"Error contacting subscription service: {e}")
                    errors["base"] = "Unable to contact the subscription service. Please check your connection."

        # Display the form
        schema = vol.Schema({
            vol.Required("email"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "subscription_url": "https://www.smarti.dev/smarti-store/p/smarti-powerflow"
            },
        )
