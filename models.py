# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Deploy Buddy Environment.

The deploy_buddy environment is a simple test environment that echoes back messages.
"""

import json
from typing import Any, Dict, List, Literal, Optional
from openenv.core.env_server.types import Action, Observation
from pydantic import Field, model_validator, field_validator


class DeployBuddyAction(Action):
    """Structured action for SRE environment"""

    action_type: Literal[
        "inspect_service",
        "inspect_logs",
        "change_lb_config",
        "restart_service",
        "revert_version",
        "wait"
    ] = Field(..., description="Type of action")

    target: Optional[str] = Field(
        default=None,
        description="Target service (api, db, task_runner)"
    )

    value: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Replica distribution across zones for change_lb_config"
    )

    grade: Optional[bool] = Field(
        default=False,
        description="enable grading/ evaluation"
    )

    @model_validator(mode="after")
    def validate_action(self):
        """
        Ensures that `value` is provided only for change_lb_config
        and validates its structure.
        """
        if self.action_type == "change_lb_config":
            if self.target is None:
                raise ValueError(
                    "`target` must be specified for change_lb_config."
                )
            if not self.value:
                raise ValueError(
                    "`value` must be provided for change_lb_config."
                )
            # Validate that replicas are non-negative integers
            for zone, replicas in self.value.items():
                if not isinstance(replicas, int) or replicas < 0:
                    raise ValueError(
                        f"Replica count for zone '{zone}' must be a non-negative integer."
                    )
                
        return self
    
    @field_validator("value", mode="before")
    @classmethod
    def parse_value(cls, v: Any) -> Dict[str, int]:
        # If the UI sends a JSON string, parse it
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(
                    "Invalid JSON format for 'value'. Expected a dictionary like "
                    '{"zone_a": 2, "zone_b": 1, "zone_c": 2}.'
                ) from e
        return v


class DeployBuddyObservation(Observation):
    """Observation for SRE environment"""

    metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="System metrics like latency, cpu, error_rate"
    )

    logs: List[str] = Field(
        default_factory=list,
        description="Sampled logs"
    )

    alerts: List[str] = Field(
        default_factory=list,
        description="Active alerts"
    )

    step: int = Field(
        default=0,
        description="Current timestep"
    )

    internal_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Network topology of the component"
    )

    task_id: int = Field(default=0)

    grades_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional data like grading results"
    )
