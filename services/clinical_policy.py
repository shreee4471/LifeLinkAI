"""Versioned red-cell ABO/Rh policy pending local clinician approval."""

POLICY_VERSION = "red-cell-abo-rh-v1"
POLICY_STATUS = "Requires clinician review before production use"

BLOOD_COMPATIBILITY = {
    "A+": ("A+", "A-", "O+", "O-"),
    "A-": ("A-", "O-"),
    "B+": ("B+", "B-", "O+", "O-"),
    "B-": ("B-", "O-"),
    "AB+": ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"),
    "AB-": ("A-", "B-", "AB-", "O-"),
    "O+": ("O+", "O-"),
    "O-": ("O-",),
}


def is_compatible_recipient_donor(recipient_group, donor_group):
    return donor_group in BLOOD_COMPATIBILITY.get(recipient_group, ())
