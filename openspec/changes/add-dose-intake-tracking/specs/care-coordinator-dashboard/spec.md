## ADDED Requirements

### Requirement: Dose history timeline on patient detail page

The patient detail page SHALL display a chronological timeline of dose events (taken, missed) for each active medication, allowing care coordinators to see adherence patterns at a glance.

#### Scenario: Patient detail shows dose history

Given a care coordinator views the patient detail page for patient 1
When the page loads
Then a "Dose History" section displays the last 30 days of dose events
And each event shows the medication name, status (taken/missed), and timestamp
And missed doses are visually highlighted

#### Scenario: Empty dose history

Given a patient has no dose log records
When the patient detail page loads
Then the dose history section displays "No dose records yet"

---

### Requirement: Aggregate dose adherence on analytics page

The analytics page SHALL display system-wide dose adherence charts including weekly adherence trend and per-medication breakdown.

#### Scenario: Weekly dose adherence chart

Given a care coordinator visits the analytics page
When the page loads
Then a line chart shows weekly dose adherence rate (%) over the selected time period
And the chart is labelled "Dose Adherence Rate"

#### Scenario: Per-medication adherence table

Given a care coordinator visits the analytics page
When the page loads
Then a table shows each medication's adherence rate, total doses, taken count, and missed count
And medications are sorted by adherence rate ascending (worst first) to highlight problem areas
