from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
import requests

from coolingpath.services import get_realtime_weather_forecast, parse_weather_forecast


def payload():
    day = datetime.now(ZoneInfo('Asia/Seoul')).date()
    return {'hourly': {
        'time': [f'{day}T08:00', f'{day}T09:00'],
        'temperature_2m': [30.0, 31.0],
        'precipitation': [0, 1],
        'relative_humidity_2m': [65, 70],
    }}


def test_weather_success(monkeypatch):
    response = Mock()
    response.json.return_value = payload()
    get = Mock(return_value=response)
    monkeypatch.setattr('coolingpath.services.requests.get', get)
    result = get_realtime_weather_forecast(37.5, 127.0)
    response.raise_for_status.assert_called_once()
    assert response.mock_calls.index(('raise_for_status', (), {})) < response.mock_calls.index(('json', (), {}))
    assert result['mode'] == 'realtime'
    assert [row['hour'] for row in result['raw_forecast']] == [8, 9]
    assert get.call_args.kwargs['timeout'] == 5


@pytest.mark.parametrize('failure', ['http', 'timeout', 'json', 'schema'])
def test_weather_failure_falls_back_without_network(monkeypatch, failure):
    response = Mock()
    response.json.return_value = payload()
    get = Mock(return_value=response)
    if failure == 'http':
        response.raise_for_status.side_effect = requests.HTTPError('503')
    elif failure == 'timeout':
        get.side_effect = requests.Timeout()
    elif failure == 'json':
        response.json.side_effect = ValueError('invalid json')
    else:
        response.json.return_value = {'hourly': {}}
    monkeypatch.setattr('coolingpath.services.requests.get', get)
    warning = Mock()
    monkeypatch.setattr('coolingpath.services.st.warning', warning)
    assert get_realtime_weather_forecast(37.5, 127) == {}
    warning.assert_called_once()
    if failure == 'http':
        response.json.assert_not_called()


@pytest.mark.parametrize('field,value', [
    ('temperature_2m', [None, 30]), ('temperature_2m', [float('nan'), 30]),
    ('temperature_2m', [float('inf'), 30]), ('temperature_2m', [True, 30]),
    ('temperature_2m', ['30', 30]), ('precipitation', [-1, 0]),
    ('relative_humidity_2m', [101, 50]), ('relative_humidity_2m', []),
    ('time', ['invalid', 'invalid']), ('precipitation', [0]),
    ('time', 'not an array'),
])
def test_invalid_weather_schema(field, value):
    data = deepcopy(payload())
    data['hourly'][field] = value
    with pytest.raises((ValueError, TypeError)):
        parse_weather_forecast(data)


def test_empty_day_and_duplicate_hour():
    data = payload()
    tomorrow = datetime.now(ZoneInfo('Asia/Seoul')).date() + timedelta(days=1)
    with pytest.raises(ValueError, match='No daytime'):
        parse_weather_forecast(data, today=tomorrow)
    data['hourly']['time'][1] = data['hourly']['time'][0]
    with pytest.raises(ValueError, match='Duplicate'):
        parse_weather_forecast(data)
