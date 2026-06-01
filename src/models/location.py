from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Location:
    zip: str
    city: str
    state: str
    lat: float
    lon: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'Location':
        return cls(
            zip=d['zip'],
            city=d['city'],
            state=d['state'],
            lat=float(d['lat']),
            lon=float(d['lon']),
        )

    @property
    def display_name(self) -> str:
        return f"{self.city}, {self.state}"
