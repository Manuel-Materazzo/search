FROM docker.io/searxng/searxng:latest

COPY --chown=searxng:searxng ./searx/templates ./searx/templates
COPY --chown=searxng:searxng ./searx/static ./searx/static

EXPOSE 8080

ENTRYPOINT ["/usr/local/searxng/entrypoint.sh"]
