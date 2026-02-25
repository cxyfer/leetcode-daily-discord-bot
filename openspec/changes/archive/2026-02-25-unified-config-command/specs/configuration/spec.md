## ADDED Requirements

### Requirement: Timezone parsing with UTC offset support
The `parse_timezone()` function in `utils/config.py` SHALL accept both IANA timezone names and UTC offset strings, returning a `tzinfo`-compatible object accepted by APScheduler's `CronTrigger`.

#### Scenario: Parse IANA timezone name
- **WHEN** `parse_timezone("Asia/Taipei")` is called
- **THEN** the function SHALL return a `pytz.tzinfo` object equivalent to `pytz.timezone("Asia/Taipei")`

#### Scenario: Parse UTC offset integer hours
- **WHEN** `parse_timezone("UTC+8")` is called
- **THEN** the function SHALL return a `datetime.timezone` with utcoffset of +08:00

#### Scenario: Parse UTC offset with minutes
- **WHEN** `parse_timezone("UTC+5:30")` is called
- **THEN** the function SHALL return a `datetime.timezone` with utcoffset of +05:30

#### Scenario: Parse UTC zero variants
- **WHEN** `parse_timezone("UTC+0")` or `parse_timezone("UTC-0")` is called
- **THEN** the function SHALL return a `datetime.timezone` with utcoffset of +00:00, scheduling-equivalent to `parse_timezone("UTC")`

#### Scenario: Reject out-of-range offset
- **WHEN** `parse_timezone("UTC+15")` or `parse_timezone("UTC-13")` is called
- **THEN** the function SHALL raise `ValueError` with a descriptive message

#### Scenario: Reject malformed input
- **WHEN** `parse_timezone("InvalidZone")` or `parse_timezone("UTC+abc")` is called
- **THEN** the function SHALL raise `ValueError` with supported format examples

#### Scenario: CronTrigger compatibility
- **WHEN** the return value of `parse_timezone()` is passed to `CronTrigger(timezone=...)`
- **THEN** APScheduler SHALL accept it without `TypeError` for both IANA and UTC offset inputs
