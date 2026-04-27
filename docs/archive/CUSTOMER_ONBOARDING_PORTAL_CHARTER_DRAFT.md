# Customer Onboarding Portal — Project Charter (Historical Draft)

> **Archived.** Superseded by [docs/active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md](../active/CUSTOMER_ONBOARDING_PORTAL_CHARTER.md), the frozen Phase 1 charter. Retained for traceability only; not part of any active generation or validation flow.

---

## Business Context

The business is launching a self-serve **Customer Onboarding Portal** to replace the current email-and-spreadsheet onboarding workflow. Today, new customers wait three to five business days between signing a contract and gaining their first usable login because identity verification, KYC document collection, and account provisioning are handled manually by an internal operations team. This delay is the largest single contributor to early-stage churn and is the most frequently cited friction point in post-sale interviews.

The portal will let new customers complete signup, identity verification, document upload, and initial profile setup themselves, with internal review reserved for flagged or non-standard cases. Success here unlocks both faster time-to-value for customers and meaningful headcount relief for the operations team.

## Primary User

**External:** A newly-contracted customer representative — typically a finance, legal, or operations lead at a small-to-mid market business — who has just received a welcome email and needs to get their organisation set up without a phone call. Assumed comfortable with web forms, less comfortable with technical configuration.

**Internal (secondary):** The operations reviewer who handles the queue of flagged onboardings.

## Success Metric

**Primary:** Median time from contract signature to first successful customer login drops from the current 3–5 business days to **under 4 hours** for the unflagged path, measured over the first full quarter post-launch.

**Secondary:** At least **70%** of new onboardings complete end-to-end without internal-ops intervention.

## Known Constraints

- Must integrate with the existing identity provider; no new auth system.
- KYC checks must call the incumbent third-party verification vendor; contract is locked for 18 months.
- Customer PII handling must satisfy current data-residency commitments (EU data stays in EU region).
- Pilot rollout must be feature-flagged; no big-bang launch.
- Engineering capacity for the first quarter is two backend engineers, one frontend, and shared design.

## Explicit Non-Goals

- **Not** a full CRM replacement. The portal owns onboarding only; account management stays in the existing CRM.
- **Not** a billing or contract-signature surface. Contract signature happens upstream and is an input, not an output.
- **Not** a self-serve plan-change or upgrade flow. Post-onboarding lifecycle changes are out of scope for this initiative.
- **No** mobile app in the first release; responsive web only.
- **No** white-label or partner-branded variants in scope.
