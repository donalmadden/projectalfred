# Customer Onboarding Portal Charter

> Frozen Phase 1 kickoff input for the Alfred blank-project demo.

## Business Context

A financial-services firm wants a self-service Customer Onboarding Portal so new retail customers can create their account, verify identity, upload required KYC documents, and activate access without a branch visit or a back-and-forth email chain. Today onboarding is fragmented across sales handoff, compliance review, and manual account setup, which slows time-to-value and makes it hard to see where customers stall. The first release must define the end-to-end onboarding journey, capture the customer profile data needed for activation, trigger welcome and activation emails at the right moments, and give leadership visibility into funnel drop-off and flagged-case volume. Customer trust is most fragile between contract signature and first login, so the flow must feel guided, fast, and auditable.

## Primary User

The primary user is a newly approved retail customer starting onboarding digitally from a phone or laptop, often outside business hours, who expects a guided step-by-step flow rather than a call with support. Most users will be completing the process for the first time and will have little patience for jargon or repeated requests. The secondary user is an internal compliance-operations reviewer who must inspect flagged applications, request missing evidence, and clear legitimate customers quickly.

## Success Metric

At least 80% of new customers should complete onboarding end-to-end without human intervention within 10 minutes of starting. The team must also be able to measure funnel conversion, abandonment by step, and turnaround time for flagged reviews during the pilot so rollout decisions are based on evidence rather than anecdotes.

## Known Constraints

The portal must integrate with the existing identity-verification vendor API and downstream account-provisioning systems; Phase 1 cannot introduce a new system of record or new data stores. The experience must be mobile-first but not mobile-only, support secure document upload from common consumer devices, and keep regulated customer data inside current compliance boundaries. Flagged or incomplete applications must route to an internal ops review queue. Initial rollout is a feature-flagged pilot cohort before broader release and should reuse the existing notification stack where possible.

## Explicit Non-Goals

This phase does not cover branch-assisted onboarding, existing-customer profile changes, international KYC variations, billing or CRM workflows, native mobile apps, or partner-branded variants.
