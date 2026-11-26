import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def load_scene_runtime_settings(scene_path: str) -> Dict[str, Any]:
    env_data_path = os.path.join(scene_path, "env_data.json")
    if not os.path.exists(env_data_path):
        return {}

    try:
        with open(env_data_path, "r", encoding="utf-8") as env_data_file:
            env_data = json.load(env_data_file)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Unable to read scene runtime settings from env_data.json: {e}") from e
    if not isinstance(env_data, dict):
        raise ValueError("env_data.json must contain a JSON object")

    settings = {}
    if "max_rounds" in env_data:
        max_rounds = env_data["max_rounds"]
        if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
            raise ValueError("max_rounds in env_data.json must be a positive integer")
        settings["max_rounds"] = max_rounds

    if "bus_idle_timeout" in env_data:
        idle_timeout = env_data["bus_idle_timeout"]
        if isinstance(idle_timeout, bool) or not isinstance(idle_timeout, (int, float)) or idle_timeout <= 0:
            raise ValueError("bus_idle_timeout in env_data.json must be a positive number")
        settings["bus_idle_timeout"] = float(idle_timeout)

    return settings


def apply_scene_runtime_constraints(config: Dict[str, Any], scene_path: str) -> Dict[str, Any]:
    settings = load_scene_runtime_settings(scene_path)
    if not settings:
        return config

    environment = config.setdefault("simulator", {}).setdefault("environment", {})
    if "max_rounds" in settings:
        max_rounds = settings["max_rounds"]
        previous_steps = environment.get("max_steps")
        if previous_steps != max_rounds:
            logger.warning(
                f"Aligning simulation max_steps ({previous_steps}) with scene max_rounds ({max_rounds})"
            )
        environment["max_steps"] = max_rounds

    if "bus_idle_timeout" in settings:
        idle_timeout = settings["bus_idle_timeout"]
        previous_timeout = environment.get("bus_idle_timeout")
        if previous_timeout != idle_timeout:
            logger.warning(
                f"Applying scene bus_idle_timeout ({idle_timeout}s; previous value: {previous_timeout})"
            )
        environment["bus_idle_timeout"] = idle_timeout

    return config


def load_agent_count_settings(scene_path: str) -> Dict[str, Dict[str, int]]:
    scene_info_path = os.path.join(scene_path, "scene_info.json")
    if not os.path.exists(scene_info_path):
        return {"default_agent_counts": {}, "minimum_agent_counts": {}}

    with open(scene_info_path, "r", encoding="utf-8") as scene_file:
        scene_info = json.load(scene_file)

    settings = {}
    for key in ("default_agent_counts", "minimum_agent_counts"):
        value = scene_info.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f"{key} in scene_info.json must be an object")

        counts = {}
        for agent_type, count in value.items():
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"{key}.{agent_type} must be a non-negative integer")
            counts[agent_type] = count
        settings[key] = counts

    return settings


def apply_agent_count_constraints(config: Dict[str, Any], scene_path: str) -> Dict[str, Any]:
    settings = load_agent_count_settings(scene_path)
    defaults = settings["default_agent_counts"]
    minimums = settings["minimum_agent_counts"]
    agent_config = config.setdefault("agent", {})
    profiles = agent_config.setdefault("profile", {})

    for agent_type in set(defaults) | set(minimums):
        profile_config = profiles.setdefault(agent_type, {})
        if not isinstance(profile_config, dict):
            raise ValueError(f"agent.profile.{agent_type} must be an object")

        count = profile_config.get("count", defaults.get(agent_type, minimums.get(agent_type, 1)))
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"agent.profile.{agent_type}.count must be a non-negative integer")
        profile_config["count"] = max(count, minimums.get(agent_type, 0))

    return config
