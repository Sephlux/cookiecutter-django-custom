from django_hosts import patterns, host

host_patterns = patterns(
    "",
    host(r"www", "{{cookiecutter.project_slug}}.apps.landing_page.urls", name="www"),
    host(r"app", "config.urls", name="app"),
    # host(r"api", "project.api_urls", name="api"),
    # host(r"", "project.urls", name="default"),  # catch-all, if desired
)
