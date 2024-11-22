import logging
import requests
from homeassistant import config_entries
import voluptuous as vol
import homeassistant.helpers.config_validation as cv  # Import config validation
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

VERIFY_SUBSCRIPTION_URL = "https://smarti.pythonanywhere.com/verify-subscription"


@config_entries.HANDLERS.register(DOMAIN)
class SmartiUpdaterFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMARTi."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        try:
            errors = {}

            if user_input is not None:
                _LOGGER.info(f"User input received: {user_input}")

                # Validate email
                email = user_input.get("email")
                if not email or "@" not in email:
                    errors["email"] = "invalid_email"
                else:
                    # Check subscription via Flask app
                    try:
                        response = requests.post(
                            VERIFY_SUBSCRIPTION_URL,
                            json={"email": email},
                            timeout=10
                        )
                        if response.status_code == 200:
                            _LOGGER.info("Subscription verified successfully.")
                            # Proceed with creating the entry
                            return self.async_create_entry(
                                title="SMARTi",
                                data=user_input
                            )
                        elif response.status_code == 403:
                            _LOGGER.warning("Subscription not found.")
                            errors["base"] = "subscription_not_found"
                        else:
                            _LOGGER.error(f"Unexpected response: {response.status_code}")
                            errors["base"] = "unknown_error"
                    except requests.RequestException as e:
                        _LOGGER.error(f"Error contacting subscription service: {e}")
                        errors["base"] = "connection_error"

            # Display the form
            schema = vol.Schema({
                vol.Required("email"): str,
                vol.Optional("update_node_red", default=False): cv.boolean,
                vol.Optional("update_dashboards", default=False): cv.boolean,
                vol.Optional("update_automations", default=False): cv.boolean,
            })

            _LOGGER.debug(f"Schema being used: {schema}")

            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                errors=errors,
                description_placeholders={"name": "SMARTi"},
            )
        except Exception as e:
            _LOGGER.error(f"Error in config flow: {e}", exc_info=True)  # Log full stack trace
            return self.async_abort(reason="unknown_error")
