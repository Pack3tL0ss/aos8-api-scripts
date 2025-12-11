#!/usr/bin/env python3
#
# Author: Wade Wells github/Pack3tL0ss
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from typing import Dict, List


class Cert:
    def __init__(self, *, p12_name: str | None = None, p12_pass: str | None = None, dir: Path | None = None, tftp_svr: str | None = None, md_path: str | None = None):
        self.p12_name: str | None = p12_name
        self.p12_pass: str | None = p12_pass
        self.dir: Path | None = dir
        self.tftp_svr: str | None = tftp_svr
        self.md_path: str | None = md_path

    def ok(self):
        name_pass_ok = True if any([x is None for x in [self.p12_name, self.p12_pass]]) else False
        location = True if self.dir or self.tftp_svr else False
        return name_pass_ok and location

class Config:
    def __init__(self, base_dir: Path = None):
        BASE_DIR = base_dir or Path(__file__).parent.parent
        yaml_config = BASE_DIR / 'config.yaml'
        self.data: dict = self.get_yaml_file(yaml_config) or {}
        self.DEBUG: bool = self.data.get("debug", False)
        self.conductors: List[str] = self.data.get("conductors", [])
        self.user: str | None = self.data.get("user")
        self.password: str | None = self.data.get("password")
        self.cert: Cert = Cert(**self.data.get("cert", {}))

    def __bool__(self):
        return len(self.data) > 0

    def __len__(self):
        return len(self.data)

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.data:
            return self.data.get(key, default)
        elif hasattr(self.cert, key):
            return getattr(self.cert, key)
        else:
            raise AttributeError(f'Config object has no attribute {key}')

    @staticmethod
    def get_yaml_file(yaml_config: Path) -> Dict:
        '''Return dict from yaml file.'''
        if yaml_config.exists() and yaml_config.stat().st_size > 0:
            with yaml_config.open() as f:
                try:
                    return yaml.load(f, Loader=yaml.SafeLoader)
                except ValueError as e:
                    print(f'Unable to load configuration from {yaml_config}\n\t{e}')
                    return {}
