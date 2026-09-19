# Databento daily Order Flow retention plan

1. Add a declarative three-asset/two-schema policy with explicit target/source
   identities and a daily cost ceiling.
2. Implement a testable collector with injected Databento client, cost-first
   admission, atomic raw DBN publication and per-artifact manifests.
3. Add a CLI for one day or a closed-day range and a Windows scheduled-task
   installer targeting the stable private market-data directory.
4. Run unit tests, install the schedule, execute the first eligible collection
   attempt and record its concrete status without exposing credentials.
5. Document how the retained trades and MBP-10 evidence plugs into Sagiv's
   footprint/delta/DOM confirmation layer while retaining source identity.
