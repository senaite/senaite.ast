Changelog
=========

1.3.0 (unreleased)
------------------

- #49 Default all antibiotics to reportable when selective reporting is enabled

1.2.0 (2025-04-04)
------------------

- #47 Add support for CLSI guideline boundaries in addition to EUCAST
- #42 Fix cannot enter small decimals in breakpoint table
- #40 Compatibility with core#2537 (Support multi-text on result entry)
- #39 Compatibility with core#2584 (SampleType to DX)
- #38 Compatibility with core#2595 (Move ARAnalysesField logic to data manager)
- #37 Compatibility with core#2567 (AnalysisCategory to DX)
- #37 Compatibility with core#2471 (Department to DX)
- #36 Fix user can edit ast built-in services after upgrades
- #35 Compatibility with core#2521 - AT2DX ARTemplate/SampleTemplate
- #34 Add transition "Reject antibiotics"
- #33 Display the Antibiotic Sensitivity section only when necessary
- #32 Compatibility with senaite.core#2492 (AnalysisProfile to DX)


1.1.0 (2024-01-04)
------------------

- #31 Support lower than, greater than and fractions for MIC values
- #30 Fix sizes for numeric fields are too small
- #26 Fix Sensitivity result is not updated when selective reporting is missing
- #25 Do not allow to "submit" AST analyses with no result save
- #23 Fix AST calculation does not work when extrapolated antibiotics
- #22 Hide Unit and display Submitter before Captured in AST entry
- #21 Fix AST entry is empty when analyses categorization for sample is checked
- #20 Compatibility with senaite.app.listing#87


1.0.0 (2022-06-18)
------------------

- #17 Selective reporting for extrapolated antibiotics
- #15 Support for extrapolated antibiotics
- #13 Allow addition of new antibiotics to submitted/verified AST analyses
- #12 Negative values for diameter and zone size tests not permitted
- #12 Do not allow to submit AST analyses with empties
- #11 Better styling of AST Panel selector in Sample view
- #10 Allow to remove retracted AST analyses retests
- Initial Release
