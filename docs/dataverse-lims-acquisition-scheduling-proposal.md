# Dataverse LIMS: Acquisition Scheduling Proposal

## 1. Purpose

This proposal defines a backend scheduling capability in LIMS to plan and track animal acquisitions across rigs.
The goal is to provide a reliable source of truth for planned sessions, associated metadata, and scheduling status.

## 2. User Stories

As a user, I want to:

- Schedule an acquisition for a specific animal, rig, date/time, and protocol(s).
- Attach notes and metadata (including aind-data-schema aligned fields) to a planned acquisition.
- View rig availability and planned acquisitions in a calendar-style view.
- Assign scientific contact(s) and experimenter(s) to each planned acquisition.
- See, from a planned session, which protocol(s) should run and with which planned parameters.
- Know whether a planned acquisition occurred as expected; if not, capture cancellation or rescheduling reasons. (outside this MVP, but important for future iterations)

## 3. Scope and Assumptions

### In scope (MVP)

- Backend storage and management of planned acquisitions.
- Dataverse as the database/backend layer.
- Programmatic access via a simple Python API.
- Rig-side read/validation of schedule at ingestion time.

### Out of scope (MVP)

- Dedicated front-end UI (though highly valuable for near-term follow-up).

### Key assumptions

- Rigs do not directly edit the schedule.
- Schedule interactions are mediated by experimenters/scientific contacts.
- Rigs query planned acquisitions and validate at ingestion.

## 4. Functional Requirements

The system should support:

- Retrieval of planned acquisitions by rig and date range.
- Retrieval of metadata and notes for a planned acquisition.
- Retrieval of next planned acquisition for an animal.
- Retrieval of protocol(s) (e.g; VrForaging, FIP, [DynamicForaging, FIP]) associated with a planned acquisition.
- Lifecycle status tracking (planned/completed/cancelled/rescheduled) (for future iterations).

## 5. Data Model (Planned Acquisition Record)

Each planned acquisition should include (AT LEAST):

- Animal ID
- Rig ID (SIPE environment variable name)
- Planned date/time (or a recurring date-based model?)
- Protocol(s) or task(s), referenced from a controlled vocabulary (VrForaging, FIP, etc.)
- Notes (free text)
- Metadata fields (either structured fields or JSON blob), e.g.:
  - Project name
  - IACUC protocol number
  - Other project-level descriptors
- Scientific contact(s)
- Experimenter(s)
- Status (Planned, Completed, Cancelled, Rescheduled)

## 6. Protocol Vocabulary Strategy

A controlled vocabulary of protocols should be maintained in Dataverse.

- This enables consistent scheduling references.
- It supports composable protocols (e.g., behavior + fiber photometry).
- It improves metadata quality and cross-rig/cross-time discoverability.
- Existing behavior curriculum tables can be reused where applicable.

## 7. API Expectations (Python Client)

A lightweight API should expose, at minimum:

- `get_planned_acquisitions(rig_id, start_date, end_date)` -> list[AcquisitionId]
- `get_acquisition_record(acquisition_id)` -> AcquisitionRecord (with metadata, notes, protocol(s), etc.)
- `get_next_acquisition_for_animal(animal_id)` -> AcquisitionId

## 8. Boundary with Runtime Execution

The scheduler is not the authority for runtime execution parameters.
Execution details remain the responsibility of downstream clients/protocol-specific systems.

For behavior workflows, existing curriculum tracking should continue to be used where appropriate. Additional tables may be introduced for other modalities (e.g., photometry settings, ephys trajectories).

## 9. Open Questions

- Should metadata be pushed upstream by the rig as a passthrough , or should metadata services query schedule metadata at transfer time?
- What is the intended user interaction surface:
  - Dedicated scheduling UI
  - Integration into existing LIMS interfaces
  - Both

## 10. Future Enhancements

- Token issuance and validation at acquisition time:
  - Rig queries schedule and receives acquisition token(s).
  - Token is presented during transfer for validation.
  - Enables pre-session traceability, stronger integrity checks, and improved reconciliation.
