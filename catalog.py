"""The same public reference data for the API and the installable offline app."""

from dataclasses import asdict

from consultation import CLINIC_INFO, OBJECTIONS, PACKAGES, PATIENT_TYPES, SINGLE_SERVICES, STAGES
from syndrome_kb import load_syndromes

VERSION = "1.0.0"


def build_catalog() -> dict:
    return {
        "version": VERSION,
        "syndromes": [asdict(record) for record in load_syndromes()],
        "clinic": CLINIC_INFO,
        "services": SINGLE_SERVICES,
        "packages": PACKAGES,
        "patientTypes": PATIENT_TYPES,
        "objections": OBJECTIONS,
        "stages": STAGES,
    }
