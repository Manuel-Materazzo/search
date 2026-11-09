FROM docker.io/searxng/searxng:latest

# Folders
COPY --chown=searxng:searxng ./searx/templates ./searx/templates
COPY --chown=searxng:searxng ./searx/static ./searx/static

# Subfolder files
COPY --chown=searxng:searxng ./searx/search/__init__.py ./searx/search/__init__.py
COPY --chown=searxng:searxng ./searx/search/models.py ./searx/search/models.py
COPY --chown=searxng:searxng ./searx/search/processors/online.py ./searx/search/processors/online.py
COPY --chown=searxng:searxng ./searx/result_types/_base.py ./searx/result_types/_base.py
COPY --chown=searxng:searxng ./searx/plugins/tracker_url_remover.py ./searx/plugins/tracker_url_remover.py
COPY --chown=searxng:searxng ./searx/data/tracker_patterns.py ./searx/data/tracker_patterns.py

# Root files
COPY --chown=searxng:searxng ./searx/preferences.py ./searx/preferences.py
COPY --chown=searxng:searxng ./searx/webadapter.py ./searx/webadapter.py
COPY --chown=searxng:searxng ./searx/webapp.py ./searx/webapp.py
COPY --chown=searxng:searxng ./searx/settings_defaults.py /usr/local/searxng/searx/settings_defaults.py
COPY --chown=searxng:searxng ./searx/settings.yml /etc/searxng/settings.yml


# Force Python to recompile by removing stale bytecode
RUN find /usr/local/searxng/searx -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
RUN find /usr/local/searxng/searx -type f -name '*.pyc' -delete 2>/dev/null || true


EXPOSE 8080

ENTRYPOINT ["/usr/local/searxng/entrypoint.sh"]
