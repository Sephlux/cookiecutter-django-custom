from django_hosts import patterns, host

host_patterns = patterns(
    "",
    host(r"www", "config.urls", name="www"),
    # host(r"api", "project.api_urls", name="api"),
    # host(r"", "project.urls", name="default"),  # catch-all, if desired
)
