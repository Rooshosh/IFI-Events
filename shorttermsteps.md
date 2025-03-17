- [x] Run local test with ngrok

- [ ] Change raw data table schema. Only store:
    - [ ] Scraped post URLs or IDs
    - [ ] Post-event-status determined by code: 'contains-event', 'is-event-llm' or 'not-event-llm'

- [ ] DB Structure:
    - [ ] Keep source for all events
    - [ ] Make new master events table

- [ ] Deduplication:
    - [ ] Prioritize good sources for main link
    - [ ] Maintain list for other links