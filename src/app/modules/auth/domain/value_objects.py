from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str

@dataclass(frozen=True, slots=True)
class RefreshToken:
    value: str