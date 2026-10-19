"""Define services for the Spritmonitor integration."""

from datetime import datetime as dt
from math import isfinite
import logging
import aiohttp

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .api import api_get, api_headers, SpritmonitorAPIError

from .const import (
    DOMAIN,
    SERVICE_ADD_FUELING_SCHEMA,
    SERVICE_ADD_FUELING,
    CONF_VEHICLE_ID,
    CONF_APP_TOKEN,
    CONF_BEARER_TOKEN,
    API_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register all Spritmonitor services."""

    async def handle_add_fueling(call: ServiceCall) -> None:
        """Handle the add fueling service call."""
        await _async_add_fueling(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_FUELING,
        handle_add_fueling,
        schema=SERVICE_ADD_FUELING_SCHEMA,
    )
    _LOGGER.info("Spritmonitor services registered.")


async def _async_add_fueling(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add a fueling entry to Spritmonitor."""
    data = dict(call.data)  # Make mutable copy

    # Handle position
    _validate_position(data)

    # Resolve device and config
    entry = _resolve_config_entry(hass, data["vehicle_device"])
    vehicle_id = entry.data[CONF_VEHICLE_ID]
    _LOGGER.info("Adding fueling for vehicle_id=%s", vehicle_id)

    # Parse date
    data["date"] = _parse_date(data.get("date"))

    # Get the current odometer and derive trip from the last Spritmonitor entry.
    data["odometer"], data["trip"] = await _calculate_trip(hass, entry, data)

    # Prepare parameters
    params = _prepare_base_params(data)
    params.update(_prepare_optional_params(data))
    _combine_attributes(data, params)
    _combine_charge_info(data, params)

    # Submit fueling
    await _submit_fueling(hass, entry, vehicle_id, data["tank_id"], params)


async def _calculate_trip(hass: HomeAssistant, entry, data: dict) -> tuple[float, float]:
    """Compute distance from the latest matching Spritmonitor fueling entry."""
    entity_id = data["odometer_entity"]
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        raise HomeAssistantError(f"Odometer entity {entity_id} is unavailable")
    try:
        current = float(state.state)
    except (TypeError, ValueError) as err:
        raise HomeAssistantError(f"Odometer entity {entity_id} is not numeric") from err
    if not isfinite(current) or current < 0:
        raise HomeAssistantError("Current odometer must be a finite nonnegative number")

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        raise HomeAssistantError("Spritmonitor vehicle coordinator not initialized")
    await coordinator.async_request_refresh()
    snapshot = coordinator.data or {}
    vehicle = snapshot.get("vehicle") or {}
    trip_unit = vehicle.get("tripunit")
    entity_unit = state.attributes.get("unit_of_measurement")
    if trip_unit and entity_unit and trip_unit.lower() != str(entity_unit).lower():
        raise HomeAssistantError(
            f"Odometer unit {entity_unit} does not match Spritmonitor unit {trip_unit}"
        )

    # PHEVs have separate fuel and electricity histories.
    electric = int(data["fuelsort_id"]) in (19, 24)
    if electric:
        previous = snapshot.get("last_electric_charge")
    else:
        previous = snapshot.get("last_gas_refueling")
    if previous is None and not electric:
        previous = snapshot.get("last_refueling")
    if not previous or previous.get("odometer") is None:
        raise HomeAssistantError(
            "No previous Spritmonitor odometer for this fuel type; add a baseline first"
        )
    try:
        last = float(previous["odometer"])
    except (ValueError, TypeError) as err:
        raise HomeAssistantError("Last Spritmonitor odometer is not numeric") from err
    if not isfinite(last):
        raise HomeAssistantError("Last Spritmonitor odometer is invalid")
    trip = current - last
    if trip < 0:
        raise HomeAssistantError(
            f"Current odometer ({current}) is lower than last Spritmonitor reading ({last})"
        )
    return current, round(trip, 3)


def _validate_position(data: dict) -> None:
    lat, lon = data.get("latitude"), data.get("longitude")
    if lat is not None and lon is not None:
        data["position"] = f"{lat},{lon}"
        _LOGGER.debug("Position set: %s", data["position"])
    elif lat is not None or lon is not None:
        raise HomeAssistantError("Both latitude and longitude must be provided together.")
    else:
        data.pop("position", None)
        _LOGGER.debug("No position provided, skipping.")


def _resolve_config_entry(hass: HomeAssistant, device_id: str):
    device_registry = async_get_device_registry(hass)
    device_entry = device_registry.devices.get(device_id)
    if not device_entry:
        raise HomeAssistantError(f"Device {device_id} not found in HA registry")

    entry = next(
        (e for e in hass.config_entries.async_entries(DOMAIN)
         if e.entry_id in device_entry.config_entries),
        None
    )
    if not entry:
        raise HomeAssistantError(f"No Spritmonitor config found for device {device_id}")
    return entry


def _parse_date(value) -> dt:
    if isinstance(value, dt):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                parsed_date = dt.strptime(value, fmt)
                _LOGGER.debug("Parsed date: %s using format %s", parsed_date, fmt)
                return parsed_date
            except ValueError:
                continue
    raise HomeAssistantError(f"Invalid date format: {value}.")


def _prepare_base_params(data: dict) -> dict:
    return {
        "date": data["date"].strftime("%d.%m.%Y"),
        "trip": data["trip"],
        "odometer": data["odometer"],
        "quantity": data["quantity"],
        "type": data["type"],
        "fuelsortid": data["fuelsort_id"],
        "quantityunitid": data["quantity_unit_id"],
    }


def _prepare_optional_params(data: dict) -> dict:
    """Prepare optional parameters for the API call."""
    mapping = {
        "price": "price",
        "currency_id": "currencyid",
        "pricetype": "pricetype",
        "note": "note",
        "stationname": "stationname",
        "location": "location",
        "country": "country",
        "bc_consumption": "bc_consumption",
        "bc_quantity": "bc_quantity",
        "bc_speed": "bc_speed",
        "percentage": "percent",
        "charging_power": "charging_power",
        "charging_duration": "charging_duration",
        "streets": "streets",
        "position": "position",
    }

    params = {}
    for key, api_name in mapping.items():
        value = data.get(key)
        if value is None:
            continue

        if key == "streets":
            if isinstance(value, list):
                value = ",".join(value)
            elif not isinstance(value, str):
                value = None

        if value is not None:
            params[api_name] = value
            _LOGGER.debug("Optional param: %s -> %s = %s", key, api_name, value)
    return params


def _combine_attributes(data: dict, params: dict) -> None:
    attributes = []
    if data.get("attributes_tires"):
        attributes.append(data["attributes_tires"])
    if data.get("attributes_driving_style"):
        attributes.append(data["attributes_driving_style"])
    for attr in ("ac", "heating", "trailer"):
        if data.get(f"attributes_{attr}"):
            attributes.append(attr)
    if attributes:
        params["attributes"] = ",".join(attributes)
        _LOGGER.debug("Combined attributes: %s", params["attributes"])


def _combine_charge_info(data: dict, params: dict) -> None:
    info = []
    if data.get("charge_info_ac_dc"):
        info.append(data["charge_info_ac_dc"])
    if data.get("charge_info_source"):
        info.append(data["charge_info_source"])
    if info:
        params["charge_info"] = ",".join(info)
        _LOGGER.debug("Combined charge_info: %s", params["charge_info"])


async def _submit_fueling(hass: HomeAssistant, entry, vehicle_id: str, tank_id: str, params: dict) -> None:
    url = f"{API_BASE_URL}/vehicle/{vehicle_id}/tank/{tank_id}/fueling.json"
    headers = api_headers(entry.data[CONF_APP_TOKEN], entry.data[CONF_BEARER_TOKEN])
    session = async_get_clientsession(hass)
    try:
        # Spritmonitor's official Add_Fuel_Entry sample submits query parameters via GET.
        result = await api_get(session, url, headers, params=params)
        if not isinstance(result, dict):
            raise HomeAssistantError("Unexpected Spritmonitor response")

        _LOGGER.info("Fueling successfully added for vehicle %s (tank %s)", vehicle_id, tank_id)
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator:
            await coordinator.async_request_refresh()
    except (aiohttp.ClientError, SpritmonitorAPIError, TimeoutError) as err:
        raise HomeAssistantError(f"Spritmonitor API request failed: {err}") from err
