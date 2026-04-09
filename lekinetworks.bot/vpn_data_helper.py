from dataclasses import dataclass, field
from datetime import datetime
import json
from typing import Optional

@dataclass
class vpn_item:
    config_name: str
    device_id: str
    expiry_date: datetime

@dataclass
class vpn_data:
    vpn_items: list[vpn_item] = field(default_factory=list)