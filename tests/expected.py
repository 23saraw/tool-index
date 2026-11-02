"""Expected indexes, derived by hand from the README's rules before any code ran. Never generate these."""

from __future__ import annotations

import copy

DIGITS = "0123456789"  # hash_blob's description starts with this 12 times: one 120-character word

SETS = {
    # set-1, in rule-5 order, with each tool's trap.
    "set-1.json": {
        "valid": True,
        "duplicates": [],
        "entries": [
            "add_days: Adds days to a date, e.g. weekends.",  # "e.g." then lowercase: no split; the end has no space
            "alpha_sync: Syncs the alpha store.",  # sorts before Zeta_sync: names sort lowercased
            "ask_user: Asks the user a question? Waits for the reply! Then returns it.",  # ? and ! end nothing
            "clear_cache: (no description)",  # no description key at all
            "Export_notes: Exports notes as plain text, one file per folder.",  # tab, newline, runs; "E" before "e"
            "export_notes: Exports notes as Markdown.",  # "\n\n  Each" collapses to " Each": a sentence end
            # 101 characters: "time." would make 101, so cut after "focus" (95), then "…" (96)
            "find_slots: Finds open meeting slots across every invited calendar, skipping holidays and any blocked focus…",
            "hash_blob: " + DIGITS * 9 + "012345678…",  # one 120-character word: its first 99, then "…"
            'log_event: (no description)',  # ""
            # exactly 100 characters: kept as is
            (
                "merge_contacts: Merges duplicate contacts that share one email address or phone number,"
                " then keeps the newest entry."
            ),
            "noop: (no description)",  # " \n\t ": only whitespace
            "pick_source: Uses e.g.",  # "e.g." then "The": a sentence end
            "ping_service: Checks that the service is up and answering",  # no period: the whole description
            "Zeta_sync: Syncs the zeta store.",
        ],
    },
    # set-2: send_note twice; Send_note differs only in case, so it is not a duplicate.
    "set-2.json": {"valid": False, "duplicates": ["send_note"], "entries": []},
}

# The first sentences at the length boundaries, and their lengths, counted by hand.
EXACTLY_100 = "Merges duplicate contacts that share one email address or phone number, then keeps the newest entry."
JUST_OVER = "Finds open meeting slots across every invited calendar, skipping holidays and any blocked focus time."


def answer(name: str) -> dict:
    """The right submission for set ``name``, as JSON."""
    return {"set": name, **copy.deepcopy(SETS[name])}
