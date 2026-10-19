# Contenido para: const.py

"""Constants for the Spritmonitor integration."""
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

# Domain for the integration
DOMAIN = "spritmonitor"
MANUFACTURER = "matbott & 🤖"

# Default values
DEFAULT_APP_TOKEN = "095369dede84c55797c22d4854ca6efe"
DEFAULT_UPDATE_INTERVAL = 6

# API Configuration
API_BASE_URL = "https://api.spritmonitor.de/v1"
API_VEHICLES_URL = f"{API_BASE_URL}/vehicles.json"
API_REMINDERS_URL = f"{API_BASE_URL}/reminders.json"

# --- URL DE FUELINGS CORREGIDA (VUELTA A LA ORIGINAL) ---
API_FUELINGS_URL_TPL = f"{API_BASE_URL}/vehicle/{{vehicle_id}}/fuelings.json"

# --- LÍNEA ANTIGUA ELIMINADA ---
# API_FUELINGS_URL = f"{API_BASE_URL}/fuelings.json"

# Configuration keys
CONF_VEHICLE_ID = "vehicle_id"
CONF_APP_TOKEN = "app_token"
CONF_BEARER_TOKEN = "bearer_token"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_VEHICLE_TYPE = "vehicle_type"
CONF_CURRENCY = "currency"

# Vehicle Types
VEHICLE_TYPE_COMBUSTION = "combustion"
VEHICLE_TYPE_ELECTRIC = "electric"
VEHICLE_TYPE_PHEV = "phev"

# Fields whose service values refer to Home Assistant entities.
ENTITY_VALUE_FIELDS = {
    "quantity": float,
    "price": float,
    "note": str,
    "stationname": str,
    "location": str,
    "bc_consumption": float,
    "bc_quantity": float,
    "bc_speed": float,
    "latitude": float,
    "longitude": float,
    "percentage": int,
    "charging_power": float,
    "charging_duration": int,
}

# Service constants
SERVICE_ADD_FUELING = "add_fueling"
SERVICE_ADD_FUELING_SCHEMA = vol.Schema(
    {
        vol.Required("vehicle_device"): cv.string,
        vol.Required("tank_id"): vol.Coerce(int),
        vol.Required("date"): cv.entity_id,
        vol.Required("odometer_entity"): cv.entity_id,
        vol.Required("quantity"): cv.entity_id,
        vol.Required("type"): cv.string,
        vol.Required("fuelsort_id"): vol.Coerce(int),
        vol.Required("quantity_unit_id"): vol.Coerce(int),

        vol.Optional("price"): cv.entity_id,
        vol.Optional("currency_id"): vol.Any(vol.Coerce(int), None),
        vol.Optional("pricetype"): vol.Any(vol.Coerce(int), None),
        vol.Optional("note"): cv.entity_id,
        vol.Optional("stationname"): cv.entity_id,
        vol.Optional("location"): cv.entity_id,
        vol.Optional("country"): vol.Any(cv.string, None),
        vol.Optional("bc_consumption"): cv.entity_id,
        vol.Optional("bc_quantity"): cv.entity_id,
        vol.Optional("bc_speed"): cv.entity_id,
        vol.Optional("latitude"): cv.entity_id,
        vol.Optional("longitude"): cv.entity_id,
        vol.Optional("percentage"): cv.entity_id,
        vol.Optional("charging_power"): cv.entity_id,
        vol.Optional("charging_duration"): cv.entity_id,
        vol.Optional("charge_info_ac_dc"): vol.Any(cv.string, None),
        vol.Optional("charge_info_source"): vol.Any(cv.string, None),
        vol.Optional("streets"): vol.Any([cv.string], None),
        vol.Optional("attributes_tires"): vol.Any(cv.string, None),
        vol.Optional("attributes_driving_style"): vol.Any(cv.string, None),
        vol.Optional("attributes_ac"): vol.Any(bool, None),
        vol.Optional("attributes_heating"): vol.Any(bool, None),
        vol.Optional("attributes_trailer"): vol.Any(bool, None),
    }
)