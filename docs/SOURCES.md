# Job source connectors

`backend.app.connectors` contains the first permitted adapters:

- `JsonApiFeedAdapter` consumes a JSON API/feed payload (`jobs` or `data` list).
- `GreenhouseCareerPageAdapter` parses an employer career page using job cards.
- `LeverCareerPageAdapter` parses an employer career page using job cards.

All adapters return the shared `SourceFetchResult` and `NormalizedJob` contract.
They accept `SourceConfig.settings["payload"]` or `settings["html"]` (and the
corresponding `*_path`) for deterministic local fixtures. Network access is
disabled unless `allow_network=true` is explicitly configured. When enabled,
the adapter sends an identifiable user agent and checks the site's
`robots.txt` before fetching; terms-of-use review remains an operator
responsibility and must be acknowledged with `terms_accepted=True` (or the
equivalent `settings["terms_accepted"] = True`) before any fixture or network
content is processed. No adapter logs credentials, bypasses authentication/CAPTCHA,
or attempts to evade bot protections.

Example fixture configuration:

```python
config = SourceConfig(
    name="Example feed",
    kind=SourceKind.FEED,
    base_url="https://jobs.example/feed",
    terms_accepted=True,
    settings={"payload": '{"jobs": [{"title": "Engineer", "description": "Build APIs", "url": "/jobs/1", "apply_url": "/apply/1"}]}'},
)
result = JsonApiFeedAdapter().fetch(config)
```

Career-page fixtures use `<article data-job="true">` (or `class="job-card"`)
and links to the description. Optional child elements can set
`data-field="title|description|location|application_url"`.
