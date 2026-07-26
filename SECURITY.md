# Security Policy

## Supported versions

The latest commit on `main` is the actively maintained version of Course Agent.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability and do not
include API keys, tokens, course files, or personal data in a report.

Use [GitHub private vulnerability reporting](https://github.com/FlowWhite/course-agent/security/advisories/new)
and include:

- the affected commit, component, or endpoint;
- clear reproduction steps and expected versus actual behavior;
- the potential impact and any suggested mitigation.

The maintainer will review the report privately and coordinate a fix before
public disclosure when appropriate.

## Scope notes

Course Agent is designed to keep raw course files in the configured local
storage volume. Relevant extracted text snippets may be sent to the configured
model provider to answer a course question. Deployers are responsible for using
an approved model provider and for protecting their own secrets and course data.
