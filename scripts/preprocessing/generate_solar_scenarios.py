"""Generate the notebook's 08–19 KST solar scenario without network access."""
import argparse
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
from pysolar.solar import get_altitude, get_azimuth

from .common import new_output


def generate_solar_scenarios(day, latitude=37.5026, longitude=127.0427):
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError('Invalid latitude/longitude')
    rows = []
    for hour in range(8, 20):
        stamp = datetime.combine(day, time(hour), tzinfo=ZoneInfo('Asia/Seoul'))
        rows.append(dict(
            time_slot=hour,
            sun_altitude=round(float(get_altitude(latitude, longitude, stamp)), 2),
            sun_azimuth=round(float(get_azimuth(latitude, longitude, stamp)), 2),
            timestamp_kst=stamp.isoformat(sep=' '),
        ))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat, default=date(2025, 7, 8))
    parser.add_argument('--latitude', type=float, default=37.5026)
    parser.add_argument('--longitude', type=float, default=127.0427)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    frame = generate_solar_scenarios(args.date, args.latitude, args.longitude)
    frame.to_csv(new_output(args.output), index=False)


if __name__ == '__main__':
    main()
