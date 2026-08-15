"""In-network fixture targets for the SSRF demonstration.

These stand in for the one external content source the preview feature is meant
to use (``assets.larkspur.test``) and an internal-only service that external
callers should never reach (``backoffice.larkspur.internal``). Both are wholly
fictional and reachable only inside the container network.
"""
