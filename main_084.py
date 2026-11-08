"""Apply an integer percentage discount to a price represented in whole cents.

Build an in-memory price adjustment report using whole-cent amounts.

The program has three connected layers. parse_request loads the built-in
example or a JSON request. validate_request checks fields and types before
build_report calls discounted_price and assembles domain details.
Finally, build_argument_parser and main select the input and output modes.

Running the file without arguments prints one JSON result. --report returns
the complete processing report, --input-json accepts another request, and
--pretty makes either output easier to read. Invalid request data produces a JSON
error on standard error and exit status two. All processing stays in memory;
this program does not access the network or read or write application files.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import sys


DEFAULT_REQUEST = {'price_cents': 1300, 'percent': 10}


def parse_request(raw_json: str | None) -> dict:
    """Key idea: Load an independent request object from the built-in example or JSON text.

    Inputs: raw_json is a JSON string, or None to select the built-in example.

    Output and return type: Return dict containing the decoded request. No application
    files are accessed.

    Important conditions: None selects a deep copy of DEFAULT_REQUEST; other input must
    decode to a JSON object. Malformed JSON or another top-level type raises ValueError.

    Role in the program: Supply the request that validation and the domain report
    consume.

    Assumptions: Input is small enough to process in memory; JSON decoding does not
    establish that individual fields are valid.
    """
    if raw_json is None:
        return deepcopy(DEFAULT_REQUEST)
    payload = json.loads(raw_json)
    if not isinstance(payload, dict):
        raise ValueError('the JSON request must be an object')
    return payload


def validate_request(payload: dict) -> dict:
    """Key idea: Check the complete request and return clean inputs for this utility.

    Inputs: payload is the object produced by parse_request, with fields price_cents,
    percent.

    Output and return type: Return a fresh dict with validated field values and copied
    mutable containers; raise ValueError for unsupported inputs.

    Important conditions: Require exactly the documented fields and reject wrong types
    or out-of-range values. Integer fields reject booleans. Invalid prices or
    percentages raise ValueError; any fractional discount cent is rounded down before
    subtraction.

    Role in the program: Protect the calculation and report from malformed external
    input.

    Assumptions: This utility handles one percentage reduction with no taxes or
    additional adjustments.
    """
    if not isinstance(payload, dict):
        raise ValueError('request must be an object')
    required_fields = set(('price_cents', 'percent'))
    if set(payload) != required_fields:
        raise ValueError('request must contain exactly: ' + ', '.join(sorted(required_fields)))
    price_cents = payload['price_cents']
    percent = payload['percent']
    if type(price_cents) is not int or price_cents < 0:
        raise ValueError('price_cents must be a nonnegative integer')
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError('percent must be an integer from zero through one hundred')
    return {'price_cents': price_cents, 'percent': percent}


def discounted_price(price_cents: int, percent: int) -> int:
    """Key idea: Apply an integer percentage discount to a price represented in whole
    cents.

    Inputs: price_cents is a nonnegative integer; percent is an integer from zero
    through one hundred.

    Output and return type: Return the remaining price as an int number of cents after
    subtracting the discount.

    Important conditions: Invalid prices or percentages raise ValueError; any fractional
    discount cent is rounded down before subtraction.

    Role in the program: Calculate the primary result used by build_report and the
    default command-line output.

    Assumptions: This utility handles one percentage reduction with no taxes or
    additional adjustments.
    """
    if price_cents < 0 or not 0 <= percent <= 100:
        raise ValueError('invalid price or percentage')
    return price_cents - price_cents * percent // 1000


def build_report(payload: dict) -> dict:
    """Key idea: Build an in-memory price adjustment report using whole-cent amounts.

    Inputs: payload is a complete request dictionary with the utility's documented
    fields.

    Output and return type: Return a JSON-compatible dict with result, domain detail
    rows, and summary values; this function does not mutate the caller's request.

    Important conditions: Validate before calculation and propagate invalid-input
    errors. Amounts remain integer cents; zero original price avoids division and
    reports an effective percentage of zero.

    Role in the program: Connect checked input, the primary calculation, and useful
    diagnostics in one processing path.

    Assumptions: All summaries describe the supplied utility result; no database,
    network service, or companion file is required.
    """
    request = validate_request(payload)
    result = discounted_price(**request)
    original = request['price_cents']
    savings = original - result
    effective_percent = round(100 * savings / original, 2) if original else 0.0
    adjustments = [{
        'name': 'percentage_discount',
        'requested_percent': request['percent'],
        'amount_cents': savings,
    }]
    return {
        'result': result,
        'adjustments': adjustments,
        'summary': {
            'original_cents': original,
            'savings_cents': savings,
            'remaining_cents': result,
            'requested_percent': request['percent'],
            'effective_percent': effective_percent,
        },
    }


def build_argument_parser() -> argparse.ArgumentParser:
    """Key idea: Describe the supported command-line request and output options.

    Inputs: None; option values are parsed later by main.

    Output and return type: Return an argparse.ArgumentParser without parsing arguments
    or running the utility.

    Important conditions: All options are optional. Omitting --input-json selects the
    example, and omitting --report selects only the primary result.

    Role in the program: Give terminal users discoverable input, reporting, formatting,
    and help modes.

    Assumptions: The standard argparse module is available and option values are
    ordinary command-line strings.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-json', help='Complete request object as JSON; omit to use the built-in example')
    parser.add_argument('--report', action='store_true', help='Print the complete processing report')
    parser.add_argument('--pretty', action='store_true', help='Indent the JSON output for readability')
    return parser


def main(argv: list[str] | None = None) -> int:
    """Key idea: Run the complete input-to-report workflow and print the selected JSON
    view.

    Inputs: argv is a list of command-line arguments, or None to use the process
    arguments.

    Output and return type: Return int zero after printing one JSON result or report;
    return int two and print a JSON error on stderr for invalid input.

    Important conditions: The parser handles help and unknown options using argparse's
    standard exits. Processing errors stop before result output. --report selects the
    full report and --pretty only changes formatting.

    Role in the program: Provide the executable entry point while leaving each
    processing function importable.

    Assumptions: Standard output is available, the calculation returns JSON-compatible
    values, and inputs are small enough for in-memory reports.
    """
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        request = parse_request(args.input_json)
        report = build_report(request)
    except (ValueError, TypeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    output = report if args.report else report['result']
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
