import re

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_NAME
from esphome.components.cc1101 import CC1101Component
from esphome.components import web_server_base

CODEOWNERS = ["@amasolov"]
DEPENDENCIES = ["cc1101", "api"]
AUTO_LOAD = ["cover", "sensor"]

CONF_HUB_ID = "hub_id"
CONF_CC1101_ID = "cc1101_id"
CONF_GDO0_PIN = "gdo0_pin"
CONF_GROUPS = "groups"
CONF_MOTOR_IDS = "motor_ids"
CONF_K520_MODE = "k520_mode"
CONF_WAKE_PREAMBLE = "wake_preamble"
CONF_WEB_SERVER_BASE_ID = "web_server_base_id"


def hex_id(value):
    """Validate an 8-hex-char motor/hub ID and normalize to lowercase.

    RX dispatch formats incoming IDs as lowercase hex, so config values
    must be lowercase too or cover/group lookups silently fail.
    """
    value = cv.string_strict(value)
    if not re.fullmatch(r"[0-9a-fA-F]{8}", value):
        raise cv.Invalid(
            f"ID must be exactly 8 hex characters (0-9, a-f), got '{value}'"
        )
    return value.lower()

sunfree_ns = cg.esphome_ns.namespace("sunfree_blinds")
SunfreeHub = sunfree_ns.class_("SunfreeHub", cg.Component)

MULTI_CONF = False

GROUP_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_NAME): cv.string_strict,
        cv.Required(CONF_MOTOR_IDS): cv.ensure_list(hex_id),
    }
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(SunfreeHub),
        cv.Optional(CONF_HUB_ID): hex_id,
        cv.Required(CONF_CC1101_ID): cv.use_id(CC1101Component),
        # Must match the cc1101 gdo0_pin — used for direct bit-bang TX.
        # Plain int (not a pin schema): the pin is shared with the cc1101
        # component, which already registers it.
        cv.Optional(CONF_GDO0_PIN, default=4): cv.int_range(min=0, max=48),
        cv.Optional(CONF_GROUPS, default=[]): cv.ensure_list(GROUP_SCHEMA),
        # Blinds2go K520 "Radio+" motors: post-pairing handshake, status
        # request by handshake, position from status byte 16.
        cv.Optional(CONF_K520_MODE, default=False): cv.boolean,
        # Wake-up preamble before each command. 160 ms matches the original
        # Tuya hub; the HackRF emulator used 250 ms on K520 motors.
        cv.Optional(CONF_WAKE_PREAMBLE, default="160ms"): cv.All(
            cv.positive_time_period_milliseconds,
            cv.Range(
                min=cv.TimePeriod(milliseconds=100),
                max=cv.TimePeriod(milliseconds=300),
            ),
        ),
        # Serves the component's page at /sunfree when web_server is used.
        cv.OnlyWith(CONF_WEB_SERVER_BASE_ID, "web_server_base"): cv.use_id(
            web_server_base.WebServerBase
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    if CONF_HUB_ID in config:
        cg.add(var.set_hub_id(config[CONF_HUB_ID]))

    cc1101 = await cg.get_variable(config[CONF_CC1101_ID])
    cg.add(var.set_cc1101(cc1101))
    cg.add(var.set_gdo0_pin(config[CONF_GDO0_PIN]))
    cg.add(var.set_k520_mode(config[CONF_K520_MODE]))
    cg.add(var.set_wake_preamble_ms(config[CONF_WAKE_PREAMBLE].total_milliseconds))

    if CONF_WEB_SERVER_BASE_ID in config:
        base = await cg.get_variable(config[CONF_WEB_SERVER_BASE_ID])
        cg.add_define("USE_SUNFREE_WEB")
        cg.add(var.set_web_base(base))

    for group in config.get(CONF_GROUPS, []):
        motor_ids = cg.RawExpression(
            "std::vector<std::string>{"
            + ",".join(f'"{m}"' for m in group[CONF_MOTOR_IDS])
            + "}"
        )
        cg.add(var.add_group(group[CONF_NAME], motor_ids))
