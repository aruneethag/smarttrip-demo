"""Canonical first-release contract. No network or optional libraries required."""
import json
import re
from datetime import date, datetime
from pathlib import Path

SCHEMA = json.loads((Path(__file__).parent / 'schemas/itinerary.schema.json').read_text(encoding='utf-8'))

def validate_schema(value, schema=None, path='$'):
    """Validate the JSON Schema keywords used by our closed, versioned contract.

    This is intentionally not a general purpose JSON Schema implementation.
    The checked-in contract is canonical and drives runtime validation directly.
    """
    schema = SCHEMA if schema is None else schema
    if '$ref' in schema:
        target = SCHEMA
        for part in schema['$ref'][2:].split('/'):
            target = target[part]
        return validate_schema(value, target, path)
    types = schema.get('type', [])
    types = [types] if isinstance(types, str) else types
    matches = {'object': isinstance(value, dict), 'array': isinstance(value, list),
               'string': isinstance(value, str), 'integer': type(value) is int,
               'null': value is None}
    if types and not any(matches.get(t, False) for t in types):
        raise ValueError(f'{path}: invalid type')
    if 'const' in schema and value != schema['const']:
        raise ValueError(f'{path}: invalid constant')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: invalid choice')
    if isinstance(value, dict):
        if set(schema.get('required', [])) - value.keys():
            raise ValueError(f'{path}: missing required fields')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise ValueError(f'{path}: unexpected fields')
        for key, val in value.items():
            if key in props:
                validate_schema(val, props[key], f'{path}.{key}')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', float('inf')):
            raise ValueError(f'{path}: invalid length')
        if schema.get('uniqueItems') and len({json.dumps(x, sort_keys=True) for x in value}) != len(value):
            raise ValueError(f'{path}: duplicate values')
        for i, val in enumerate(value):
            validate_schema(val, schema.get('items', {}), f'{path}[{i}]')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0):
            raise ValueError(f'{path}: empty string')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            raise ValueError(f'{path}: invalid format')
        if schema.get('format') == 'date':
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError(f'{path}: invalid date')
        if schema.get('format') == 'date-time':
            if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
                raise ValueError(f'{path}: time zone required')
        if schema.get('format') == 'uri' and not re.match(r'^https?://[^\s/]+', value):
            raise ValueError(f'{path}: invalid URI')
    if type(value) is int and value < schema.get('minimum', -float('inf')):
        raise ValueError(f'{path}: below minimum')
    if type(value) is int and value > schema.get('maximum', float('inf')):
        raise ValueError(f'{path}: above maximum')
