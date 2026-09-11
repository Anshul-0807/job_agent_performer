"""Unit test: validation guards in ai_fill_form (no wrong answers ever)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.auto_applier import _valid_text_value, _valid_option_value

BANK = [
    "gyaneshwar chouhan", "gyaneshwarchouhan123@gmail.com", "+91-8793024246",
    "https://linkedin.com/in/gyaneshwar-chouhan-49bb85403",
    "surat, gujarat, india", "surat", "gujarat", "india",
    "6 lpa", "7 lpa", "immediate joiner", "3 years", "qa engineer",
    "manual testing, automation testing", "yes, i am willing to relocate anywhere in india",
    "linkedin", "yes, i am authorized to work in india", "currently employed, immediate joiner",
]

CASES = [
    # (fn, value, options, expected)
    ("text", "Surat", None, True),
    ("text", "7", None, True),            # "7" is inside "7 lpa"
    ("text", "3", None, True),            # "3" is inside "3 years"
    ("text", "Immediate", None, True),    # inside "immediate joiner"
    ("text", "7 LPA", None, True),
    ("text", "Gyaneshwar", None, True),   # inside full name
    ("text", "8 LPA", None, False),       # invented salary -> REJECT
    ("text", "Mumbai", None, False),      # not in answers -> REJECT
    ("text", "5 years", None, False),     # invented -> REJECT
    ("text", "10", None, False),          # not in any answer -> REJECT
    ("text", "", None, False),
    ("opt", "Immediate", ["15 days", "30 days", "60 days", "Immediate"], True),
    ("opt", "Immediate", ["15 days", "30 days", "60 days"], False),  # not an option -> REJECT
    ("opt", "Yes, I can relocate", ["true", "false"], False),        # invented option -> REJECT
    ("opt", "true", ["true", "false"], True),
    ("opt", "Yes, I can relocate", ["Yes, I can relocate", "No"], True),
    ("opt", "Manual Testing", ["Manual Testing", "DevOps"], True),
    ("opt", "Manual Testing", ["Selenium", "DevOps"], False),        # not an option -> REJECT
    ("opt", "I", ["India", "USA"], False),                           # too short -> REJECT
    ("opt", "India", ["India", "USA"], True),
    ("opt", "", ["India", "USA"], False),
]

fails = 0
for fn, value, opts, expected in CASES:
    got = _valid_text_value(value, BANK) if fn == "text" else _valid_option_value(value, opts)
    status = "OK " if got == expected else "FAIL"
    if got != expected:
        fails += 1
    print(f"  [{status}] {fn}({value!r}, {opts!r}) -> {got} expected {expected}")

print(f"\nRESULT: {'PASS' if fails == 0 else f'{fails} FAILURES'}")